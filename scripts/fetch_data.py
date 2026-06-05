#!/usr/bin/env python3
"""Fetch options/underlying parquet for configured symbols."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from signals.config import load_config
from signals.data_sources import ensure_options_file, ensure_underlying_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Download options data for symbols")
    parser.add_argument("--symbols", nargs="+", default=None)
    args = parser.parse_args()

    cfg = load_config()
    symbols = args.symbols or list(cfg.starter_symbols)

    for sym in symbols:
        print(f"Fetching {sym}...")
        opt = ensure_options_file(sym, cfg)
        und = ensure_underlying_file(sym, cfg)
        print(f"  options: {opt or 'FAILED'}")
        print(f"  underlying: {und or 'FAILED'}")


if __name__ == "__main__":
    main()
