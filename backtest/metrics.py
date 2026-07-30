"""Performance metrics for a BacktestResult, per PLANNING.md §3."""
from __future__ import annotations

import numpy as np
import pandas as pd

from backtest.engine import BacktestResult


def summarize(result: BacktestResult) -> dict:
    trades = result.trades
    curve = result.equity_curve

    if not trades:
        return {"num_trades": 0}

    pnls = np.array([t.pnl for t in trades])
    wins = pnls[pnls > 0]
    losses = pnls[pnls <= 0]
    win_rate = len(wins) / len(pnls)
    avg_win = wins.mean() if len(wins) else 0.0
    avg_loss = losses.mean() if len(losses) else 0.0
    expectancy = pnls.mean()

    daily_ret = curve.pct_change().dropna()
    sharpe = (daily_ret.mean() / daily_ret.std() * np.sqrt(252)) if daily_ret.std() > 0 else 0.0

    running_max = curve.cummax()
    drawdown = (curve - running_max) / running_max
    max_drawdown = drawdown.min()

    total_return = (curve.iloc[-1] - curve.iloc[0]) / curve.iloc[0]

    by_structure = {}
    for t in trades:
        by_structure.setdefault(t.structure, []).append(t.pnl)
    structure_summary = {
        s: {"num_trades": len(p), "total_pnl": float(np.sum(p)), "win_rate": float(np.mean(np.array(p) > 0))}
        for s, p in by_structure.items()
    }

    by_ticker = {}
    for t in trades:
        by_ticker.setdefault(t.ticker, []).append(t.pnl)
    ticker_summary = {
        tk: {"num_trades": len(p), "total_pnl": float(np.sum(p))}
        for tk, p in by_ticker.items()
    }

    return {
        "num_trades": len(trades),
        "win_rate": float(win_rate),
        "avg_win": float(avg_win),
        "avg_loss": float(avg_loss),
        "expectancy_per_trade": float(expectancy),
        "total_pnl": float(pnls.sum()),
        "total_return_pct": float(total_return * 100),
        "sharpe": float(sharpe),
        "max_drawdown_pct": float(max_drawdown * 100),
        "by_structure": structure_summary,
        "by_ticker": ticker_summary,
    }


def print_report(result: BacktestResult) -> None:
    s = summarize(result)
    if s["num_trades"] == 0:
        print("No trades were opened during the backtest window.")
        return

    print("=== Backtest Summary ===")
    print(f"Trades:          {s['num_trades']}")
    print(f"Win rate:        {s['win_rate']:.1%}")
    print(f"Avg win:         ${s['avg_win']:.2f}")
    print(f"Avg loss:        ${s['avg_loss']:.2f}")
    print(f"Expectancy/trade:${s['expectancy_per_trade']:.2f}")
    print(f"Total P&L:       ${s['total_pnl']:.2f}")
    print(f"Total return:    {s['total_return_pct']:.2f}%")
    print(f"Sharpe:          {s['sharpe']:.2f}")
    print(f"Max drawdown:    {s['max_drawdown_pct']:.2f}%")

    print("\n--- By structure ---")
    for struct, d in s["by_structure"].items():
        print(f"{struct:28s} n={d['num_trades']:4d}  win_rate={d['win_rate']:.1%}  total_pnl=${d['total_pnl']:.2f}")

    print("\n--- By ticker ---")
    for tk, d in s["by_ticker"].items():
        print(f"{tk:6s} n={d['num_trades']:4d}  total_pnl=${d['total_pnl']:.2f}")
