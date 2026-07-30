from risk.manager import (
    MAX_CONCURRENT_POSITIONS,
    MAX_TRADE_COST_HARD_CAP,
    PortfolioState,
    approve_trade,
    size_for_trade,
)


def test_size_for_trade_targets_cost_midpoint():
    # $1.10/share -> $110/contract, right at the target midpoint -> 1 contract
    assert size_for_trade(max_loss_per_contract=1.10) == 1


def test_size_for_trade_scales_up_for_cheap_contracts():
    # $0.20/share -> $20/contract; should buy multiple to approach the target
    contracts = size_for_trade(max_loss_per_contract=0.20)
    assert contracts > 1
    assert contracts * 0.20 * 100 <= MAX_TRADE_COST_HARD_CAP


def test_size_for_trade_zero_when_even_one_contract_too_expensive():
    assert size_for_trade(max_loss_per_contract=5.0) == 0  # $500/contract


def test_size_for_trade_zero_for_non_positive_cost():
    assert size_for_trade(max_loss_per_contract=0) == 0


def test_approve_trade_rejects_duplicate_ticker():
    portfolio = PortfolioState(equity=2_500, start_of_day_equity=2_500, open_positions={"AAPL": object()})
    assert approve_trade("AAPL", 1.0, portfolio) == 0


def test_approve_trade_rejects_when_max_positions_reached():
    portfolio = PortfolioState(
        equity=2_500, start_of_day_equity=2_500,
        open_positions={f"T{i}": object() for i in range(MAX_CONCURRENT_POSITIONS)},
    )
    assert approve_trade("NEW", 1.0, portfolio) == 0


def test_approve_trade_rejects_on_circuit_breaker():
    portfolio = PortfolioState(equity=2_350, start_of_day_equity=2_500)
    assert approve_trade("AAPL", 1.0, portfolio) == 0


def test_approve_trade_allows_normal_case():
    portfolio = PortfolioState(equity=2_500, start_of_day_equity=2_500)
    assert approve_trade("AAPL", 1.0, portfolio) > 0
