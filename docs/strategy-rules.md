# Strategy Rules v1 — Weekly / Bi-Weekly Options

Watchlist: `AAPL, MSFT, GOOGL, AMZN, META, TSLA, SPY, QQQ`
Expiration cycle: **weekly (7–10 DTE) or bi-weekly (14–17 DTE) only.**

This replaces the earlier "Standard tier" (30–45 DTE) approach — v1 is
short-term only. Every threshold below is a starting hypothesis, not a final
answer; the backtester is what validates or kills each one. This doc is
written to be directly codeable: each step below maps to a function in
`signals/` or `execution/`.

A few honest notes up front: weekly/bi-weekly options are high-gamma,
fast-decaying instruments — small misreads in timing or IV compress returns
quickly. The volatility and event-calendar checks (§3) matter as much as the
chart pattern (§1–2). Backtest through at least one low-IV period and one
surprise-gap event before sizing this up.

## 1. Trend context (per ticker, evaluated once per day at/after close)
- **Daily trend:** 20 EMA and 50 EMA slope + price position relative to both.
  Classified as `uptrend` / `downtrend` / `range-bound`.
- **Weekly trend (confirmation):** same read on the weekly chart. If daily and
  weekly disagree, classify as `range-bound` (ambiguous) rather than forcing a
  direction — don't fight the higher timeframe.
- **Key levels within the expiration window:** most recent swing high/low,
  round numbers, and a VWAP anchor (e.g. anchored VWAP from the last swing
  point). These become the candidate strike levels in §5.

## 2. Momentum & mean-reversion signals
- **RSI(14):** flag overbought (>70) / oversold (<30) / diverging from price
  (price makes new high/low, RSI doesn't confirm).
- **MACD(12,26,9):** crossover direction and whether the histogram is
  expanding or contracting.
- **Bollinger Bands (20, 2σ):** is price riding a band (momentum — trend
  continuation setup) or tagging a band edge and reverting (mean-reversion
  setup)? This distinction feeds directly into §4's strategy selection.
- **Volume vs. 20-day average:** confirming (≥1.2× avg on the trigger day) or
  diverging (move on light volume — lower conviction).

## 3. Volatility read (evaluated per ticker before any trade)
- **IV Rank / IV Percentile** (30–90 day lookback) for the underlying.
  - IV Rank/Percentile ≥ 50 → **high IV** regime.
  - IV Rank/Percentile < 50 → **low IV** regime.
- **Expected move** for the target expiration: read straight from the
  at-the-money straddle price on that expiration's chain.
- **Event calendar check:** earnings date, and (for SPY/QQQ) FOMC/CPI/NFP
  dates falling inside the expiration window.
  - Default v1 rule: **skip new entries within 5 trading days of a scheduled
    earnings date**, *unless* the setup is explicitly an earnings-IV-crush
    premium-selling trade (§4) sized and flagged as such — never treat an
    earnings-window trade as a normal directional trade.

## 4. Strategy selection (trend/momentum read × volatility regime)
| Setup | Structure | Notes |
|---|---|---|
| High IV + range-bound / mean-reversion (price at BB edge) | **Iron condor** or **short strangle** | Short strikes placed outside the expected move, at technical support/resistance from §1. |
| High IV + directional bias (clear trend, momentum confirming) | **Credit spread** (bull put spread in uptrend / bear call spread in downtrend) | Sold outside the expected move. |
| Low IV + strong directional signal (trend + momentum aligned, riding BB) | **Debit spread** (call or put) | Aligned with trend direction; caps cost vs. a naked long option. |
| Low IV + anticipated breakout ahead of a flagged catalyst | **Long straddle/strangle** | Only when a specific catalyst is inside the expiration window (§3) — not a default state. |
| Existing stock position | **Covered call** (at resistance) or **cash-secured put** (at support) | Only applies if/when the bot manages an underlying equity position — out of scope until execution module supports it. |

No trade if the volatility regime and trend/momentum read don't map cleanly
to a row above (e.g. high IV with no clear range or trend read) — skip
rather than force a structure.

## 5. Strike & risk parameters
- **Short strike placement** (condor/strangle/credit spread): outside the
  expected move (§3), at a technical level with confluence from §1 (e.g.
  prior swing level ≈ 1 standard deviation away).
- **Short strike delta target:** 0.15–0.25 for defined-risk premium selling.
- **Debit spread / long option delta:** long leg 0.60–0.70, short leg (if
  spread) 0.25–0.30 — deliberately less ITM-heavy than a pure directional
  long since these are the shorter (7–17 DTE) expirations from the top of
  this doc, not the old 30–45 DTE tier.
- **Max risk per trade:** 1–2% of account equity (net debit, or max loss on
  a defined-risk credit structure).
- **Liquidity filter:** skip the trade if bid/ask spread on any leg is wider
  than 10% of the mid price — weekly chains are often thinner than monthlies.

## 6. Trade management
- **Profit target:** close at 50% of max credit received (credit structures)
  or 50% of premium paid (debit structures / long premium).
- **Stop-loss / adjustment trigger:** close or adjust if the underlying
  breaches the short strike, or loss reaches 2× credit received (credit
  structures); close debit structures at −40% of premium paid.
- **DTE exit rule:** close or adjust at **21 DTE or 50% of max profit,
  whichever comes first** — for the bi-weekly cycle this is close to the
  midpoint of the trade's life; for the weekly cycle this effectively means
  managing well before expiration week gamma risk sets in. For structures
  entered at 7–10 DTE, treat this as **50% of max profit or 3 DTE**, whichever
  comes first, since 21 DTE isn't reachable.
- **Trend/momentum reversal exit:** close early if the §1/§2 read that
  justified entry flips (e.g. price closes back through the 20 EMA against
  the trade direction, or MACD crosses against the position).
- **Expiration handling:** close, don't let anything expire in-the-money
  untested — no assignment/exercise handling exists yet (see scope note
  below).

## 7. Post-trade log (per `journal/`)
Record per trade: entry date, structure, strike(s), credit/debit received or
paid, IV rank at entry, expected move at entry, exit date, P/L, exit reason
(profit target / stop / DTE rule / reversal / manual), and whether the
technical thesis (§1–2) actually played out — this last field is qualitative
but essential for pattern review over time, not just P/L.

## 8. Scope note vs. PLANNING.md
This version adds premium-selling structures (iron condor, short strangle,
credit spreads) that weren't in the original v1 scope (PLANNING.md §2, which
listed "long calls/puts, debit spreads" only and explicitly excluded
multi-leg volatility strategies and short-leg assignment handling). Before
building execution/risk logic for short legs, PLANNING.md needs a matching
update — flagged as a next step, not yet done.

## 9. What the backtester needs to measure
- Per-structure expectancy (condor vs. credit spread vs. debit spread vs.
  straddle) — which structures actually earn their complexity.
- Per-ticker performance (tech names vs. SPY/QQQ may behave very differently
  in a weekly-options context — SPY/QQQ likely favor premium-selling given
  typically lower realized vol; single names may favor debit spreads around
  idiosyncratic moves).
- Sensitivity of the 21-DTE/50%-profit management rule vs. simpler fixed
  profit targets.
- Explicit low-IV-period and gap-event stress tests, per the note in the
  intro — don't size this up on backtest results alone until both are run.
