"""Data layer interface (PLANNING.md §5). Any source (Alpaca, synthetic,
later Polygon/ORATS) implements this so downstream modules never know which
one they're talking to."""
from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


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
