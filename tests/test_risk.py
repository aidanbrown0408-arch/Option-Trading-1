from risk.manager import MAX_CONCURRENT_POSITIONS, PortfolioState, approve_trade, size_for_trade


def test_size_for_trade_respects_risk_budget():
    contracts = size_for_trade(equity=100_000, max_loss_per_contract=5.0)
    assert contracts == int((100_000 * 0.02) // 500)
    assert contracts > 0


def test_size_for_trade_zero_when_loss_too_large():
    assert size_for_trade(equity=1_000, max_loss_per_contract=50.0) == 0


def test_approve_trade_rejects_duplicate_ticker():
    portfolio = PortfolioState(equity=100_000, start_of_day_equity=100_000, open_positions={"AAPL": object()})
    assert approve_trade("AAPL", 2.0, portfolio) == 0


def test_approve_trade_rejects_when_max_positions_reached():
    portfolio = PortfolioState(
        equity=100_000, start_of_day_equity=100_000,
        open_positions={f"T{i}": object() for i in range(MAX_CONCURRENT_POSITIONS)},
    )
    assert approve_trade("NEW", 2.0, portfolio) == 0


def test_approve_trade_rejects_on_circuit_breaker():
    portfolio = PortfolioState(equity=94_000, start_of_day_equity=100_000)
    assert approve_trade("AAPL", 2.0, portfolio) == 0


def test_approve_trade_allows_normal_case():
    portfolio = PortfolioState(equity=100_000, start_of_day_equity=100_000)
    assert approve_trade("AAPL", 2.0, portfolio) > 0
