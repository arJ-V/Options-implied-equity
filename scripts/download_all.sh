#!/usr/bin/env bash
# Download full 104-ticker Dubach options panel (options + underlying parquet).
# Expect ~15–25 GB on disk depending on ticker liquidity.
#
# Usage:
#   ./scripts/download_all.sh              # all 104 tickers
#   ./scripts/download_all.sh aapl msft    # subset only
#   ./scripts/download_all.sh --retry-failed

set -euo pipefail

BASE_URL="${DUBACH_BASE_URL:-https://static.philippdubach.com/data/options}"
OUT_DIR="${OUT_DIR:-$(cd "$(dirname "$0")/.." && pwd)/data/raw}"
PARALLEL="${PARALLEL:-4}"

ALL_TICKERS=(aapl abbv abt acn adbe aig amd amgn amt amzn
  avgo axp ba bac bk bkng blk bmy brk.b c
  cat cl cmcsa cof cop cost crm csco cvs cvx
  de dhr dis duk emr fdx gd ge gild gm
  goog googl gs hd hon ibm intu isrg iwm jnj
  jpm ko lin lly lmt low ma mcd mdlz mdt
  met meta mmm mo mrk ms msft nee nflx nke
  now nvda orcl pep pfe pg pltr pm pypl qcom
  qqq rtx sbux schw so spg spy t tgt tmo
  tmus tsla txn uber unh unp ups usb v vix
  vz wfc wmt xom)

RETRY_FAILED=false
TICKERS=()

for arg in "$@"; do
  case "$arg" in
    --retry-failed) RETRY_FAILED=true ;;
    *) TICKERS+=("${arg,,}") ;;
  esac
done

if [[ ${#TICKERS[@]} -eq 0 ]]; then
  TICKERS=("${ALL_TICKERS[@]}")
fi

mkdir -p "$OUT_DIR"
FAILED_LOG="$OUT_DIR/.failed_downloads"

# Fail fast if the CDN is offline (avoids 200+ useless 404s).
probe_code="$(curl -sI -o /dev/null -w "%{http_code}" "${BASE_URL}/aapl/options.parquet" || true)"
if [[ "$probe_code" != "200" ]]; then
  echo "ERROR: Dubach CDN unreachable (HTTP ${probe_code})."
  echo "The full 104-ticker panel is not available from this source right now."
  echo ""
  echo "Working fallback (~1.3 GB):"
  echo "  ./scripts/download_release.sh"
  echo ""
  echo "For a full historical panel, use ThetaData free EOD (see README) or retry later."
  exit 2
fi

download_one() {
  local ticker="$1"
  local sym_dir="$OUT_DIR/${ticker}"
  mkdir -p "$sym_dir"

  for kind in options underlying; do
    local dest="$sym_dir/${kind}.parquet"
    if [[ -f "$dest" && -s "$dest" ]]; then
      echo "[skip] $ticker $kind (exists)"
      continue
    fi

    local url="${BASE_URL}/${ticker}/${kind}.parquet"
    echo "[get]  $url"
    if ! curl -fL --retry 3 --retry-delay 5 -o "$dest" "$url"; then
      echo "[fail] $ticker $kind" | tee -a "$FAILED_LOG"
      rm -f "$dest"
    fi
  done
}

export -f download_one
export BASE_URL OUT_DIR FAILED_LOG

if [[ "$RETRY_FAILED" == true && -f "$FAILED_LOG" ]]; then
  mapfile -t TICKERS < <(awk '{print $1}' "$FAILED_LOG" | sort -u)
  : > "$FAILED_LOG"
fi

printf '%s\n' "${TICKERS[@]}" | xargs -P "$PARALLEL" -I {} bash -c 'download_one "$@"' _ {}

echo ""
echo "Done. Files in: $OUT_DIR"
if [[ -f "$FAILED_LOG" && -s "$FAILED_LOG" ]]; then
  echo "Some downloads failed. Retry with:"
  echo "  ./scripts/download_all.sh --retry-failed"
  exit 1
fi
