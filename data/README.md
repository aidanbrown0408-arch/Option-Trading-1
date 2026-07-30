# data

Data layer: fetches historical bars/options chains for backtesting, and
live quotes/chains for signal generation and execution.

v1 source: Alpaca Options Market Data API (see PLANNING.md §4). Interface
should be source-agnostic so a second provider (e.g. Polygon.io) can be
added later without touching downstream modules.
