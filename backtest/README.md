# backtest

Backtesting engine: replays signals + trade construction + risk manager over
historical data (no broker adapter involved). Must be built and show
positive expectancy before any paper/live trading begins.

Run: `python -m backtest.run_backtest --start 2022-06-01 --end 2026-06-30`
(default `--equity` is now $2,500, `--source synthetic` by default).

Uses `data/synthetic.py` by default — this sandbox has no network access to
Alpaca, so options prices are simulated via Black-Scholes off a synthetic
regime-switching price path rather than replayed from a real chain (see
`execution/options_pricing.py` docstring for the caveat). Real validation
requires `--source alpaca` with real API keys/network access outside this
sandbox — that's been run and is what drove two scope changes below.

Scope history worth knowing before trusting any number this prints:
- v1 originally included credit spreads, iron condor, and long straddles.
  A real-data run showed long straddle contributing ~94% of total P&L at a
  68.6% win rate — implausible for long premium, and traced to our IV proxy
  (trailing realized vol) badly underpricing straddles ahead of real
  historical earnings jumps, since real markets price in an IV run-up
  ahead of earnings that realized vol can't see coming. **v1 has since been
  narrowed to long calls, long puts, and debit spreads only** — see
  `docs/strategy-rules.md`.
- Position sizing changed from %-of-equity to a target-cost model (~$70-150
  per trade) once the account size was set to $2,500 — see `risk/manager.py`
  and PLANNING.md §6. At the original 0.65 delta this excluded every ticker
  entirely (a real run produced zero trades — every contract cost $500+).
  Delta targets were dropped to 0.12 (long call/put) and 0.20/0.10 (debit
  spread) to fit the budget — see `docs/strategy-rules.md` §5 for the
  resulting win-rate/risk-profile tradeoff (deep OTM = lower probability of
  profit, bigger payoff when right).
- No transaction-cost model exists yet: every fill is at the theoretical
  Black-Scholes mid, with zero slippage/commissions. Real weekly-options
  spreads are often 5-15% wide, so real returns will be lower than shown
  here. Worth adding before trusting a number for paper trading.
