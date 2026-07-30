"""Real data provider backed by Alpaca's Market Data API. Requires
ALPACA_API_KEY / ALPACA_SECRET_KEY env vars and network access to Alpaca
(neither is available in this sandbox — this is untested here; run it from
an environment that has both). See PLANNING.md §4 for the history-window
caveat: Alpaca's OPRA options history only goes back to ~early 2024.
"""
from __future__ import annotations

import os

import pandas as pd

from data.provider import DataProvider


class AlpacaDataProvider(DataProvider):
    def __init__(self):
        try:
            from alpaca.data.historical import StockHistoricalDataClient
        except ImportError as e:
            raise ImportError("pip install alpaca-py to use AlpacaDataProvider") from e

        api_key = os.environ.get("ALPACA_API_KEY")
        secret_key = os.environ.get("ALPACA_SECRET_KEY")
        if not api_key or not secret_key:
            raise RuntimeError("Set ALPACA_API_KEY / ALPACA_SECRET_KEY env vars")

        self._client = StockHistoricalDataClient(api_key, secret_key)

    def get_daily_bars(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame

        req = StockBarsRequest(
            symbol_or_symbols=ticker, timeframe=TimeFrame.Day, start=start, end=end,
        )
        bars = self._client.get_stock_bars(req).df
        bars = bars.xs(ticker, level=0) if ticker in bars.index.get_level_values(0) else bars
        bars = bars[["open", "high", "low", "close", "volume"]]
        # Alpaca returns tz-aware (UTC) timestamps; the rest of the engine
        # (synthetic provider, backtest date range) is tz-naive, so strip tz
        # and normalize to the date to keep index lookups comparable.
        bars.index = bars.index.tz_convert("UTC").tz_localize(None).normalize()
        return bars

    def get_iv_rank(self, ticker: str, date: pd.Timestamp) -> float:
        # TODO: derive from Alpaca Options Market Data API (chain IV history)
        # once available; not implemented/tested in this sandbox.
        raise NotImplementedError("IV rank from Alpaca options data not yet implemented")

    def is_earnings_window(self, ticker: str, date: pd.Timestamp, window_days: int = 5) -> bool:
        # TODO: source an earnings calendar (Alpaca corporate actions API or
        # a separate calendar provider) — not implemented/tested here.
        raise NotImplementedError("Earnings calendar lookup not yet implemented")
