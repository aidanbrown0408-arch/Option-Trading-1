"""Signal engine: trend/momentum/volatility read -> structure selection.

Pure functions only (no I/O, no broker calls) per strategy-rules.md.
Implements §1 (trend), §2 (momentum), §3 (volatility regime) and §4
(strategy selection matrix).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from signals.indicators import (
    bollinger_bands,
    ema,
    macd,
    made_new_high,
    made_new_low,
    rsi,
    trend_strength,
    volume_ratio,
)

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
    breakout_up: bool
    breakout_down: bool
    weekly_rsi: float
    trend_strength: float  # (EMA20-EMA50)/EMA50 on the daily close


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
    weekly_rsi_val = rsi(weekly["close"]).iloc[-1]

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
        breakout_up=made_new_high(close),
        breakout_down=made_new_low(close),
        weekly_rsi=float(weekly_rsi_val),
        trend_strength=trend_strength(close),
    )


# --- §4 strategy selection matrix -------------------------------------------------
# Exactly 3 structures, per user decision: long call, long put, and iron
# condor -- iron condor kept specifically because it's had the highest win
# rate of any structure in every run so far (72-79%). Dropped: debit spread
# put and both credit spreads (not proven wrong, just cut for scope -- see
# git history if reconsidering), and long_straddle (proven pricing
# artifact: a real-data run showed 94% of total P&L / 68.6% win rate came
# from our realized-vol IV proxy underpricing straddles ahead of real
# historical earnings jumps).
#
# Directional entries (long call/put) require LOW IV, full stop -- with no
# debit/credit spread left to route the high-IV case to, the alternative
# would be buying rich premium in a high-IV regime with no structural edge
# to compensate. Tried allowing that: blended win rate went DOWN despite
# stricter entry filters, because it diluted the sample with structurally
# worse high-IV entries. Skipping high-IV directional setups entirely
# instead of forcing a worse trade.

LONG_CALL = "long_call"
LONG_PUT = "long_put"
IRON_CONDOR = "iron_condor"
NO_TRADE = None


MIN_VOLUME_RATIO = 1.2  # strategy-rules.md §2: "confirming (>=1.2x avg)" -- was
                         # computed but never actually enforced until now.
MIN_TREND_STRENGTH = 0.01  # EMA20/EMA50 must be >=1% apart -- a bare
                            # crossover (classify_trend's own bar) can fire
                            # on a trend that's barely formed.


def select_structure(read: SignalRead) -> Optional[str]:
    """Maps a SignalRead to a structure per strategy-rules.md §4.

    Multiple independent confirmations required for a directional entry,
    not just one signal family:
      1. Daily trend (EMA20/EMA50 crossover + slope)
      2. Weekly trend (must agree with daily -- see combined_trend)
      3. Trend strength (EMA separation >= MIN_TREND_STRENGTH, not just a
         bare crossover)
      4. Daily momentum (MACD histogram positive/rising + RSI >=/<=50)
      5. Weekly momentum (weekly RSI agrees with the daily read)
      6. Volume (>=1.2x the 20-day average)
      7. Breakout (genuine new 10-day high/low within the last 3 sessions)
      8. Bollinger Band guardrail (not entering against an overbought/
         oversold extreme)
      9. Low IV regime (no debit/credit spread left to absorb a high-IV
         entry's richer premium, so high IV skips the trade entirely)
    Losing any one of these blocks the trade -- deliberately strict, since
    at 0.12-delta OTM long options a losing trade is the expected common
    case (delta ~= probability of profit), so entry quality is the only
    lever to raise win rate without also raising cost/contract.

    Iron condor is a separate, range-bound/mean-reversion setup: high IV +
    price at a Bollinger Band edge, no trend/momentum requirement (that's
    the opposite of what the structure is for).
    """

    volume_confirms = read.volume_ratio >= MIN_VOLUME_RATIO
    momentum_confirms_up = (read.macd_hist > 0 and read.macd_rising
                             and read.rsi >= 50 and read.weekly_rsi >= 50)
    momentum_confirms_down = (read.macd_hist < 0 and not read.macd_rising
                               and read.rsi <= 50 and read.weekly_rsi <= 50)
    trend_strong_up = read.trend_strength >= MIN_TREND_STRENGTH
    trend_strong_down = read.trend_strength <= -MIN_TREND_STRENGTH

    if (read.trend == TREND_UP and momentum_confirms_up and volume_confirms
            and read.breakout_up and trend_strong_up and read.bb_position != BB_LOWER
            and read.iv_regime == "low"):
        return LONG_CALL
    if (read.trend == TREND_DOWN and momentum_confirms_down and volume_confirms
            and read.breakout_down and trend_strong_down and read.bb_position != BB_UPPER
            and read.iv_regime == "low"):
        return LONG_PUT

    if (read.trend == TREND_RANGE and read.iv_regime == "high"
            and read.bb_position in (BB_UPPER, BB_LOWER)):
        return IRON_CONDOR

    return NO_TRADE
