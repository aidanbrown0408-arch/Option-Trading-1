# risk

Portfolio/risk manager: position sizing, exposure limits, and the daily
circuit breaker. Sits between the trade constructor and the broker adapter —
every order must be approved here first (see PLANNING.md §6).
