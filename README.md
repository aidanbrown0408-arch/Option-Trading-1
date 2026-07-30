# Option-Trading-1

A directional-options trading bot: watchlist-driven signal generation, trade
construction, and risk-managed execution via Alpaca — backtest first, then
paper trade, then live.

See [`PLANNING.md`](PLANNING.md) for the project plan and architecture, and
[`docs/strategy-rules.md`](docs/strategy-rules.md) for the concrete v1
strategy rules.

## Status
Planning phase — no trading logic implemented yet. Repo is scaffolded per the
architecture in PLANNING.md §5:

- `config/` — watchlist and strategy parameters
- `data/` — historical + live market data (Alpaca Options Market Data API)
- `signals/` — directional signal engine
- `execution/` — trade construction + broker adapter (Alpaca)
- `risk/` — position sizing and exposure limits
- `backtest/` — backtesting engine (build this first)
- `journal/` — trade log and reporting

## Setup
```
pip install -r requirements.txt
```
Alpaca API keys will be read from environment variables
(`ALPACA_API_KEY`, `ALPACA_SECRET_KEY`) once the broker adapter is
implemented — paper trading keys only until the strategy is validated.
