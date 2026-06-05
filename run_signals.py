#!/usr/bin/env python3
"""Compute options-implied signals for configured symbols."""

from __future__ import annotations

import argparse
from pathlib import Path

from paths import SIGNALS_PARQUET
from signals.config import load_config
from signals.constants import SIGNAL_COLS
from signals.pipeline import compute_signals


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute options-implied equity signals")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=None,
        help="Tickers to process (default: config starter_symbols)",
    )
    parser.add_argument("--start", default=None, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="End date YYYY-MM-DD")
    parser.add_argument(
        "--output",
        default=str(SIGNALS_PARQUET),
        help="Output parquet path",
    )
    args = parser.parse_args()

    cfg = load_config()
    symbols = args.symbols or list(cfg.starter_symbols)

    panel = compute_signals(symbols, cfg=cfg, start=args.start, end=args.end)
    if panel.empty:
        raise SystemExit("No signals produced.")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(output, index=False)

    signal_cols = [c for c in SIGNAL_COLS if c in panel.columns]
    if "risk_reversal_norm" in panel.columns:
        signal_cols.append("risk_reversal_norm")
    coverage = panel[signal_cols].notna().mean().mul(100).round(1)
    print(f"\nWrote {len(panel)} rows to {output}")
    print("Coverage (% non-NaN):")
    for name, pct in coverage.items():
        print(f"  {name}: {pct}%")


if __name__ == "__main__":
    main()
