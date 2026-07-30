"""Diagnostic tool: for one ticker, count how many candidate trading days get
filtered out at each stage (data availability, signal read, earnings window,
structure selection, affordability). Use this whenever a backtest run
reports "no trades" and it isn't obvious why -- it pinpoints the bottleneck
instead of guessing. Not part of the normal backtest loop.

Usage:
    python -m backtest.diagnose --source alpaca --ticker AAPL --start 2023-01-01 --end 2026-06-30
"""
from __future__ import annotations

import argparse
from collections import Counter

import pandas as pd

from backtest.engine import RISK_FREE_RATE, TARGET_DTE_DAYS, _current_sigma
from data.provider import DataProvider
from execution.constructor import build_trade
from risk.manager import size_for_trade
from signals.engine import NO_TRADE, build_signal_read, select_structure


def diagnose_ticker(ticker: str, provider: DataProvider, start: str, end: str) -> None:
    daily_full = provider.get_daily_bars(ticker, "2022-01-01", end)
    print(f"Fetched {len(daily_full)} daily bars for {ticker}, "
          f"range {daily_full.index.min()} to {daily_full.index.max()}" if len(daily_full) else
          f"Fetched 0 daily bars for {ticker}")

    dates = pd.bdate_range(start, end)
    counts = Counter()
    sample_costs = []

    for date in dates:
        counts["total_days"] += 1
        daily = daily_full.loc[:date]
        if len(daily) < 60 or date not in daily.index:
            counts["insufficient_data_or_date_missing"] += 1
            continue

        weekly_close = daily["close"].resample("W").last().dropna()
        weekly_vol = daily["volume"].resample("W").sum()
        weekly = pd.DataFrame({"close": weekly_close, "volume": weekly_vol})
        iv_rank = provider.get_iv_rank(ticker, date)
        read = build_signal_read(daily, weekly, iv_rank)
        if read is None:
            counts["no_signal_read"] += 1
            continue

        if provider.is_earnings_window(ticker, date):
            counts["earnings_skip"] += 1
            continue

        structure = select_structure(read)
        if structure is NO_TRADE:
            counts["no_trade_signal"] += 1
            continue
        counts["structure_selected"] += 1
        counts[f"  structure__{structure}"] += 1

        underlying = float(daily["close"].iloc[-1])
        sigma = _current_sigma(daily)
        T = TARGET_DTE_DAYS / 365.0
        candidate = build_trade(structure, underlying, T, RISK_FREE_RATE, sigma)
        cost = candidate.max_loss * 100
        sample_costs.append(cost)
        contracts = size_for_trade(candidate.max_loss)
        if contracts <= 0:
            counts["rejected_unaffordable"] += 1
        else:
            counts["would_open_trade"] += 1

    print(f"\n=== {ticker} diagnostic ({start} to {end}) ===")
    for k in ["total_days", "insufficient_data_or_date_missing", "no_signal_read",
              "earnings_skip", "no_trade_signal", "structure_selected"]:
        print(f"{k:35s} {counts.get(k, 0)}")
    for k, v in counts.items():
        if k.startswith("  structure__"):
            print(f"{k:35s} {v}")
    for k in ["rejected_unaffordable", "would_open_trade"]:
        print(f"{k:35s} {counts.get(k, 0)}")

    if sample_costs:
        s = pd.Series(sample_costs)
        print(f"\ncost/contract over candidates: min={s.min():.2f} "
              f"median={s.median():.2f} max={s.max():.2f}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--start", default="2023-01-01")
    parser.add_argument("--end", default="2026-06-30")
    parser.add_argument("--source", default="synthetic", choices=["synthetic", "alpaca"])
    args = parser.parse_args()

    if args.source == "alpaca":
        from data.alpaca_provider import AlpacaDataProvider
        provider = AlpacaDataProvider()
    else:
        from data.synthetic import SyntheticDataProvider
        provider = SyntheticDataProvider()

    diagnose_ticker(args.ticker, provider, args.start, args.end)


if __name__ == "__main__":
    main()
