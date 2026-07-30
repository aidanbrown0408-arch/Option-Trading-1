# Strategy Rules v1 — Directional Long Options (Weekly / Bi-Weekly)

Watchlist: `AAPL, MSFT, GOOGL, AMZN, META, TSLA, SPY, QQQ`
Expiration cycle: **weekly (7–10 DTE) or bi-weekly (14–17 DTE) only.**
Account size: **~$2,500.** Structures: **long calls, long puts, and debit
spreads only** — no premium selling (credit spreads/iron condor) and no
long-vol catalyst plays (straddle/strangle). Those were tried and dropped:
they needed real historical options IV data we don't have, and the
backtester showed the straddle P&L was dominated by an unvalidated IV-markup
assumption rather than real edge (see PLANNING.md history / git log for
that finding).

Every threshold below is a starting hypothesis, not a final answer; the
backtester is what validates or kills each one. This doc is written to be
directly codeable: each step below maps to a function in `signals/` or
`execution/`.

A few honest notes up front: weekly/bi-weekly options are high-gamma,
fast-decaying instruments — small misreads in timing compress returns
quickly. At a $2,500 account, a single contract on a higher-priced
underlying (TSLA, MSFT) can cost more than the whole per-trade budget below
— see §5's affordability note, this is a real, structural constraint, not a
bug to route around.

## 1. Trend context (per ticker, evaluated once per day at/after close)
- **Daily trend:** 20 EMA and 50 EMA slope + price position relative to both.
  Classified as `uptrend` / `downtrend` / `range-bound`.
- **Weekly trend (confirmation):** same read on the weekly chart. If daily and
  weekly disagree, classify as `range-bound` (ambiguous) rather than forcing a
  direction — don't fight the higher timeframe.

## 2. Momentum & mean-reversion signals
- **RSI(14):** flag overbought (>70) / oversold (<30) / diverging from price
  (price makes new high/low, RSI doesn't confirm).
- **MACD(12,26,9):** crossover direction and whether the histogram is
  expanding or contracting.
- **Bollinger Bands (20, 2σ):** used only as a guardrail — don't buy a call
  with price already tagging the upper band (mean-reversion risk against
  you), or a put tagging the lower band.
- **Volume vs. 20-day average:** confirming (≥1.2× avg on the trigger day) or
  diverging (move on light volume — lower conviction).

## 3. Volatility read (evaluated per ticker before any trade)
- **IV Rank / IV Percentile** (30–90 day lookback, realized-vol proxy — see
  `data/provider.py`) for the underlying.
  - IV Rank/Percentile ≥ 50 → **high IV** regime → use a **debit spread**
    (cap cost vs. a naked long option in a richer-premium environment).
  - IV Rank/Percentile < 50 → **low IV** regime → a plain **long call/put**
    is cheap enough to buy outright.
- **Event calendar check:** skip new entries within 5 trading days of a
  scheduled earnings date, unconditionally — no earnings-play carve-out in
  this version (that was the straddle/catalyst path, now removed).

## 4. Strategy selection (trend/momentum read × volatility regime)
| Setup | Structure |
|---|---|
| Uptrend + momentum confirms + not at upper BB | Low IV → **long call**; High IV → **debit call spread** |
| Downtrend + momentum confirms + not at lower BB | Low IV → **long put**; High IV → **debit put spread** |
| Anything else (range-bound, momentum disagrees, or price at the BB edge against the trade) | **No trade** |

## 5. Strike & risk parameters
- **Long call/put delta:** 0.65 (in-the-money-ish, less theta-sensitive than
  ATM/OTM, behaves more like the stock).
- **Debit spread:** long leg 0.65 delta, short leg 0.28 delta.
- **Position sizing — target cost, not %-of-equity:** at $2,500, the
  standard "1-2% of equity per trade" rule ($25-50) is smaller than a single
  contract typically costs, which would reject almost every trade. Instead,
  target a **total position cost of roughly $70-150 per trade** (doesn't
  need to land exactly in that range) by choosing contract count; reject the
  trade outright if even 1 contract costs more than ~$200 (see
  `risk/manager.py`).
  - **Consequence, not a bug:** at these delta targets, higher-priced names
    (TSLA, MSFT, and often SPY/QQQ) frequently cost more than $200 for even
    1 contract and will simply not trade until the account is bigger. This
    was confirmed empirically in a backtest run and left as-is by choice —
    see §8.
- **Liquidity filter (not yet enforced in the backtester):** skip the trade
  if bid/ask spread on any leg is wider than 10% of the mid price — weekly
  chains are often thinner than monthlies. The current backtest prices
  everything at the theoretical Black-Scholes mid with zero slippage/
  commissions, which is optimistic; see `backtest/README.md`.

## 6. Trade management
- **Profit target:** close at +50% of premium paid.
- **Stop loss:** close at −40% of premium paid.
- **DTE exit rule:** close at 3 DTE regardless of P&L (gamma risk near
  expiration in a 7-10 DTE trade is severe).
- **Trend/momentum reversal exit:** close early if the §1/§2 read that
  justified entry flips (e.g. price closes back through the 20 EMA against
  the trade direction).
- **Expiration handling:** close, don't let anything expire in-the-money
  untested — no assignment/exercise handling exists (not needed for long
  options, but still: always close before expiration in practice).

## 7. Post-trade log (per `journal/`)
Record per trade: entry date, structure, strike(s), premium paid, IV rank at
entry, exit date, P/L, exit reason (profit target / stop / DTE rule /
reversal / manual), and whether the technical thesis (§1-2) actually played
out — qualitative, but essential for pattern review over time, not just P/L.

## 8. What the backtester needs to measure
- Per-structure expectancy (long call/put vs. debit spread) — does the
  cheaper, capped-cost debit spread actually outperform the naked long
  option in the high-IV regime it's meant for?
- Per-ticker performance, with an explicit eye on which tickers actually get
  enough trades to be affordable at $2,500 (see §5) — track this so the
  watchlist decision (leave excluded / widen deltas / trim watchlist) can be
  revisited data-driven once the account size changes.
- Explicit low-IV-period and gap-event stress tests before trusting any
  positive expectancy shown here.
- Sensitivity to a real transaction-cost model once one exists (see
  `backtest/README.md`) — the current numbers assume zero slippage and zero
  commissions, which is optimistic for a small account trading thin weekly
  chains.
