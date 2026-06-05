#!/usr/bin/env python3
"""Compute options-implied signals for configured symbols."""

from __future__ import annotations

import argparse
from pathlib import Path

from signals.config import load_config
from signals.pipeline import compute_signals

ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "signals.parquet"


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
        default=str(DEFAULT_OUTPUT),
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

    signal_cols = [
        "smirk", "risk_reversal", "risk_reversal_norm", "put_call_spread",
        "term_slope", "vrp", "implied_skew",
    ]
    signal_cols = [c for c in signal_cols if c in panel.columns]
    coverage = panel[signal_cols].notna().mean().mul(100).round(1)
    print(f"\nWrote {len(panel)} rows to {output}")
    print("Coverage (% non-NaN):")
    for name, pct in coverage.items():
        print(f"  {name}: {pct}%")


if __name__ == "__main__":
    main()
