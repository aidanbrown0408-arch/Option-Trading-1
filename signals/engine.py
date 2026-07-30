"""Signal engine: trend/momentum/volatility read -> structure selection.

Pure functions only (no I/O, no broker calls) per strategy-rules.md.
Implements §1 (trend), §2 (momentum), §3 (volatility regime) and §4
(strategy selection matrix).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from signals.indicators import bollinger_bands, ema, macd, rsi, volume_ratio

TREND_UP = "uptrend"
TREND_DOWN = "downtrend"
TREND_RANGE = "range_bound"

BB_UPPER = "upper"
BB_LOWER = "lower"
BB_MIDDLE = "middle"


@dataclass
class SignalRead:
    date: pd.Timestamp
    daily_trend: str
    weekly_trend: str
    trend: str  # combined per §1: disagreement -> range_bound
    rsi: float
    macd_hist: float
    macd_rising: bool
    bb_position: str
    volume_ratio: float
    iv_regime: str  # "high" | "low"
    iv_rank: float


def classify_trend(close: pd.Series) -> str:
    """20/50 EMA slope + price position. Assumes `close` already sliced to
    the relevant timeframe (daily or weekly)."""
    if len(close) < 51:
        return TREND_RANGE
    ema20 = ema(close, 20)
    ema50 = ema(close, 50)
    price = close.iloc[-1]
    e20, e20_prev = ema20.iloc[-1], ema20.iloc[-5]
    e50 = ema50.iloc[-1]
    if price > e20 > e50 and e20 > e20_prev:
        return TREND_UP
    if price < e20 < e50 and e20 < e20_prev:
        return TREND_DOWN
    return TREND_RANGE


def combined_trend(daily_close: pd.Series, weekly_close: pd.Series) -> tuple[str, str, str]:
    daily = classify_trend(daily_close)
    weekly = classify_trend(weekly_close)
    if daily == weekly and daily != TREND_RANGE:
        return daily, weekly, daily
    return daily, weekly, TREND_RANGE


def bb_position(close: pd.Series) -> str:
    bands = bollinger_bands(close)
    price = close.iloc[-1]
    upper, lower = bands["upper"].iloc[-1], bands["lower"].iloc[-1]
    if pd.isna(upper) or pd.isna(lower):
        return BB_MIDDLE
    if price >= upper:
        return BB_UPPER
    if price <= lower:
        return BB_LOWER
    return BB_MIDDLE


def classify_iv_regime(iv_rank: float, threshold: float = 50.0) -> str:
    return "high" if iv_rank >= threshold else "low"


def build_signal_read(
    daily: pd.DataFrame,
    weekly: pd.DataFrame,
    iv_rank: float,
) -> Optional[SignalRead]:
    """`daily`/`weekly` are OHLCV DataFrames indexed by date, columns
    open/high/low/close/volume, sliced up to (and including) the eval date."""
    if len(daily) < 51 or len(weekly) < 51:
        return None

    close = daily["close"]
    daily_trend, weekly_trend, trend = combined_trend(close, weekly["close"])

    rsi_val = rsi(close).iloc[-1]
    macd_df = macd(close)
    macd_hist = macd_df["hist"].iloc[-1]
    macd_rising = macd_df["hist"].iloc[-1] > macd_df["hist"].iloc[-4]
    bb_pos = bb_position(close)
    vol_ratio = volume_ratio(daily["volume"]).iloc[-1]
    iv_regime = classify_iv_regime(iv_rank)

    return SignalRead(
        date=daily.index[-1],
        daily_trend=daily_trend,
        weekly_trend=weekly_trend,
        trend=trend,
        rsi=float(rsi_val),
        macd_hist=float(macd_hist),
        macd_rising=bool(macd_rising),
        bb_position=bb_pos,
        volume_ratio=float(vol_ratio) if pd.notna(vol_ratio) else 0.0,
        iv_regime=iv_regime,
        iv_rank=iv_rank,
    )


# --- §4 strategy selection matrix -------------------------------------------------

IRON_CONDOR = "iron_condor"
CREDIT_SPREAD_BULL_PUT = "credit_spread_bull_put"
CREDIT_SPREAD_BEAR_CALL = "credit_spread_bear_call"
DEBIT_SPREAD_CALL = "debit_spread_call"
DEBIT_SPREAD_PUT = "debit_spread_put"
LONG_STRADDLE = "long_straddle"
NO_TRADE = None


def select_structure(read: SignalRead, catalyst_flagged: bool) -> Optional[str]:
    """Maps a SignalRead to a structure per strategy-rules.md §4.
    Returns None if no row of the matrix cleanly applies."""

    momentum_confirms_up = read.macd_hist > 0 and read.macd_rising and read.rsi >= 45
    momentum_confirms_down = read.macd_hist < 0 and not read.macd_rising and read.rsi <= 55

    if catalyst_flagged and read.iv_regime == "low":
        return LONG_STRADDLE

    if read.iv_regime == "high":
        if read.trend == TREND_RANGE and read.bb_position in (BB_UPPER, BB_LOWER):
            return IRON_CONDOR
        if read.trend == TREND_UP and momentum_confirms_up:
            return CREDIT_SPREAD_BULL_PUT
        if read.trend == TREND_DOWN and momentum_confirms_down:
            return CREDIT_SPREAD_BEAR_CALL
        return NO_TRADE

    # low IV regime
    if read.trend == TREND_UP and momentum_confirms_up and read.bb_position != BB_LOWER:
        return DEBIT_SPREAD_CALL
    if read.trend == TREND_DOWN and momentum_confirms_down and read.bb_position != BB_UPPER:
        return DEBIT_SPREAD_PUT
    return NO_TRADE
