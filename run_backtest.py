#!/usr/bin/env python3
"""Run signal backtests against processed signals panel."""

from __future__ import annotations

import argparse
from pathlib import Path

from backtest.engine import run_backtest, save_backtest
from paths import DATA_PROCESSED, SIGNALS_PARQUET


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest options-implied signals")
    parser.add_argument(
        "--signals",
        default=str(SIGNALS_PARQUET),
        help="Input signals parquet",
    )
    parser.add_argument(
        "--horizon",
        type=int,
        default=21,
        help="Primary forward-return horizon in trading days",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DATA_PROCESSED),
        help="Directory for backtest outputs",
    )
    args = parser.parse_args()

    results = run_backtest(signals_path=Path(args.signals), forward_horizon=args.horizon)
    out = save_backtest(results, Path(args.output_dir))

    summary = results["summary"]
    print(f"\nBacktest summary ({args.horizon}d forward returns)")
    print(summary.to_string(index=False, float_format=lambda x: f"{x: .4f}"))
    print(f"\nWrote outputs to {out}")


if __name__ == "__main__":
    main()
