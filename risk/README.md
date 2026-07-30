# risk

Portfolio/risk manager: position sizing, exposure limits, and the daily
circuit breaker. Sits between the trade constructor and the broker adapter —
every order must be approved here first (see PLANNING.md §6).

For short-premium structures (credit spreads, iron condors, short strangles),
sizing is based on max defined loss, not premium paid — the risk manager
needs to compute this per-structure rather than assuming "risk = debit paid."
