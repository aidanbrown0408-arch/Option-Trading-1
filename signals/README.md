# signals

Signal engine: pure functions that take market data for a ticker and return
a directional signal (bullish/bearish/none) plus IV rank, per the rules in
`docs/strategy-rules.md`. No I/O, no broker calls — unit-testable in isolation.
