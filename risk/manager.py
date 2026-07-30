"""Portfolio/risk manager: sizing and exposure limits, per
docs/strategy-rules.md §5 and PLANNING.md §6. Every trade candidate must be
approved here before it can be opened.

Sizing is target-cost-based, not %-of-equity: for a small account (~$2.5k),
1-2% of equity ($25-50) is often less than a single contract costs, which
would reject nearly every trade on affordable underlyings. Instead we target
a per-trade dollar cost of roughly $70-150 (doesn't need to land exactly in
that band) by choosing a contract count, and reject only if even 1 contract
blows past the hard cap below.

`equity` on PortfolioState is spendable cash, not "total account value": it
gets debited by the premium paid when a position opens and credited by the
proceeds when it closes (see backtest/engine.py). Without this, sizing could
approve a trade whose cost was already tied up in other open positions,
letting simulated equity go negative -- a real bug found via an impossible
-111% max drawdown in a backtest run. `total_equity()` adds back the cost
basis of currently-open positions so merely opening a trade doesn't look
like a loss for circuit-breaker/reporting purposes.
"""
from __future__ import annotations

from dataclasses import dataclass, field

TARGET_TRADE_COST_LOW = 70.0
TARGET_TRADE_COST_HIGH = 150.0
TARGET_TRADE_COST_MID = (TARGET_TRADE_COST_LOW + TARGET_TRADE_COST_HIGH) / 2
MAX_TRADE_COST_HARD_CAP = 200.0  # reject if even 1 contract costs more than this

MAX_CONCURRENT_POSITIONS = 5
DAILY_LOSS_CIRCUIT_BREAKER_PCT = 0.05


@dataclass
class PortfolioState:
    equity: float  # spendable cash
    start_of_day_equity: float  # total_equity() snapshot at start of day
    open_positions: dict = field(default_factory=dict)  # ticker -> position
    # each open_positions value must expose `.contracts` and
    # `.candidate.entry_cost` (backtest.engine.OpenPosition satisfies this;
    # not imported here to avoid a circular import).

    def total_equity(self) -> float:
        committed = sum(p.candidate.entry_cost * p.contracts * 100 for p in self.open_positions.values())
        return self.equity + committed

    @property
    def daily_pnl_pct(self) -> float:
        return (self.total_equity() - self.start_of_day_equity) / self.start_of_day_equity


def size_for_trade(max_loss_per_contract: float, available_cash: float) -> int:
    """Number of contracts targeting a total cost near TARGET_TRADE_COST_MID,
    never exceeding available_cash. max_loss_per_contract is per-share; the
    contract (x100 shares) is what's actually bought/sold."""
    per_contract_cost = max_loss_per_contract * 100
    if per_contract_cost <= 0 or per_contract_cost > MAX_TRADE_COST_HARD_CAP:
        return 0

    contracts = max(1, round(TARGET_TRADE_COST_MID / per_contract_cost))
    while contracts > 1 and contracts * per_contract_cost > MAX_TRADE_COST_HARD_CAP:
        contracts -= 1
    while contracts > 0 and contracts * per_contract_cost > available_cash:
        contracts -= 1
    return contracts


def approve_trade(ticker: str, max_loss_per_contract: float, portfolio: PortfolioState) -> int:
    """Returns the approved contract count (0 = rejected)."""
    if ticker in portfolio.open_positions:
        return 0
    if len(portfolio.open_positions) >= MAX_CONCURRENT_POSITIONS:
        return 0
    if portfolio.daily_pnl_pct <= -DAILY_LOSS_CIRCUIT_BREAKER_PCT:
        return 0
    return size_for_trade(max_loss_per_contract, portfolio.equity)
