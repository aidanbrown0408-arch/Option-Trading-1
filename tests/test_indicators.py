import numpy as np
import pandas as pd

from signals.indicators import (
    bollinger_bands,
    ema,
    macd,
    made_new_high,
    made_new_low,
    realized_vol,
    rsi,
    volume_ratio,
)


def _rising_series(n=100, start=100.0, step=0.5):
    return pd.Series(start + np.arange(n) * step)


def test_ema_tracks_trend():
    s = _rising_series()
    e = ema(s, 20)
    assert e.iloc[-1] > e.iloc[20]


def test_rsi_bounds():
    s = _rising_series()
    r = rsi(s)
    assert (r.dropna() >= 0).all() and (r.dropna() <= 100).all()


def test_rsi_high_on_strong_uptrend():
    s = _rising_series(n=60)
    r = rsi(s)
    assert r.iloc[-1] > 60


def test_macd_columns():
    s = _rising_series()
    df = macd(s)
    assert set(df.columns) == {"macd", "signal", "hist"}


def test_bollinger_bands_ordering():
    s = pd.Series(100 + np.random.default_rng(0).normal(0, 1, 60))
    bb = bollinger_bands(s)
    valid = bb.dropna()
    assert (valid["upper"] >= valid["mid"]).all()
    assert (valid["mid"] >= valid["lower"]).all()


def test_volume_ratio_above_one_on_spike():
    vol = pd.Series([1_000_000] * 25 + [5_000_000])
    ratio = volume_ratio(vol)
    assert ratio.iloc[-1] > 1


def test_realized_vol_zero_for_flat_price():
    flat = pd.Series([100.0] * 30)
    rv = realized_vol(flat)
    assert rv.dropna().abs().max() < 1e-9


def test_made_new_high_true_on_fresh_breakout():
    s = pd.Series([100.0] * 9 + [110.0])  # today is a clean new 10-day high
    assert made_new_high(s, lookback=10, within_last=3) is True


def test_made_new_high_false_if_high_is_stale():
    # the high was set 5 sessions ago, price has since drifted down -- not
    # a fresh breakout even though it's technically still the 10-day high
    s = pd.Series([100.0, 110.0, 105.0, 104.0, 103.0, 102.0])
    assert made_new_high(s, lookback=6, within_last=3) is False


def test_made_new_high_false_with_insufficient_history():
    s = pd.Series([100.0, 101.0])
    assert made_new_high(s, lookback=10, within_last=3) is False


def test_made_new_low_true_on_fresh_breakdown():
    s = pd.Series([100.0] * 9 + [90.0])
    assert made_new_low(s, lookback=10, within_last=3) is True
