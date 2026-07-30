# execution

Trade construction (strike/expiry/structure selection) and the broker
adapter (Alpaca). Same interface for paper and live trading — mode is a
config flag, not a code fork.

Structures to support per `docs/strategy-rules.md` §4: long call, long put,
debit call spread, debit put spread. All single-name, long-premium-only —
no multi-leg atomic order handling needed (a debit spread's two legs can be
placed as a standard vertical spread order type). Premium-selling structures
(credit spreads, iron condor) and straddles were dropped from scope; see
PLANNING.md §2 and `backtest/README.md` for why.
