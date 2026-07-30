"""Black-Scholes pricing used to simulate option prices/deltas for backtesting.

We don't have real historical options-chain data available (see data/README.md
and the Alpaca history-window caveat in PLANNING.md), so the backtester prices
each leg off the underlying price path + a modeled IV rather than replaying an
actual chain. This is an approximation: real chains have skew, wider
short-dated spreads, and discrete strikes. Treat backtest P&L as directional
signal, not a promise of live fill quality.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import exp, log, sqrt

from scipy.stats import norm

CALL = "call"
PUT = "put"


def _d1_d2(S: float, K: float, T: float, r: float, sigma: float) -> tuple[float, float]:
    T = max(T, 1e-6)
    sigma = max(sigma, 1e-4)
    d1 = (log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt(T))
    d2 = d1 - sigma * sqrt(T)
    return d1, d2


def bs_price(S: float, K: float, T: float, r: float, sigma: float, kind: str) -> float:
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    if kind == CALL:
        return S * norm.cdf(d1) - K * exp(-r * T) * norm.cdf(d2)
    return K * exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def bs_delta(S: float, K: float, T: float, r: float, sigma: float, kind: str) -> float:
    d1, _ = _d1_d2(S, K, T, r, sigma)
    return norm.cdf(d1) if kind == CALL else norm.cdf(d1) - 1


def strike_for_delta(
    S: float, T: float, r: float, sigma: float, kind: str, target_delta: float,
    lo_mult: float = 0.5, hi_mult: float = 1.8, tol: float = 1e-4, max_iter: int = 100,
) -> float:
    """Bisection search for the strike whose |delta| matches target_delta.

    Call |delta| decreases as strike increases (deeper OTM); put |delta|
    increases as strike increases (deeper ITM) — the two need opposite
    bisection directions.
    """
    target = abs(target_delta)
    lo, hi = S * lo_mult, S * hi_mult
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        d = abs(bs_delta(S, mid, T, r, sigma, kind))
        if abs(d - target) < tol:
            return mid
        d_decreasing_in_k = kind == CALL
        if (d > target) == d_decreasing_in_k:
            lo = mid
        else:
            hi = mid
    return mid


@dataclass(frozen=True)
class Leg:
    kind: str  # CALL | PUT
    side: int  # +1 long, -1 short
    strike: float

    def price(self, S: float, T: float, r: float, sigma: float) -> float:
        return bs_price(S, self.strike, T, r, sigma, self.kind)


def structure_value(legs: list[Leg], S: float, T: float, r: float, sigma: float) -> float:
    """Positive = structure is worth this much (mark), regardless of how it
    was entered (debit or credit)."""
    return sum(leg.side * leg.price(S, T, r, sigma) for leg in legs)
