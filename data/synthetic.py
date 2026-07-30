"""Synthetic data provider: generates plausible daily OHLCV via regime-
switching GBM so the backtest engine can be exercised end-to-end without
real market data access. Not a substitute for a real backtest — see
PLANNING.md §4 and docs/strategy-rules.md §9 (stress-test on real data before
sizing up). Swap this for a real AlpacaDataProvider once you have API keys
and network access to Alpaca outside this sandbox.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from data.provider import DataProvider, realized_vol_iv_rank_proxy


class SyntheticDataProvider(DataProvider):
    def __init__(self, seed: int = 42):
        self._rng = np.random.default_rng(seed)
        self._cache: dict[str, pd.DataFrame] = {}

    def _generate(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        dates = pd.bdate_range(start, end)
        n = len(dates)
        rng = np.random.default_rng(abs(hash(ticker)) % (2**32) ^ 42)

        # Regime-switching drift/vol so trend + range-bound + high/low IV
        # periods all show up in the backtest, rather than pure random walk.
        regime_len = 40
        n_regimes = n // regime_len + 2
        drifts = rng.choice([0.0006, -0.0006, 0.0000], size=n_regimes, p=[0.35, 0.25, 0.40])
        vols = rng.choice([0.012, 0.022, 0.035], size=n_regimes, p=[0.4, 0.4, 0.2])

        daily_drift = np.repeat(drifts, regime_len)[:n]
        daily_vol = np.repeat(vols, regime_len)[:n]

        shocks = rng.normal(0, 1, n) * daily_vol + daily_drift
        log_price = np.cumsum(shocks) + np.log(150.0)
        close = np.exp(log_price)

        high = close * (1 + np.abs(rng.normal(0, 0.006, n)))
        low = close * (1 - np.abs(rng.normal(0, 0.006, n)))
        open_ = low + (high - low) * rng.uniform(0, 1, n)
        base_volume = rng.integers(3_000_000, 8_000_000, n)
        # volume spikes correlated with |shock| (breakout days trade heavier)
        volume = (base_volume * (1 + 3 * np.abs(shocks) / daily_vol.mean())).astype(int)

        df = pd.DataFrame(
            {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
            index=dates,
        )
        return df

    def _get_full(self, ticker: str) -> pd.DataFrame:
        if ticker not in self._cache:
            self._cache[ticker] = self._generate(ticker, "2022-01-01", "2026-06-30")
        return self._cache[ticker]

    def get_daily_bars(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        df = self._get_full(ticker)
        return df.loc[start:end]

    def get_iv_rank(self, ticker: str, date: pd.Timestamp) -> float:
        return realized_vol_iv_rank_proxy(self._get_full(ticker), date)

    def is_earnings_window(self, ticker: str, date: pd.Timestamp, window_days: int = 5) -> bool:
        # Deterministic pseudo-quarterly earnings: one ~63-trading-day cycle,
        # offset per ticker so tickers don't all report the same week.
        offset = abs(hash(ticker)) % 63
        trading_day = (date - pd.Timestamp("2022-01-03")).days
        cycle_pos = (trading_day + offset) % 63
        return cycle_pos < window_days
