"""Real data provider backed by Alpaca's Market Data API. Requires
ALPACA_API_KEY / ALPACA_SECRET_KEY env vars and network access to Alpaca
(neither is available in this sandbox — this is untested here; run it from
an environment that has both). See PLANNING.md §4 for the history-window
caveat: Alpaca's OPRA options history only goes back to ~early 2024.
"""
from __future__ import annotations

import os
from datetime import date as date_cls, timedelta

import pandas as pd

from data.provider import DataProvider, realized_vol_iv_rank_proxy


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
        self._daily_cache: dict[str, pd.DataFrame] = {}
        self._earnings_cache: dict[str, pd.DatetimeIndex] = {}

    def get_daily_bars(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        from alpaca.data.enums import DataFeed
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame

        # Free/basic Alpaca plans only have IEX feed access, not the default
        # SIP feed (SIP raises "subscription does not permit..."). IEX daily
        # bars are a fine proxy for a signal backtest even if you're on SIP.
        # Also clamp `end` to today - 1 day: SIP-only restrictions aside, you
        # can't request data past what actually exists yet.
        yesterday = (date_cls.today() - timedelta(days=1)).isoformat()
        end = min(end, yesterday)

        req = StockBarsRequest(
            symbol_or_symbols=ticker, timeframe=TimeFrame.Day, start=start, end=end,
            feed=DataFeed.IEX,
        )
        bars = self._client.get_stock_bars(req).df
        bars = bars.xs(ticker, level=0) if ticker in bars.index.get_level_values(0) else bars
        bars = bars[["open", "high", "low", "close", "volume"]]
        # Alpaca returns tz-aware (UTC) timestamps; the rest of the engine
        # (synthetic provider, backtest date range) is tz-naive, so strip tz
        # and normalize to the date to keep index lookups comparable.
        bars.index = bars.index.tz_convert("UTC").tz_localize(None).normalize()
        return bars

    def _get_full_daily(self, ticker: str) -> pd.DataFrame:
        # Alpaca's OPRA options history only starts ~early 2024 (PLANNING.md
        # §4), but equity bars go back much further, so this range is fine
        # for the realized-vol proxy below even outside the options window.
        if ticker not in self._daily_cache:
            self._daily_cache[ticker] = self.get_daily_bars(ticker, "2022-01-01", "2026-12-31")
        return self._daily_cache[ticker]

    def get_iv_rank(self, ticker: str, date: pd.Timestamp) -> float:
        # Alpaca's options data API returns current/live greeks per contract,
        # not a ready-made 1-year historical IV time series, so a full daily
        # options-chain replay to build real IV rank isn't practical for a
        # simple backtest. Same realized-vol-percentile proxy as
        # SyntheticDataProvider — see realized_vol_iv_rank_proxy's docstring
        # for why this is an approximation, not real IV.
        return realized_vol_iv_rank_proxy(self._get_full_daily(ticker), date)

    def is_earnings_window(self, ticker: str, date: pd.Timestamp, window_days: int = 5) -> bool:
        # Alpaca has no earnings calendar endpoint; using yfinance's (best
        # effort, not guaranteed complete/accurate). This filter is a v1
        # heuristic (strategy-rules.md §3), not a hard safety rule, so on any
        # lookup failure we fail OPEN (assume not near earnings) rather than
        # block trading entirely if the calendar source is unavailable.
        try:
            import yfinance as yf
        except ImportError:
            return False

        if ticker not in self._earnings_cache:
            try:
                dates = yf.Ticker(ticker).get_earnings_dates(limit=60)
                idx = pd.to_datetime(dates.index).tz_localize(None) if dates is not None else pd.DatetimeIndex([])
            except Exception:
                idx = pd.DatetimeIndex([])
            self._earnings_cache[ticker] = idx

        earnings_dates = self._earnings_cache[ticker]
        if len(earnings_dates) == 0:
            return False
        return bool((abs((earnings_dates - date).days) <= window_days).any())
