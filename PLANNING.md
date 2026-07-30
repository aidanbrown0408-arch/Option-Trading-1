# Options Trading Bot — Project Plan

## 1. Goal
Build a bot that trades **directional options strategies** (long calls/puts, debit
spreads) across a **watchlist of tickers**, progressing from research →
backtest → paper trading → live trading.

## 2. Scope (v1)
- Watchlist-driven scanning: evaluate each ticker on a schedule (e.g. daily/hourly).
- Directional signal generation (technical + optional fundamental/IV filters).
- Trade construction: choose expiration, strike, and structure (long option vs.
  debit spread) based on signal strength, IV rank, and cost.
- Risk management: position sizing, max loss per trade, max portfolio risk,
  stop-loss / profit-target rules, max concurrent positions.
- Execution via broker API in **paper mode** first, live mode gated behind a flag.
- Logging, trade journal, and performance reporting.

Out of scope for v1: multi-leg volatility strategies (straddles/condors),
assignment/exercise handling for short legs, multi-account support.

## 3. Phases
1. **Requirements & strategy spec** (this doc + `docs/strategy-rules.md`)
   - Define entry/exit signals precisely enough to code and backtest.
2. **Data layer**
   - Historical price + options chain data source (for backtesting).
   - Live/delayed quote + options chain source (for signal generation & execution).
3. **Backtesting engine**
   - Simulate the strategy over historical data before risking capital.
   - Report: win rate, avg win/loss, max drawdown, Sharpe, per-ticker breakdown.
4. **Signal & trade-construction module**
   - Pure functions: given market data → trade candidate (or no-op).
   - Unit-testable independent of broker/data plumbing.
5. **Broker integration (paper mode)**
   - Order placement, position tracking, account state sync.
6. **Risk & portfolio manager**
   - Enforces sizing/exposure limits before any order reaches the broker.
7. **Paper trading run**
   - Run the full loop live against paper account for a defined trial period.
8. **Live trading (opt-in, small size)**
   - Same code path as paper, switched via config, starting with minimal size.
9. **Monitoring & reporting**
   - Trade log, daily P&L summary, alerting on errors/risk breaches.

## 4. Decisions needed before coding starts
| Question | Options | Notes |
|---|---|---|
| Broker/API | Tastytrade, Interactive Brokers, Alpaca (options), Tradier | Determines auth, order & chain-data APIs available |
| Historical options data source | CBOE DataShop, ORATS, Polygon.io, broker's own history | Needed for backtesting realistic fills/greeks |
| Language/runtime | Python (pandas, broker SDKs) recommended | Best library support for options/quant work |
| Watchlist composition | Fixed list vs. screened dynamically | Start fixed (e.g. 10–20 liquid large-cap/ETF names) |
| Signal approach | Rules-based (MA/RSI/trend) vs. ML | Start rules-based for v1, explainable & backtestable |
| Scheduling | Cron/polling vs. event-driven (webhooks/streaming) | Start with scheduled polling, simplest to reason about |

## 5. Proposed architecture
```
watchlist config ─┐
                   ▼
            [ Data Layer ] ── quotes, chains, historical bars
                   ▼
          [ Signal Engine ] ── per-ticker directional signal
                   ▼
      [ Trade Constructor ] ── pick strike/expiry/structure
                   ▼
      [ Risk Manager ] ── sizing, exposure limits, approve/reject
                   ▼
      [ Broker Adapter ] ── paper or live execution
                   ▼
      [ Journal / Reporting ] ── trade log, P&L, alerts
```
Each stage is a separate module with a narrow interface, so the backtester can
reuse Signal Engine + Trade Constructor + Risk Manager without touching the
broker adapter.

## 6. Risk management defaults (tune later)
- Max risk per trade: 1–2% of account equity.
- Max concurrent positions: 5–8.
- Max sector/ticker concentration: e.g. no more than 2 positions per ticker.
- Hard stop-loss at defined % of premium paid; profit target at defined % gain.
- Daily loss circuit breaker: halt new entries if daily drawdown exceeds X%.

## 7. Immediate next steps
1. Confirm broker + data provider (drives everything downstream) — see §4.
2. Write `docs/strategy-rules.md` with concrete, codeable entry/exit rules.
3. Scaffold repo structure (`data/`, `signals/`, `execution/`, `risk/`,
   `backtest/`, `config/`, `tests/`).
4. Build the backtester first — no live/paper trading until a strategy shows
   a positive expectancy historically.
