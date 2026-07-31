import pytest

from execution.constructor import build_trade
from signals.engine import IRON_CONDOR, LONG_CALL, LONG_PUT

S, T, r, sigma = 100.0, 10 / 365, 0.045, 0.28


def test_long_call_is_single_leg_debit_unbounded_profit():
    trade = build_trade(LONG_CALL, S, T, r, sigma)
    assert len(trade.legs) == 1
    assert trade.entry_cost > 0
    assert trade.max_loss == pytest.approx(trade.entry_cost)
    assert trade.max_profit == float("inf")


def test_long_put_is_single_leg_debit_unbounded_profit():
    trade = build_trade(LONG_PUT, S, T, r, sigma)
    assert len(trade.legs) == 1
    assert trade.entry_cost > 0
    assert trade.max_profit == float("inf")


def test_iron_condor_has_four_legs_and_capped_loss():
    trade = build_trade(IRON_CONDOR, S, T, r, sigma)
    assert len(trade.legs) == 4
    assert trade.entry_cost < 0  # net credit
    assert trade.max_loss > 0


def test_unknown_structure_raises():
    with pytest.raises(ValueError):
        build_trade("debit_spread_put", S, T, r, sigma)
