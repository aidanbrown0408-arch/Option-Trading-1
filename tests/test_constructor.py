import pytest

from execution.constructor import build_trade
from signals.engine import CREDIT_SPREAD_BULL_PUT, DEBIT_SPREAD_CALL, IRON_CONDOR, LONG_STRADDLE

S, T, r, sigma = 100.0, 10 / 365, 0.045, 0.28


def test_debit_spread_call_is_net_debit_and_capped_loss():
    trade = build_trade(DEBIT_SPREAD_CALL, S, T, r, sigma)
    assert trade.entry_cost > 0
    assert trade.max_loss == pytest.approx(trade.entry_cost)
    assert trade.max_profit > 0


def test_credit_spread_is_net_credit_and_capped_loss():
    trade = build_trade(CREDIT_SPREAD_BULL_PUT, S, T, r, sigma)
    assert trade.entry_cost < 0
    assert trade.max_profit == pytest.approx(-trade.entry_cost)
    assert trade.max_loss > 0


def test_iron_condor_has_four_legs_and_capped_loss():
    trade = build_trade(IRON_CONDOR, S, T, r, sigma)
    assert len(trade.legs) == 4
    assert trade.max_loss > 0
    assert trade.entry_cost < 0  # net credit


def test_long_straddle_is_debit_with_unbounded_profit():
    trade = build_trade(LONG_STRADDLE, S, T, r, sigma)
    assert trade.entry_cost > 0
    assert trade.max_profit == float("inf")
