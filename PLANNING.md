# Options Trading Bot — Project Plan

## 1. Goal
Build a bot that trades **directional options strategies** (long calls/puts, debit
spreads) across a **watchlist of tickers**, progressing from research →
backtest → paper trading → live trading.

## 2. Scope (v1)
- **Account size: ~$2,500.** Sizing is target-cost-based (~$70-150/trade),
  not %-of-equity — see §6 and `docs/strategy-rules.md` §5.
- **Short-term only:** weekly (7–10 DTE) and bi-weekly (14–17 DTE) expirations —
  no 30–45 DTE "standard" tier (dropped from the original plan).
- **Directional long premium only: long calls, long puts, and debit spreads.**
  Premium-selling (credit spreads, iron condor) and long-vol catalyst plays
  (straddle/strangle) were tried and dropped — they needed real historical
  options IV we don't have, and a real-data backtest showed the straddle
  result was dominated by an unvalidated IV-markup assumption, not real edge.
- Watchlist-driven scanning: evaluate each ticker once per day at/after close.
- Signal generation from trend (daily/weekly EMA), momentum (RSI, MACD,
  Bollinger Bands), and volatility (IV rank/percentile) — see
  `docs/strategy-rules.md` for the full spec.
- Trade construction: strategy selected from a trend/momentum × IV-regime
  matrix — long call/put in the low-IV regime, debit spread in the high-IV
  regime.
- Risk management: target-cost position sizing, profit-target/stop-loss/
  DTE-exit rules, max concurrent positions, daily loss circuit breaker.
- Execution via broker API in **paper mode** first, live mode gated behind a flag.
- Logging, trade journal, and performance reporting.

Out of scope for v1: any short-premium/defined-risk structure (credit
spreads, iron condor, covered calls, cash-secured puts — the last two also
need an equity-position manager execution doesn't have), long-vol catalyst
plays (straddle/strangle), assignment/exercise handling (not needed for pure
long options), multi-account support.

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

## 4. Decisions
| Question | Decision | Notes |
|---|---|---|
| Broker/API | **Alpaca** | Paper + live trading, single API for equities and options orders. |
| Historical options data source | **Alpaca Options Market Data API** (to start) | Same API key as execution, simplest stack. Caveat: Alpaca's OPRA options history only goes back to ~early 2024, so backtests are limited to that window. If we need a longer lookback later, add Polygon.io or ORATS as a second source behind the same data-layer interface — the rest of the system won't need to change. |
| Language/runtime | **Python** | pandas, alpaca-py SDK, good options/quant library support. |
| Watchlist | **AAPL, MSFT, GOOGL, AMZN, META, TSLA, SPY, QQQ** | 6 large-cap tech names + 2 broad-market ETFs. All highly liquid options chains, tight spreads — good for directional strategies. |
| Signal approach | Rules-based (MA/RSI/trend) for v1 | Explainable and backtestable; ML can come later. |
| Scheduling | Scheduled polling (e.g. daily, or hourly during market hours) | Simplest to reason about and backtest; can move to streaming later. |

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
- Position sizing targets a total cost of ~$70-150 per trade (not %-of-equity
  — at $2,500, the usual 1-2% rule is smaller than a single contract often
  costs). Reject the trade if even 1 contract costs more than ~$200.
  Consequence: higher-priced names (TSLA, MSFT, often SPY/QQQ) may not trade
  at all at current delta targets — confirmed in backtest, left as-is.
- Max concurrent positions: 5.
- Hard stop-loss at −40% of premium paid; profit target at +50% of premium
  paid; DTE exit at 3 days remaining.
- Daily loss circuit breaker: halt new entries if daily drawdown exceeds 5%.

## 7. Immediate next steps
1. ~~Confirm broker + data provider~~ — done, see §4.
2. Write `docs/strategy-rules.md` with concrete, codeable entry/exit rules. ✅
3. Scaffold repo structure (`data/`, `signals/`, `execution/`, `risk/`,
   `backtest/`, `config/`, `tests/`). ✅
4. Build the backtester first — no live/paper trading until a strategy shows
   a positive expectancy historically.
