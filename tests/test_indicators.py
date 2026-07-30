import numpy as np
import pandas as pd

from signals.indicators import bollinger_bands, ema, macd, rsi, volume_ratio, realized_vol


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
