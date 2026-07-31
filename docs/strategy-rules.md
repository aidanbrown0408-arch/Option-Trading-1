# Strategy Rules v1 — Weekly / Bi-Weekly Options

Watchlist: `AAPL, MSFT, GOOGL, AMZN, META, TSLA` (SPY/QQQ removed per user
decision).
Expiration cycle: **weekly (7–10 DTE) or bi-weekly (14–17 DTE) only.**
Account size: **~$2,500.**

**Exactly 3 structures, per user decision: long call, long put, iron
condor.** Iron condor was kept specifically because it's had the highest
win rate of any structure in every backtest run so far (72–79%). Everything
else that was ever tried is excluded:
- **`long_straddle` — excluded, proven wrong.** A real-data run showed it
  contributing 94% of total P&L at a 68.6% win rate, traced to our IV proxy
  (trailing realized vol — see `data/provider.py`) badly underpricing
  straddles ahead of real historical earnings jumps.
- **`debit_spread_call` — excluded, confirmed worst performer** on both
  real (-$1,967, 29.7% win) and synthetic data.
- **`debit_spread_put` / `credit_spread_bull_put` / `credit_spread_bear_call`
  — cut for scope**, not proven wrong, just outside the current 3-structure
  limit. See git history if reconsidering.

Every threshold below is a starting hypothesis, not a final answer; the
backtester is what validates or kills each one.

A few honest notes up front: weekly/bi-weekly options are high-gamma,
fast-decaying instruments — small misreads in timing compress returns
quickly. At a $2,500 account, a single contract on a higher-priced
underlying can cost more than the whole per-trade budget — see §5.

## 1. Trend context (per ticker, evaluated once per day at/after close)
- **Daily trend:** 20 EMA and 50 EMA slope + price position relative to both.
  Classified as `uptrend` / `downtrend` / `range-bound`.
- **Weekly trend (confirmation):** same read on the weekly chart. If daily and
  weekly disagree, classify as `range-bound` — don't fight the higher timeframe.
- **Trend strength:** (EMA20-EMA50)/EMA50 must be ≥1% (either direction) —
  a bare crossover can fire on a trend that's barely formed; this requires
  real separation between the two EMAs.
- **Breakout confirmation:** a new 10-day high (uptrend) / low (downtrend)
  set within the last 3 sessions. Speced in an earlier version of this doc
  but never wired into the code until the win-rate investigation (§9) —
  now a required gate.

## 2. Momentum & mean-reversion signals
- **Daily RSI(14):** ≥50 for a call-side entry, ≤50 for a put-side entry.
- **Weekly RSI(14):** must agree with the daily read (≥50 / ≤50) — added
  per user request for "multiple analysis confirming trade": a genuine
  multi-timeframe momentum confirmation, not just one indicator on one
  timeframe.
- **MACD(12,26,9):** crossover direction and whether the histogram is
  expanding or contracting.
