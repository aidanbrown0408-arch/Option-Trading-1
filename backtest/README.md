# backtest

Backtesting engine: replays signals + trade construction + risk manager over
historical data (no broker adapter involved). Must be built and show
positive expectancy before any paper/live trading begins.

Run: `python -m backtest.run_backtest --start 2022-06-01 --end 2026-06-30`

Uses `data/synthetic.py` by default — this sandbox has no network access to
Alpaca, so options prices are simulated via Black-Scholes off a synthetic
regime-switching price path rather than replayed from a real chain (see
`execution/options_pricing.py` docstring for the caveat). Current synthetic
run: 714 trades, 56.6% win rate, ~breakeven expectancy ($1.02/trade), -19%
max drawdown — essentially noise, which is expected from synthetic data with
no real edge baked in. This does NOT validate the strategy; it validates
that the engine runs correctly end-to-end. Real validation requires
`--source alpaca` with real API keys/network access outside this sandbox.
