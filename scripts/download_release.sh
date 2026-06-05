#!/usr/bin/env bash
# Download the working SPY/QQQ/IWM mirror (~1.3 GB).
# Use this while the Dubach CDN is offline.

set -euo pipefail

BASE="https://github.com/lambdaclass/options_portfolio_backtester/releases/download/data-v1"
OUT_DIR="${OUT_DIR:-$(cd "$(dirname "$0")/.." && pwd)/data/raw/release}"

mkdir -p "$OUT_DIR"
cd "$OUT_DIR"

for f in SPY_options.parquet SPY_underlying.parquet \
         QQQ_options.parquet QQQ_underlying.parquet \
         IWM_options.parquet IWM_underlying.parquet; do
  if [[ -f "$f" && -s "$f" ]]; then
    echo "[skip] $f"
    continue
  fi
  echo "[get]  $f"
  curl -fL --retry 3 --retry-delay 5 -o "$f" "$BASE/$f"
done

echo ""
echo "Done. Files in: $OUT_DIR"
ls -lh "$OUT_DIR"
