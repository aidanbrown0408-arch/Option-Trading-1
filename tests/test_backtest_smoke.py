from backtest.engine import run_backtest
from backtest.metrics import summarize
from data.synthetic import SyntheticDataProvider


def test_backtest_runs_and_produces_equity_curve():
    provider = SyntheticDataProvider(seed=1)
    result = run_backtest(["AAPL", "SPY"], provider, "2023-01-01", "2023-06-30", starting_equity=50_000)
    assert len(result.equity_curve) > 0
    assert result.equity_curve.iloc[0] > 0


def test_backtest_summary_has_expected_keys_when_trades_exist():
    provider = SyntheticDataProvider(seed=1)
    result = run_backtest(["AAPL", "SPY", "TSLA", "QQQ"], provider, "2022-06-01", "2023-12-31")
    if result.trades:
        s = summarize(result)
        assert "win_rate" in s
        assert "max_drawdown_pct" in s
        assert s["num_trades"] == len(result.trades)
