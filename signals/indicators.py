"""Technical indicators used by the signal engine (strategy-rules.md §1-2)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def ema(close: pd.Series, span: int) -> pd.Series:
    return close.ewm(span=span, adjust=False).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    # avg_loss == 0: all-gains run -> RSI 100, unless avg_gain is also 0 (flat) -> 50
    out = out.where(avg_loss != 0, np.where(avg_gain > 0, 100, 50))
    return pd.Series(out, index=close.index).fillna(50)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "hist": hist})


def bollinger_bands(close: pd.Series, period: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return pd.DataFrame({"mid": mid, "upper": upper, "lower": lower})


def volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
    avg = volume.rolling(period).mean()
    return volume / avg.replace(0, np.nan)


def realized_vol(close: pd.Series, period: int = 20, annualize: bool = True) -> pd.Series:
    log_ret = np.log(close / close.shift(1))
    vol = log_ret.rolling(period).std()
    if annualize:
        vol = vol * np.sqrt(252)
    return vol


def made_new_high(close: pd.Series, lookback: int = 10, within_last: int = 3) -> bool:
    """True if the latest close is a new `lookback`-day high, and that high
    was set within the last `within_last` sessions (not stale/faded).
    Originally speced in strategy-rules.md §1 ("new 10-day high... trigger")
    but never wired into select_structure() until now -- an extra
    confirmation gate to raise entry quality."""
    if len(close) < lookback:
        return False
    window = close.tail(lookback)
    high_idx = window.values.argmax()
    sessions_since_high = len(window) - 1 - high_idx
    return bool(close.iloc[-1] >= window.max() and sessions_since_high < within_last)


def made_new_low(close: pd.Series, lookback: int = 10, within_last: int = 3) -> bool:
    if len(close) < lookback:
        return False
    window = close.tail(lookback)
    low_idx = window.values.argmin()
    sessions_since_low = len(window) - 1 - low_idx
    return bool(close.iloc[-1] <= window.min() and sessions_since_low < within_last)


def trend_strength(close: pd.Series, fast: int = 20, slow: int = 50) -> float:
    """(EMA_fast - EMA_slow) / EMA_slow -- how separated the two EMAs are,
    not just which side of each other they're on. classify_trend() only
    checks a bare crossover (price > ema20 > ema50), which fires on a trend
    that's barely formed; this measures how strong it actually is."""
    if len(close) < slow:
        return 0.0
    e_fast = ema(close, fast).iloc[-1]
    e_slow = ema(close, slow).iloc[-1]
    if e_slow == 0:
        return 0.0
    return float((e_fast - e_slow) / e_slow)
