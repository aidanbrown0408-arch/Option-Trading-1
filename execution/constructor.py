"""Trade construction: structure name -> option legs, per strategy-rules.md §5.

Delta targets:
  - Debit spread: long leg 0.65 delta, short leg 0.28 delta.
  - Credit spread: short leg 0.20 delta, protective long leg 0.10 delta.
  - Iron condor: bull put spread + bear call spread, both legs per credit spread deltas.
  - Long straddle: both legs ATM (delta ~0.50 call / -0.50 put).
"""
from __future__ import annotations

from dataclasses import dataclass

from execution.options_pricing import CALL, PUT, Leg, strike_for_delta, structure_value
from signals.engine import (
    CREDIT_SPREAD_BEAR_CALL,
    CREDIT_SPREAD_BULL_PUT,
    DEBIT_SPREAD_CALL,
    DEBIT_SPREAD_PUT,
    IRON_CONDOR,
    LONG_STRADDLE,
)

LONG_DELTA = 0.65
SHORT_DELTA = 0.28
CREDIT_SHORT_DELTA = 0.20
CREDIT_LONG_DELTA = 0.10


@dataclass
class TradeCandidate:
    structure: str
    legs: list[Leg]
    entry_cost: float  # positive = net debit paid, negative = net credit received
    max_loss: float
    max_profit: float


def _debit_spread(S: float, T: float, r: float, sigma: float, kind: str) -> list[Leg]:
    long_k = strike_for_delta(S, T, r, sigma, kind, LONG_DELTA)
    short_k = strike_for_delta(S, T, r, sigma, kind, SHORT_DELTA)
    return [Leg(kind, +1, long_k), Leg(kind, -1, short_k)]


def _credit_spread(S: float, T: float, r: float, sigma: float, kind: str) -> list[Leg]:
    short_k = strike_for_delta(S, T, r, sigma, kind, CREDIT_SHORT_DELTA)
    long_k = strike_for_delta(S, T, r, sigma, kind, CREDIT_LONG_DELTA)
    return [Leg(kind, -1, short_k), Leg(kind, +1, long_k)]


def build_trade(
    structure: str, S: float, T: float, r: float, sigma: float,
) -> TradeCandidate:
    if structure == DEBIT_SPREAD_CALL:
        legs = _debit_spread(S, T, r, sigma, CALL)
    elif structure == DEBIT_SPREAD_PUT:
        legs = _debit_spread(S, T, r, sigma, PUT)
    elif structure == CREDIT_SPREAD_BULL_PUT:
        legs = _credit_spread(S, T, r, sigma, PUT)
    elif structure == CREDIT_SPREAD_BEAR_CALL:
        legs = _credit_spread(S, T, r, sigma, CALL)
    elif structure == IRON_CONDOR:
        legs = _credit_spread(S, T, r, sigma, PUT) + _credit_spread(S, T, r, sigma, CALL)
    elif structure == LONG_STRADDLE:
        atm_call = strike_for_delta(S, T, r, sigma, CALL, 0.50)
        atm_put = strike_for_delta(S, T, r, sigma, PUT, 0.50)
        legs = [Leg(CALL, +1, atm_call), Leg(PUT, +1, atm_put)]
    else:
        raise ValueError(f"unknown structure: {structure}")

    entry_cost = structure_value(legs, S, T, r, sigma)
    is_debit = structure in (DEBIT_SPREAD_CALL, DEBIT_SPREAD_PUT, LONG_STRADDLE)

    if is_debit:
        max_loss = entry_cost
        if structure == LONG_STRADDLE:
            max_profit = float("inf")
        else:
            width = abs(legs[0].strike - legs[1].strike)
            max_profit = width - entry_cost
    else:
        credit = -entry_cost
        if structure == IRON_CONDOR:
            put_width = abs(legs[0].strike - legs[1].strike)
            call_width = abs(legs[2].strike - legs[3].strike)
            max_loss = max(put_width, call_width) - credit
        else:
            width = abs(legs[0].strike - legs[1].strike)
            max_loss = width - credit
        max_profit = credit

    return TradeCandidate(structure=structure, legs=legs, entry_cost=entry_cost,
                           max_loss=max_loss, max_profit=max_profit)