- **Bollinger Bands (20, 2σ):** for directional entries, a guardrail — don't
  buy a call with price already tagging the upper band, or a put tagging
  the lower band. For the iron condor, the opposite: *requires* price at a
  band edge (that's the mean-reversion setup the structure is for).
- **Volume vs. 20-day average:** required ≥1.2× avg on the trigger day —
  computed since early versions of this doc but not actually enforced in
  code until the win-rate investigation; now a hard gate.

## 3. Volatility read (evaluated per ticker before any trade)
- **IV Rank / IV Percentile** (realized-vol proxy — see `data/provider.py`
  for the "why this is an approximation" caveat).
  - ≥50 → **high IV** regime.
  - <50 → **low IV** regime.
- **Directional entries (long call/put) require the LOW IV regime, full
  stop.** With no debit/credit spread left to absorb a high-IV entry's
  richer premium, allowing calls/puts in high IV means paying up with no
  structural edge to compensate. This was tested: allowing it diluted the
  win rate (see §9) despite every other filter being stricter. High-IV
  directional setups are now skipped entirely rather than traded worse.
- **Event calendar check:** skip new entries within 5 trading days of a
  scheduled earnings date, unconditionally.

## 4. Strategy selection (trend/momentum/breakout/volatility read)
| Setup | Structure |
|---|---|
| Uptrend + trend-strength + daily & weekly momentum + volume + fresh breakout + not at upper BB + **low IV** | **Long call** |
| Downtrend + trend-strength + daily & weekly momentum + volume + fresh breakdown + not at lower BB + **low IV** | **Long put** |
| Range-bound + high IV + price at a BB edge | **Iron condor** |
| Anything else (including any directional setup in high IV) | **No trade** |

## 5. Strike & risk parameters
- **Long call/put delta:** 0.12 (deep OTM).
- **Iron condor:** short legs 0.20 delta, protective long legs 0.10 delta.
  - **This is a real tradeoff, not just a tuning knob.** The original spec
    used 0.65 delta ("behaves like the stock," higher win rate). At 0.65
    delta, a single 7-10 DTE contract on any of these tickers costs
    $500-1900 — confirmed empirically when a real-data run produced **zero
    trades** because every candidate exceeded the affordability cap. Low
    delta is what makes trades affordable on a $2,500 account, but delta is
    roughly probability of profit for the long-premium side.
- **Position sizing — target cost, not %-of-equity:** target a total
  position cost of ~$70-150/trade by choosing contract count; reject if
  even 1 contract costs more than ~$200 (see `risk/manager.py`). Iron
  condor is sized by **max defined loss**, not premium received.
- **Cash accounting:** premium paid/received is debited/credited from
  spendable cash at entry and settled at exit — sizing checks against
  actual remaining cash, not just total account value (a real bug was
  caught and fixed here — see `risk/manager.py` module docstring).
- **Liquidity filter (not yet enforced in the backtester):** skip the trade
  if bid/ask spread on any leg is wider than 10% of the mid price. The
  current backtest prices everything at the theoretical Black-Scholes mid
  with zero slippage/commissions — optimistic; see `backtest/README.md`.

## 6. Trade management
**Long call/put:**
- Profit target: close at +50% of premium paid.
- Stop loss: close at −40% of premium paid.

**Iron condor:**
- Profit target: close at 50% of max credit captured.
- Stop loss: close if loss reaches 2× the credit received.

**Both:**
- DTE exit: close at 3 DTE regardless of P&L.
- Trend/momentum reversal exit: close early if the §1/§2 read that justified
  entry flips.

## 7. Post-trade log (per `journal/`)
Record per trade: entry date, structure, strike(s), premium paid/received,
IV rank at entry, exit date, P/L, exit reason, and whether the technical
thesis actually played out.

## 8. Win-rate policy
Per user decision: **any structure whose backtested win rate falls below
20% gets dropped from the selection matrix** — evaluate once enough trades
have accumulated to be statistically meaningful (2-3 trades tells you
nothing either way).

## 9. What changed to raise win rate, and why
Diagnosis (via the exit-reason breakdown in `backtest/metrics.py`) showed
almost every trade resolves via a clean profit-target or stop-loss hit,
essentially never via the DTE clock running out — so the 7-10 DTE window
isn't the bottleneck, entry quality is. Response, in order tried:
1. RSI tightened to ≥50/≤50, volume filter actually enforced, breakout
   confirmation wired in (was speced, never coded). Result: win rate
   33.6% (real-data baseline) → 41.8% (synthetic).
2. Scope cut to 3 structures (long call/put + iron condor) per user
   request, plus weekly-RSI and trend-strength confirmations added.
   Result on synthetic data: win rate dropped to 37.8% — investigated why.
3. **Found the cause:** without debit/credit spreads to route high-IV
   directional setups to, those setups were falling through to long
   call/put anyway, buying rich premium with no compensating edge. Gated
   long call/put to the low-IV regime only (§3). Result: win rate recovered
   to 42.3%, long_call specifically 34.1% → 40.0%, expectancy per trade
   $12.94 → $24.06 on the same synthetic sample.

## 10. What the backtester still needs to measure
- Per-ticker performance vs. $2,500 affordability (§5).
- Explicit low-IV-period and gap-event stress tests before trusting any
  positive expectancy shown here.
- Sensitivity to a real transaction-cost model once one exists — the
  current numbers assume zero slippage and zero commissions.
- Whether iron_condor's consistently high win rate holds up on real data
  with a larger sample (it's had as few as 2 trades in some runs).
