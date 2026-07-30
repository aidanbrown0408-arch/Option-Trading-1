# risk

Portfolio/risk manager: position sizing, exposure limits, and the daily
circuit breaker. Sits between the trade constructor and the broker adapter —
every order must be approved here first (see PLANNING.md §6).

All structures in scope (long call/put, debit spread) are long-premium, so
max loss == premium paid — no separate defined-loss calc needed (that was
only relevant for the now-dropped credit spreads/iron condor).

Sizing is target-cost-based (~$70-150/trade), not %-of-equity — see the
module docstring for why a small ($2,500) account needs this instead of the
usual 1-2%-of-equity rule.
