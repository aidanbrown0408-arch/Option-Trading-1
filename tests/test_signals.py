import numpy as np
import pandas as pd

from signals.engine import (
    CREDIT_SPREAD_BULL_PUT,
    DEBIT_SPREAD_CALL,
    IRON_CONDOR,
    LONG_STRADDLE,
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


def test_select_structure_low_iv_uptrend_gives_debit_call():
    r = _read()
    assert select_structure(r, catalyst_flagged=False) == DEBIT_SPREAD_CALL


def test_select_structure_high_iv_uptrend_gives_credit_spread():
    r = _read(iv_regime="high")
    assert select_structure(r, catalyst_flagged=False) == CREDIT_SPREAD_BULL_PUT


def test_select_structure_high_iv_range_bb_edge_gives_condor():
    r = _read(trend=TREND_RANGE, iv_regime="high", bb_position="upper", macd_hist=0, macd_rising=False)
    assert select_structure(r, catalyst_flagged=False) == IRON_CONDOR


def test_select_structure_catalyst_low_iv_gives_straddle():
    r = _read(iv_regime="low")
    assert select_structure(r, catalyst_flagged=True) == LONG_STRADDLE


def test_select_structure_no_clean_match_returns_none():
    r = _read(trend=TREND_RANGE, iv_regime="low", bb_position="middle", macd_hist=0, macd_rising=False, rsi=50)
    assert select_structure(r, catalyst_flagged=False) is None
