# Strategy Rules v1 — Weekly / Bi-Weekly Options

Watchlist: `AAPL, MSFT, GOOGL, AMZN, META, TSLA, SPY, QQQ`
Expiration cycle: **weekly (7–10 DTE) or bi-weekly (14–17 DTE) only.**
Account size: **~$2,500.**

Structures in play: **long call, long put, debit put spread, credit spreads
(bull put / bear call), iron condor.** Two structures are deliberately
excluded, for different reasons:
- **`long_straddle` — excluded, proven wrong.** A real-data run showed it
  contributing 94% of total P&L at a 68.6% win rate, traced to our IV proxy
  (trailing realized vol — see `data/provider.py`) badly underpricing
  straddles ahead of real historical earnings jumps. Not real edge.
- **`debit_spread_call` — excluded, confirmed worst performer.** Consistently
  the worst structure on both real (-$1,967, 29.7% win) and synthetic
  (-$403, 33% win) data. No replacement in that slot for a directional,
  low-IV uptrend — the high-IV uptrend slot is filled by `credit_spread_bull_put`.

**Open caveat on what's back in:** credit spreads and iron condor share the
same unvalidated-IV-proxy risk that got straddle removed — they were never
individually proven wrong the way straddle was, so they're included, but
don't treat their backtest numbers as more trustworthy than straddle's were
before that got caught. Watch for the same pattern (suspiciously high win
rate concentrated in one structure) before trusting real-data results.

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
  weekly disagree, classify as `range-bound` (ambiguous) rather than forcing a
  direction — don't fight the higher timeframe.
- **Breakout confirmation:** a new 10-day high (uptrend) / low (downtrend)
  set within the last 3 sessions. Speced in the original version of this doc
  but never actually wired into the code until the win-rate investigation
  below — now a required gate, not just a nice-to-have.

## 2. Momentum & mean-reversion signals
- **RSI(14):** require ≥50 for a call-side entry, ≤50 for a put-side entry
  (tightened from an earlier ≥45/≤55 — see §9).
- **MACD(12,26,9):** crossover direction and whether the histogram is
  expanding or contracting.
- **Bollinger Bands (20, 2σ):** for directional entries, a guardrail — don't
  buy a call with price already tagging the upper band (mean-reversion risk
  against you), or a put tagging the lower band. For the iron condor, the
  opposite: *requires* price at a band edge (that's the mean-reversion setup
  the structure is meant for).
- **Volume vs. 20-day average:** required ≥1.2× avg on the trigger day —
  this was computed but not actually enforced in the code until the same
  investigation; now a hard gate, not optional.

## 3. Volatility read (evaluated per ticker before any trade)
- **IV Rank / IV Percentile** (realized-vol proxy — see `data/provider.py`
  for the "why this is an approximation" caveat).
  - ≥50 → **high IV** regime.
  - <50 → **low IV** regime.
- **Event calendar check:** skip new entries within 5 trading days of a
  scheduled earnings date, unconditionally.

## 4. Strategy selection (trend/momentum/breakout read × volatility regime)
| Setup | Structure |
|---|---|
| Uptrend + momentum + volume + fresh breakout + not at upper BB | Low IV → **long call**; High IV → **credit spread (bull put)** |
| Downtrend + momentum + volume + fresh breakdown + not at lower BB | Low IV → **long put**; High IV → **debit put spread** |
| Range-bound + high IV + price at a BB edge | **Iron condor** |
| Anything else | **No trade** |

## 5. Strike & risk parameters
- **Long call/put delta:** 0.12 (deep OTM).
- **Debit put spread:** long leg 0.20 delta, short leg 0.10 delta.
- **Credit spread / iron condor:** short leg 0.20 delta, protective long leg
  0.10 delta.
  - **This is a real tradeoff, not just a tuning knob.** The original spec
    used 0.65 delta ("behaves like the stock," higher win rate). At 0.65
    delta, a single 7-10 DTE contract on any of these 8 tickers costs
    $500-1900 — confirmed empirically when a real-data run produced **zero
    trades** because every candidate exceeded the affordability cap. Low
    delta is what makes trades affordable on a $2,500 account, but delta is
    roughly probability of profit for the long-premium side — expect a
    lower win rate than a "stock substitute" design would give.
- **Position sizing — target cost, not %-of-equity:** target a total
  position cost of ~$70-150/trade by choosing contract count; reject if
  even 1 contract costs more than ~$200 (see `risk/manager.py`). Credit
  structures are sized by **max defined loss**, not premium received (a
  credit spread's risk isn't the credit collected, it's the spread width
  minus that credit).
- **Cash accounting:** premium paid/received is debited/credited from
  spendable cash at entry and settled at exit — sizing checks against
  actual remaining cash, not just total account value, so it can't approve
  a trade whose cost is already tied up in other open positions. (This was
  a real bug, caught via an impossible -111% backtest drawdown before the
  fix — see `risk/manager.py` module docstring.)
- **Liquidity filter (not yet enforced in the backtester):** skip the trade
  if bid/ask spread on any leg is wider than 10% of the mid price. The
  current backtest prices everything at the theoretical Black-Scholes mid
  with zero slippage/commissions — optimistic; see `backtest/README.md`.

## 6. Trade management
**Long-premium (long call/put, debit spread):**
- Profit target: close at +50% of premium paid.
- Stop loss: close at −40% of premium paid.

**Credit structures (credit spread, iron condor):**
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
20% gets dropped from the selection matrix** (§4) — evaluate this whenever
enough trades have accumulated to be statistically meaningful (a structure
with 2-3 trades total, win or lose, tells you almost nothing; wait for a
real sample before acting on this rule for a given structure).

## 9. What changed to raise win rate, and why
Earlier versions of this doc used looser entry criteria (RSI ≥45/≤55, no
breakout requirement, no volume enforcement) and a 65.6%→33.6% win rate
range showed up across synthetic/real runs. Diagnosis (via the exit-reason
breakdown in `backtest/metrics.py`) showed **almost every trade resolves
via a clean profit-target or stop-loss hit, essentially never via the DTE
clock running out** — so the 7-10 DTE window isn't the bottleneck, entry
quality is. Response: require RSI ≥50/≤50 (not just weakly non-negative),
enforce the volume filter that was computed but never checked, and add the
originally-speced-but-unwired breakout confirmation. Fewer, higher-
conviction entries — trades less often, by design.

## 10. What the backtester still needs to measure
- Per-structure expectancy now that credit spreads/iron condor are back —
  watch specifically for the same "one structure dominates P&L with a
  suspiciously clean win rate" pattern that flagged straddle as an artifact.
- Per-ticker performance vs. $2,500 affordability (§5).
- Explicit low-IV-period and gap-event stress tests before trusting any
  positive expectancy shown here.
- Sensitivity to a real transaction-cost model once one exists — the
  current numbers assume zero slippage and zero commissions.
