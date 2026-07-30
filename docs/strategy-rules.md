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

### 1a. Signal strength tier (determines expiration — see §3)
A setup that meets the base criteria above is **Standard** tier by default.
It is upgraded to **Fast** tier only if, in addition, ALL of the following hold:
- The breakout is a new **20-day** high/low (not just 10-day) within the last
  2 sessions — a stronger, more decisive move.
- Volume on the trigger day ≥ 1.5× the 20-day average volume (conviction behind
  the move).
- RSI has accelerated: today's RSI is at least 5 points higher than 3 sessions
  ago (bullish) / 5 points lower (bearish) — momentum is building, not stalling.

Fast tier is meant for short-fuse, high-conviction moves; Standard tier is the
default slower trend-following case. A setup that fails any Fast-tier
condition simply trades as Standard — it is never rejected for failing to
upgrade.

## 2. Volatility filter
- Compute IV rank (current IV vs. 1-year range) for the underlying.
- Only enter **long options** (calls/puts) if IV rank < 40 (cheaper premium,
  avoid buying into a vol crush).
- If IV rank ≥ 40, switch structure to a **debit spread** (buy ATM/near-ATM,
  sell further OTM same expiration) to reduce vega/theta exposure — same
  directional bet, capped cost.

## 3. Trade construction
Expiration and strikes depend on the signal tier from §1a. Both tiers still
go through the same IV-rank filter (§2) and the same position sizing / spread
filter below.

**Standard tier (default — 30–45 DTE):**
- Expiration: 30–45 DTE at entry — enough time for the thesis to play out,
  decay still manageable.
- Strike (long option leg): delta ~0.60–0.70 (in-the-money-ish, behaves more
  like stock, less theta-sensitive than ATM/OTM).
- Debit spread short leg: delta ~0.25–0.30 on the same expiration.

**Fast tier (7–14 DTE, weekly/bi-weekly):**
- Expiration: nearest weekly or bi-weekly expiration with **at least 7 DTE**
  at entry (never enter with <7 DTE — too little room for error).
- Strike (long option leg): delta ~0.75–0.85 (deeper ITM than Standard tier —
  short-dated options need to behave more like stock to survive the faster
  theta decay).
- Debit spread short leg: delta ~0.35–0.40 on the same expiration.
- Fast tier is skipped entirely if IV rank ≥ 40 and no liquid weekly/bi-weekly
  spread can be built with acceptable bid/ask width — in that case, fall back
  to Standard tier rather than force a bad fill.

**Both tiers:**
- Position size: risk (premium paid, or net debit) capped at 1–2% of account
  equity per trade (see risk defaults in PLANNING.md §6).
- Skip the trade if the bid/ask spread on the chosen contract is wider than
  10% of the mid price (execution quality filter) — this filter is stricter
  in practice for Fast tier, since weekly chains are often thinner.

## 4. Exit rules (checked daily; whichever hits first)

**Standard tier:**
- **Profit target:** close at +75% of the premium paid (long option) or +60%
  of max profit (debit spread).
- **Stop loss:** close at −40% of premium paid.
- **Time stop:** close at 10 DTE regardless of P&L (avoid late-cycle theta decay).
- **Thesis invalidation:** close if price closes back below the 50-day SMA
  (bullish trade) / above the 50-day SMA (bearish trade) — the trend that
  justified the entry is gone.

**Fast tier:**
- **Profit target:** close at +50% of the premium paid (long option) or +45%
  of max profit (debit spread) — take the win sooner, theta is working harder
  against you.
- **Stop loss:** close at −35% of premium paid (tighter than Standard —
  less time for a thesis to recover).
- **Time stop:** close at 3 DTE regardless of P&L (weekly/bi-weekly gamma
  risk near expiration is severe).
- **Thesis invalidation:** same rule as Standard (50-day SMA break).

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
  date** to avoid IV-crush risk until this is explicitly backtested.) This
  applies to both tiers, but matters most for Fast tier — a 7–14 DTE trade
  has almost no room to absorb an earnings-driven IV crush.
- Does the Fast-tier upgrade (§1a) actually add expectancy, or does the
  tighter stop/faster time-stop just cut winners short? This is exactly the
  kind of question the backtester should answer by running Standard-only vs.
  Standard+Fast side by side.
