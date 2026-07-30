"""CLI entry point. Usage:

    python -m backtest.run_backtest --start 2023-01-01 --end 2026-06-30

Uses SyntheticDataProvider by default (see data/synthetic.py) since this
sandbox has no network access to Alpaca. Pass --source alpaca to use real
data once you have ALPACA_API_KEY/ALPACA_SECRET_KEY and network access.
"""
from __future__ import annotations

import argparse

import yaml

from backtest.engine import run_backtest
from backtest.metrics import print_report
from data.synthetic import SyntheticDataProvider


def load_watchlist(path: str = "config/watchlist.yaml") -> list[str]:
    with open(path) as f:
        return yaml.safe_load(f)["tickers"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2023-01-01")
    parser.add_argument("--end", default="2026-06-30")
    parser.add_argument("--source", default="synthetic", choices=["synthetic", "alpaca"])
    parser.add_argument("--equity", type=float, default=2_500.0)
    parser.add_argument("--verbose", action="store_true",
                         help="print every OPEN/CLOSE event as it happens")
    args = parser.parse_args()

    if args.source == "alpaca":
        from data.alpaca_provider import AlpacaDataProvider
        provider = AlpacaDataProvider()
    else:
        provider = SyntheticDataProvider()

    tickers = load_watchlist()
    result = run_backtest(tickers, provider, args.start, args.end, args.equity, verbose=args.verbose)
    print_report(result)


if __name__ == "__main__":
    main()
