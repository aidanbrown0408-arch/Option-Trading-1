"""Trade construction: structure name -> option legs, per strategy-rules.md §5.

Directional only: long call, long put, debit call spread, debit put spread.

Delta targets are deliberately low (deep OTM) to fit a $2,500 account's
~$70-150/trade budget across $150-600+/share underlyings -- at the original
0.65 "behaves like stock" delta, a single contract on any of these tickers
costs $500-1900 (confirmed empirically: every trade was rejected). Delta is
roughly the probability of finishing in-the-money, so this is a real
tradeoff, not just a tuning knob: these are low-probability, high-payoff-if-
right trades, not the higher-win-rate "stock substitute" the original spec
assumed. See docs/strategy-rules.md §5.

  - Long call/put: single leg, 0.12 delta.
  - Debit spread: long leg 0.20 delta, short leg 0.10 delta (narrow width
    keeps cost down -- a wider, higher-delta spread reprices back into the
    $300-800+ range on the pricier names).
"""
from __future__ import annotations

from dataclasses import dataclass

from execution.options_pricing import CALL, PUT, Leg, strike_for_delta, structure_value
from signals.engine import DEBIT_SPREAD_CALL, DEBIT_SPREAD_PUT, LONG_CALL, LONG_PUT

LONG_OPTION_DELTA = 0.12
DEBIT_SPREAD_LONG_DELTA = 0.20
DEBIT_SPREAD_SHORT_DELTA = 0.10


@dataclass
class TradeCandidate:
    structure: str
    legs: list[Leg]
    entry_cost: float  # always positive here: net debit paid
    max_loss: float
    max_profit: float


def _debit_spread(S: float, T: float, r: float, sigma: float, kind: str) -> list[Leg]:
    long_k = strike_for_delta(S, T, r, sigma, kind, DEBIT_SPREAD_LONG_DELTA)
    short_k = strike_for_delta(S, T, r, sigma, kind, DEBIT_SPREAD_SHORT_DELTA)
    return [Leg(kind, +1, long_k), Leg(kind, -1, short_k)]


def build_trade(
    structure: str, S: float, T: float, r: float, sigma: float,
) -> TradeCandidate:
    if structure == LONG_CALL:
        legs = [Leg(CALL, +1, strike_for_delta(S, T, r, sigma, CALL, LONG_OPTION_DELTA))]
    elif structure == LONG_PUT:
        legs = [Leg(PUT, +1, strike_for_delta(S, T, r, sigma, PUT, LONG_OPTION_DELTA))]
    elif structure == DEBIT_SPREAD_CALL:
        legs = _debit_spread(S, T, r, sigma, CALL)
    elif structure == DEBIT_SPREAD_PUT:
        legs = _debit_spread(S, T, r, sigma, PUT)
    else:
        raise ValueError(f"unknown structure: {structure}")

    entry_cost = structure_value(legs, S, T, r, sigma)
    max_loss = entry_cost

    if structure in (LONG_CALL, LONG_PUT):
        max_profit = float("inf")
    else:
        width = abs(legs[0].strike - legs[1].strike)
        max_profit = width - entry_cost

    return TradeCandidate(structure=structure, legs=legs, entry_cost=entry_cost,
                           max_loss=max_loss, max_profit=max_profit)
