# execution

Trade construction (strike/expiry/structure selection) and the broker
adapter (Alpaca). Same interface for paper and live trading — mode is a
config flag, not a code fork.

Structures to support per `docs/strategy-rules.md` §4: debit spreads, long
straddles/strangles, credit spreads, iron condors, short strangles. Iron
condors are 4-leg orders — the Alpaca adapter needs to place/manage
multi-leg orders atomically, not as separate single-leg orders.
