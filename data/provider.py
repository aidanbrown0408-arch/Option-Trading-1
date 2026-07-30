"""Data layer interface (PLANNING.md §5). Any source (Alpaca, synthetic,
later Polygon/ORATS) implements this so downstream modules never know which
one they're talking to."""
from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from signals.indicators import realized_vol


def realized_vol_iv_rank_proxy(daily: pd.DataFrame, date: pd.Timestamp) -> float:
    """IV rank proxy: percentile rank of current realized vol within its own
    1-year trailing history. Used when a real historical IV surface isn't
    available (see execution/options_pricing.py caveat) — real option IV
    tends to run richer than realized vol and reacts faster to upcoming
    events, so this under/overstates IV rank around catalysts. Replace with
    a real IV history source before trusting sizing decisions on it."""
    window = daily.loc[:date].tail(252)
    if len(window) < 40:
        return 50.0
    rv = realized_vol(window["close"])
    current = rv.iloc[-1]
    history = rv.dropna()
    if len(history) < 20 or pd.isna(current):
        return 50.0
    return float((history < current).mean() * 100)


class DataProvider(ABC):
    @abstractmethod
    def get_daily_bars(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        """Returns a DataFrame indexed by date with columns
        open/high/low/close/volume."""

    @abstractmethod
    def get_iv_rank(self, ticker: str, date: pd.Timestamp) -> float:
        """Returns IV rank/percentile (0-100) for the underlying as of `date`."""

    @abstractmethod
    def is_earnings_window(self, ticker: str, date: pd.Timestamp, window_days: int = 5) -> bool:
        """True if `date` falls within `window_days` trading days of a
        scheduled earnings date."""
