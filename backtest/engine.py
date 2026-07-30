"""Backtesting engine: replays signals + trade construction + risk manager
over historical (or synthetic) data. No broker adapter involved — see
PLANNING.md §5 and docs/strategy-rules.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Optional

import pandas as pd

from data.provider import DataProvider
from execution.constructor import TradeCandidate, build_trade
from execution.options_pricing import structure_value
from risk.manager import PortfolioState, approve_trade
from signals.engine import LONG_STRADDLE, NO_TRADE, build_signal_read, select_structure
from signals.indicators import realized_vol

TARGET_DTE_DAYS = 10  # mid-point of the 7-10 DTE weekly window (strategy-rules.md §1 intro)
RISK_FREE_RATE = 0.045
PROFIT_TARGET_PCT = 0.50
DEBIT_STOP_PCT = 0.40
CREDIT_STOP_MULT = 2.0
DTE_EXIT_DAYS = 3

# Our IV proxy is trailing realized vol (data/provider.py), which is
# backward-looking and blind to the real IV run-up markets price in ahead of
# earnings. Without this markup, straddle entries get priced as if IV were
# still calm right before a real historical earnings jump, understating cost
# and manufacturing an unrealistic edge. 1.6x is a rough placeholder for
# "typical" earnings IV expansion, not a fitted number — revisit once real
# historical options IV is available.
EARNINGS_IV_MARKUP = 1.6


@dataclass
class OpenPosition:
    ticker: str
    structure: str
    entry_date: pd.Timestamp
    expiry_date: pd.Timestamp
    entry_underlying: float
    entry_sigma: float
    candidate: TradeCandidate
    contracts: int
    entry_trend: str


@dataclass
class ClosedTrade:
    ticker: str
    structure: str
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    contracts: int
    pnl: float
    exit_reason: str


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    trades: list[ClosedTrade] = field(default_factory=list)


def _dte_years(current_date: pd.Timestamp, expiry_date: pd.Timestamp) -> float:
    return max((expiry_date - current_date).days, 0) / 365.0


def _current_sigma(daily: pd.DataFrame) -> float:
    rv = realized_vol(daily["close"])
    val = rv.iloc[-1]
    return float(val) if pd.notna(val) else 0.25


def _check_exit(pos: OpenPosition, current_date: pd.Timestamp, mark: float,
                 underlying: float, trend_now: str) -> Optional[str]:
    dte_remaining = (pos.expiry_date - current_date).days
    is_debit = pos.candidate.entry_cost > 0

    if is_debit:
        pnl_pct = (mark - pos.candidate.entry_cost) / abs(pos.candidate.entry_cost)
        if pnl_pct >= PROFIT_TARGET_PCT:
            return "profit_target"
        if pnl_pct <= -DEBIT_STOP_PCT:
            return "stop_loss"
    else:
        credit = -pos.candidate.entry_cost
        current_credit_owed = -mark  # what it would cost to close now
        profit_captured = credit - current_credit_owed
        if profit_captured >= PROFIT_TARGET_PCT * pos.candidate.max_profit:
            return "profit_target"
        if current_credit_owed >= CREDIT_STOP_MULT * credit:
            return "stop_loss"

    if dte_remaining <= DTE_EXIT_DAYS:
        return "dte_exit"

    if pos.entry_trend != trend_now and trend_now != "range_bound":
        return "trend_reversal"

    return None


def run_backtest(
    tickers: list[str],
    provider: DataProvider,
    start: str,
    end: str,
    starting_equity: float = 100_000.0,
) -> BacktestResult:
    all_daily = {t: provider.get_daily_bars(t, "2022-01-01", end) for t in tickers}
    dates = pd.bdate_range(start, end)

    portfolio = PortfolioState(equity=starting_equity, start_of_day_equity=starting_equity)
    open_positions: dict[str, OpenPosition] = {}
    trades: list[ClosedTrade] = []
    equity_curve = []

    for date in dates:
        portfolio.start_of_day_equity = portfolio.equity

        for ticker in list(open_positions.keys()):
            pos = open_positions[ticker]
            daily = all_daily[ticker].loc[:date]
            if daily.empty or date not in daily.index:
                continue
            underlying = float(daily["close"].iloc[-1])
            T = _dte_years(date, pos.expiry_date)
            sigma = pos.entry_sigma
            mark = structure_value(pos.candidate.legs, underlying, T, RISK_FREE_RATE, sigma)

            weekly = daily["close"].resample("W").last().dropna()
            read = build_signal_read(daily, pd.DataFrame({"close": weekly, "volume": daily["volume"].resample("W").sum()}), provider.get_iv_rank(ticker, date))
            trend_now = read.trend if read else pos.entry_trend

            reason = _check_exit(pos, date, mark, underlying, trend_now)
            if T <= 0 and reason is None:
                reason = "expired"

            if reason:
                if pos.candidate.entry_cost > 0:
                    pnl = (mark - pos.candidate.entry_cost) * pos.contracts * 100
                else:
                    pnl = (-pos.candidate.entry_cost - (-mark)) * pos.contracts * 100
                portfolio.equity += pnl
                trades.append(ClosedTrade(
                    ticker=ticker, structure=pos.structure, entry_date=pos.entry_date,
                    exit_date=date, contracts=pos.contracts, pnl=pnl, exit_reason=reason,
                ))
                del open_positions[ticker]

        for ticker in tickers:
            if ticker in open_positions:
                continue
            daily = all_daily[ticker].loc[:date]
            if len(daily) < 60 or date not in daily.index:
                continue

            weekly_close = daily["close"].resample("W").last().dropna()
            weekly_vol = daily["volume"].resample("W").sum()
            weekly = pd.DataFrame({"close": weekly_close, "volume": weekly_vol})
            iv_rank = provider.get_iv_rank(ticker, date)
            read = build_signal_read(daily, weekly, iv_rank)
            if read is None:
                continue

            if provider.is_earnings_window(ticker, date) and read.iv_regime == "low":
                catalyst_flagged = True
            elif provider.is_earnings_window(ticker, date):
                continue  # skip: earnings window, not a flagged long-vol setup (strategy-rules.md §3)
            else:
                catalyst_flagged = False

            structure = select_structure(read, catalyst_flagged)
            if structure is NO_TRADE:
                continue

            underlying = float(daily["close"].iloc[-1])
            sigma = _current_sigma(daily)
            if structure == LONG_STRADDLE:
                sigma *= EARNINGS_IV_MARKUP
            expiry_date = date + timedelta(days=TARGET_DTE_DAYS)
            T = TARGET_DTE_DAYS / 365.0

            candidate = build_trade(structure, underlying, T, RISK_FREE_RATE, sigma)
            per_contract_risk = candidate.max_loss
            contracts = approve_trade(ticker, per_contract_risk, portfolio)
            if contracts <= 0:
                continue

            open_positions[ticker] = OpenPosition(
                ticker=ticker, structure=structure, entry_date=date, expiry_date=expiry_date,
                entry_underlying=underlying, entry_sigma=sigma, candidate=candidate,
                contracts=contracts, entry_trend=read.trend,
            )

        equity_curve.append((date, portfolio.equity))

    curve = pd.Series({d: e for d, e in equity_curve}).sort_index()
    return BacktestResult(equity_curve=curve, trades=trades)
