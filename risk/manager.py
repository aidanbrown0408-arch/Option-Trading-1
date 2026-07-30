"""Portfolio/risk manager: sizing and exposure limits, per
docs/strategy-rules.md §5 and PLANNING.md §6. Every trade candidate must be
approved here before it can be opened."""
from __future__ import annotations

from dataclasses import dataclass, field

MAX_RISK_PCT = 0.02  # 1-2% of equity per trade; use the upper bound
MAX_CONCURRENT_POSITIONS = 5
DAILY_LOSS_CIRCUIT_BREAKER_PCT = 0.05


@dataclass
class PortfolioState:
    equity: float
    start_of_day_equity: float
    open_positions: dict = field(default_factory=dict)  # ticker -> position

    @property
    def daily_pnl_pct(self) -> float:
        return (self.equity - self.start_of_day_equity) / self.start_of_day_equity


def size_for_trade(equity: float, max_loss_per_contract: float) -> int:
    """Number of contracts such that total max loss <= MAX_RISK_PCT of equity.
    max_loss_per_contract is per-share; multiply by 100 for the contract."""
    if max_loss_per_contract <= 0:
        return 0
    risk_budget = equity * MAX_RISK_PCT
    contracts = int(risk_budget // (max_loss_per_contract * 100))
    return max(contracts, 0)


def approve_trade(ticker: str, max_loss_per_contract: float, portfolio: PortfolioState) -> int:
    """Returns the approved contract count (0 = rejected)."""
    if ticker in portfolio.open_positions:
        return 0
    if len(portfolio.open_positions) >= MAX_CONCURRENT_POSITIONS:
        return 0
    if portfolio.daily_pnl_pct <= -DAILY_LOSS_CIRCUIT_BREAKER_PCT:
        return 0
    return size_for_trade(portfolio.equity, max_loss_per_contract)
