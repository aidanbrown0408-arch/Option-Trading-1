import numpy as np
import pandas as pd

from signals.engine import (
    DEBIT_SPREAD_CALL,
    DEBIT_SPREAD_PUT,
    LONG_CALL,
    LONG_PUT,
    SignalRead,
    TREND_DOWN,
    TREND_RANGE,
    TREND_UP,
    classify_iv_regime,
    classify_trend,
    select_structure,
)


def test_classify_trend_uptrend():
    close = pd.Series(100 + np.arange(80) * 0.6)
    assert classify_trend(close) == TREND_UP


def test_classify_trend_downtrend():
    close = pd.Series(200 - np.arange(80) * 0.6)
    assert classify_trend(close) == TREND_DOWN


def test_classify_trend_short_series_is_range():
    close = pd.Series([100.0] * 10)
    assert classify_trend(close) == TREND_RANGE


def test_classify_iv_regime_threshold():
    assert classify_iv_regime(60) == "high"
    assert classify_iv_regime(40) == "low"
    assert classify_iv_regime(50) == "high"


def _read(**overrides) -> SignalRead:
    base = dict(
        date=pd.Timestamp("2024-01-01"), daily_trend=TREND_UP, weekly_trend=TREND_UP,
        trend=TREND_UP, rsi=55, macd_hist=1.0, macd_rising=True, bb_position="middle",
        volume_ratio=1.2, iv_regime="low", iv_rank=30,
    )
    base.update(overrides)
    return SignalRead(**base)


def test_select_structure_low_iv_uptrend_gives_long_call():
    r = _read()
    assert select_structure(r) == LONG_CALL


def test_select_structure_high_iv_uptrend_gives_debit_spread_call():
    r = _read(iv_regime="high")
    assert select_structure(r) == DEBIT_SPREAD_CALL


def test_select_structure_low_iv_downtrend_gives_long_put():
    r = _read(trend=TREND_DOWN, daily_trend=TREND_DOWN, weekly_trend=TREND_DOWN,
              rsi=45, macd_hist=-1.0, macd_rising=False)
    assert select_structure(r) == LONG_PUT


def test_select_structure_high_iv_downtrend_gives_debit_spread_put():
    r = _read(trend=TREND_DOWN, daily_trend=TREND_DOWN, weekly_trend=TREND_DOWN,
              rsi=45, macd_hist=-1.0, macd_rising=False, iv_regime="high")
    assert select_structure(r) == DEBIT_SPREAD_PUT


def test_select_structure_range_bound_returns_none():
    r = _read(trend=TREND_RANGE)
    assert select_structure(r) is None


def test_select_structure_no_momentum_confirmation_returns_none():
    r = _read(macd_hist=-0.1, macd_rising=False)  # trend up but momentum disagrees
    assert select_structure(r) is None


def test_select_structure_bb_edge_blocks_entry():
    r = _read(bb_position="lower")  # uptrend but price at lower band -> skip call
    assert select_structure(r) is None
