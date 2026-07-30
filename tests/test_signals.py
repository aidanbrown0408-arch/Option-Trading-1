import numpy as np
import pandas as pd

from signals.engine import (
    CREDIT_SPREAD_BULL_PUT,
    DEBIT_SPREAD_PUT,
    IRON_CONDOR,
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
        volume_ratio=1.2, iv_regime="low", iv_rank=30, breakout_up=True, breakout_down=False,
    )
    base.update(overrides)
    return SignalRead(**base)


def _downtrend_overrides(**extra):
    base = dict(trend=TREND_DOWN, daily_trend=TREND_DOWN, weekly_trend=TREND_DOWN,
                rsi=45, macd_hist=-1.0, macd_rising=False, breakout_up=False, breakout_down=True)
    base.update(extra)
    return base


def test_select_structure_low_iv_uptrend_gives_long_call():
    r = _read()
    assert select_structure(r) == LONG_CALL


def test_select_structure_high_iv_uptrend_gives_credit_spread_bull_put():
    r = _read(iv_regime="high")
    assert select_structure(r) == CREDIT_SPREAD_BULL_PUT


def test_select_structure_low_iv_downtrend_gives_long_put():
    r = _read(**_downtrend_overrides())
    assert select_structure(r) == LONG_PUT


def test_select_structure_high_iv_downtrend_gives_debit_spread_put():
    r = _read(**_downtrend_overrides(iv_regime="high"))
    assert select_structure(r) == DEBIT_SPREAD_PUT


def test_select_structure_range_bound_low_iv_returns_none():
    r = _read(trend=TREND_RANGE, breakout_up=False)
    assert select_structure(r) is None


def test_select_structure_range_bound_high_iv_bb_edge_gives_iron_condor():
    r = _read(trend=TREND_RANGE, iv_regime="high", bb_position="upper", breakout_up=False)
    assert select_structure(r) == IRON_CONDOR


def test_select_structure_range_bound_high_iv_middle_bb_returns_none():
    r = _read(trend=TREND_RANGE, iv_regime="high", bb_position="middle", breakout_up=False)
    assert select_structure(r) is None


def test_select_structure_no_momentum_confirmation_returns_none():
    r = _read(macd_hist=-0.1, macd_rising=False)  # trend up but momentum disagrees
    assert select_structure(r) is None


def test_select_structure_bb_edge_blocks_entry():
    r = _read(bb_position="lower")  # uptrend but price at lower band -> skip call
    assert select_structure(r) is None


def test_select_structure_low_volume_blocks_entry():
    r = _read(volume_ratio=0.9)  # trend + momentum confirm, but no volume confirmation
    assert select_structure(r) is None


def test_select_structure_weak_rsi_blocks_entry():
    r = _read(rsi=48)  # uptrend + momentum, but RSI below the 50 conviction threshold
    assert select_structure(r) is None


def test_select_structure_no_breakout_blocks_entry():
    r = _read(breakout_up=False)  # trend + momentum + volume confirm, but no fresh breakout
    assert select_structure(r) is None
