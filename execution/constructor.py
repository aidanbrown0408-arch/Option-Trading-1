"""Trade construction: structure name -> option legs, per strategy-rules.md §5.

Exactly 3 structures, per user decision: long call, long put, iron condor.
Debit/credit spreads dropped for scope (not proven wrong, just cut -- see
git history if reconsidering); long_straddle stays out (proven pricing
artifact, see signals/engine.py).

Delta targets for the long-premium side are deliberately low (deep OTM) to
fit a $2,500 account's ~$70-150/trade budget across $150-600+/share
underlyings -- at the original 0.65 "behaves like stock" delta, a single
contract on any of these tickers costs $500-1900 (confirmed empirically:
every trade was rejected). Delta is roughly the probability of finishing
in-the-money, so this is a real tradeoff, not just a tuning knob: these are
low-probability, high-payoff-if-right trades, not the higher-win-rate
"stock substitute" the original spec assumed. See docs/strategy-rules.md §5.

  - Long call/put: single leg, 0.12 delta.
  - Iron condor: short legs 0.20 delta, protective long legs 0.10 delta --
    defined-risk premium-selling, sized by max_loss rather than premium paid.
"""
from __future__ import annotations

from dataclasses import dataclass

from execution.options_pricing import CALL, PUT, Leg, strike_for_delta, structure_value
from signals.engine import IRON_CONDOR, LONG_CALL, LONG_PUT

LONG_OPTION_DELTA = 0.12
CREDIT_SHORT_DELTA = 0.20
CREDIT_LONG_DELTA = 0.10

CREDIT_STRUCTURES = (IRON_CONDOR,)


@dataclass
class TradeCandidate:
    structure: str
    legs: list[Leg]
    entry_cost: float  # positive = net debit paid; negative = net credit received
    max_loss: float
    max_profit: float


def _credit_spread(S: float, T: float, r: float, sigma: float, kind: str) -> list[Leg]:
    short_k = strike_for_delta(S, T, r, sigma, kind, CREDIT_SHORT_DELTA)
    long_k = strike_for_delta(S, T, r, sigma, kind, CREDIT_LONG_DELTA)
    return [Leg(kind, -1, short_k), Leg(kind, +1, long_k)]


def build_trade(
    structure: str, S: float, T: float, r: float, sigma: float,
) -> TradeCandidate:
    if structure == LONG_CALL:
        legs = [Leg(CALL, +1, strike_for_delta(S, T, r, sigma, CALL, LONG_OPTION_DELTA))]
    elif structure == LONG_PUT:
        legs = [Leg(PUT, +1, strike_for_delta(S, T, r, sigma, PUT, LONG_OPTION_DELTA))]
    elif structure == IRON_CONDOR:
        legs = _credit_spread(S, T, r, sigma, PUT) + _credit_spread(S, T, r, sigma, CALL)
    else:
        raise ValueError(f"unknown structure: {structure}")

    entry_cost = structure_value(legs, S, T, r, sigma)

    if structure in (LONG_CALL, LONG_PUT):
        max_loss = entry_cost
        max_profit = float("inf")
    else:  # iron condor
        credit = -entry_cost
        put_width = abs(legs[0].strike - legs[1].strike)
        call_width = abs(legs[2].strike - legs[3].strike)
        max_loss = max(put_width, call_width) - credit
        max_profit = credit

    return TradeCandidate(structure=structure, legs=legs, entry_cost=entry_cost,
                           max_loss=max_loss, max_profit=max_profit)
