# Strategy Rules v1 — Directional Trend Options

Watchlist: `AAPL, MSFT, GOOGL, AMZN, META, TSLA, SPY, QQQ`

These rules are written to be directly codeable and backtestable. Every
threshold below is a starting hypothesis, not a final answer — the backtester
(phase 3) is what validates or kills each one.

## 1. Signal (per ticker, evaluated once per day at/after close)
Bullish setup — all must hold:
- Price > 50-day SMA > 200-day SMA (uptrend + trend alignment).
- 14-day RSI between 45 and 70 (momentum present, not overbought).
- Price made a new 10-day high within the last 3 sessions (trigger).

Bearish setup — mirror image (Price < 50 SMA < 200 SMA, RSI 30–55, new 10-day
low within 3 sessions).

No trade if neither setup is met, or if both a bullish and bearish condition
partially trigger (ambiguous).

## 2. Volatility filter
- Compute IV rank (current IV vs. 1-year range) for the underlying.
- Only enter **long options** (calls/puts) if IV rank < 40 (cheaper premium,
  avoid buying into a vol crush).
- If IV rank ≥ 40, switch structure to a **debit spread** (buy ATM/near-ATM,
  sell further OTM same expiration) to reduce vega/theta exposure — same
  directional bet, capped cost.

## 3. Trade construction
- Expiration: 30–45 days to expiration (DTE) at entry — enough time for the
  thesis to play out, decay still manageable.
- Strike (long option leg): delta ~0.60–0.70 (in-the-money-ish, behaves more
  like stock, less theta-sensitive than ATM/OTM).
- Debit spread short leg: delta ~0.25–0.30 on the same expiration.
- Position size: risk (premium paid, or net debit) capped at 1–2% of account
  equity per trade (see risk defaults in PLANNING.md §6).
- Skip the trade if the bid/ask spread on the chosen contract is wider than
  10% of the mid price (execution quality filter).

## 4. Exit rules (checked daily; whichever hits first)
- **Profit target:** close at +75% of the premium paid (long option) or +60%
  of max profit (debit spread).
- **Stop loss:** close at −40% of premium paid.
- **Time stop:** close at 10 DTE regardless of P&L (avoid late-cycle theta decay).
- **Thesis invalidation:** close if price closes back below the 50-day SMA
  (bullish trade) / above the 50-day SMA (bearish trade) — the trend that
  justified the entry is gone.

## 5. Portfolio-level constraints
- Max 1 open position per ticker at a time (no pyramiding in v1).
- Max concurrent positions across the whole watchlist: 5.
- No new entries if the account is down >5% for the day (circuit breaker).

## 6. What the backtester needs to measure
- Per-rule contribution: win rate/expectancy with the IV filter on vs. off,
  with the trend filter on vs. off — so we know which rules are load-bearing.
- Per-ticker performance (tech names vs. SPY/QQQ may behave very differently).
- Sensitivity to the profit target / stop loss / DTE thresholds (a simple
  parameter sweep) before locking in v1 defaults.

## 7. Open questions to revisit after first backtest results
- Should SPY/QQQ (index/ETF, lower realized vol) use different thresholds
  than single-name tech stocks?
- Is the 45-day-max DTE window wide enough given earnings dates? (Earnings
  handling — trade through vs. avoid — is not yet specified; default for v1
  is to **skip new entries within 5 trading days of a scheduled earnings
  date** to avoid IV-crush risk until this is explicitly backtested.)
