import pytest

from execution.options_pricing import CALL, PUT, bs_delta, bs_price, strike_for_delta, structure_value, Leg


def test_call_price_positive_and_bounded():
    price = bs_price(S=100, K=100, T=0.1, r=0.045, sigma=0.25, kind=CALL)
    assert 0 < price < 100


def test_put_call_parity():
    S, K, T, r, sigma = 100, 105, 0.2, 0.04, 0.3
    call = bs_price(S, K, T, r, sigma, CALL)
    put = bs_price(S, K, T, r, sigma, PUT)
    import math
    lhs = call - put
    rhs = S - K * math.exp(-r * T)
    assert lhs == pytest.approx(rhs, abs=1e-6)


def test_delta_ranges():
    call_delta = bs_delta(100, 100, 0.2, 0.045, 0.25, CALL)
    put_delta = bs_delta(100, 100, 0.2, 0.045, 0.25, PUT)
    assert 0 <= call_delta <= 1
    assert -1 <= put_delta <= 0


def test_strike_for_delta_recovers_target():
    K = strike_for_delta(S=100, T=0.05, r=0.045, sigma=0.3, kind=CALL, target_delta=0.30)
    d = bs_delta(100, K, 0.05, 0.045, 0.3, CALL)
    assert d == pytest.approx(0.30, abs=0.01)


def test_structure_value_debit_spread_matches_manual():
    legs = [Leg(CALL, +1, 100), Leg(CALL, -1, 110)]
    val = structure_value(legs, S=105, T=0.1, r=0.045, sigma=0.25)
    manual = bs_price(105, 100, 0.1, 0.045, 0.25, CALL) - bs_price(105, 110, 0.1, 0.045, 0.25, CALL)
    assert val == pytest.approx(manual)
