# Options-Implied Equity Signals

Research pipeline for options-implied equity return signals: surface standardization, signal computation, backtesting, and an interactive dashboard.

See [`instructions.md`](instructions.md) for formula definitions and [`config.yaml`](config.yaml) for pinned parameters.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 1. Download data (~1.3 GB)
./scripts/download_release.sh

# 2. Compute signals
python run_signals.py --start 2020-01-01 --end 2024-12-31

# 3. Backtest
python run_backtest.py --horizon 21

# 4. Dashboard
streamlit run app/dashboard.py
```

Open http://localhost:8501

## Project layout

```
signals/          # Surface builder + Phase 1 signals
backtest/         # Forward returns, IC, long-short
app/dashboard.py  # Streamlit + Plotly visualizer
run_signals.py    # Signal pipeline CLI
run_backtest.py   # Backtest CLI
data/
  raw/release/    # Input parquet (SPY, QQQ, IWM)
  processed/      # signals.parquet, backtest outputs
```

## Signals (Phase 1)

| Signal | Formula | Expected direction |
|--------|---------|-------------------|
| Smirk | `iv_p25_30 - iv_atm_30` | high → short |
| Risk reversal | `iv_c25 - iv_p25` | high → long |
| Put-call spread | OI-wtd `IV_call - IV_put` | high → long |
| Term slope | `iv_atm_90 - iv_atm_30` | inversion → bearish |
| VRP | `iv_atm_30 - RV_21` | empirical |
| Implied skew (BKM) | strike-strip integrals | more neg → long |

## Backtest

```bash
python run_backtest.py --horizon 21
```

Outputs: `backtest_summary.parquet`, `backtest_ic.parquet`, `backtest_ls.parquet`

## Data fetching

```bash
python scripts/fetch_data.py --symbols SPY QQQ IWM   # release → Dubach CDN → yfinance fallback
./scripts/download_release.sh                       # direct GitHub release download
```

## Deployment

### Docker

```bash
docker compose up --build
```

Mount `data/processed` and `data/raw/release` (configured in `docker-compose.yml`).

### Streamlit Community Cloud

1. Push repo to GitHub
2. Include precomputed `data/processed/signals.parquet` (or run pipeline in CI)
3. Deploy with main file: `app/dashboard.py`
4. Python 3.11+, deps: `requirements.txt` (auto-detected)

## Data sources

- **Current:** [Lambda Class release](https://github.com/lambdaclass/options_portfolio_backtester/releases/tag/data-v1) — SPY, QQQ, IWM (2008–2025)
- **Full panel:** Dubach CDN (currently offline) or ThetaData free EOD

## Tests

```bash
pytest -q
```

## Streamlit Cloud

1. Push repo to GitHub (includes `data/sample/signals.parquet` — 2024 demo data for SPY/QQQ/IWM)
2. Go to [share.streamlit.io](https://share.streamlit.io) → **Create app**
3. Set:
   - **Repository:** `arJ-V/Options-implied-equity`
   - **Branch:** `main`
   - **Main file path:** `app/dashboard.py`
4. **Advanced settings → Python version:** 3.11 (or 3.12)
5. Dependencies: Streamlit reads `requirements.txt` from the repo root automatically — no extra config needed
6. Optional **Secrets** (Settings → Secrets) to override data path:

```toml
[data]
signals_path = "data/sample/signals.parquet"
```

The dashboard auto-uses `data/processed/signals.parquet` if you've run the full pipeline locally; otherwise it falls back to the bundled sample.

## Roadmap

- [x] Phase 1 signals + pipeline
- [x] Backtest engine + dashboard + Docker
- [x] BKM implied skew (Phase 2)
- [x] Earnings mask for term slope (yfinance calendar)
- [x] Multi-source data loader
- [ ] Order flow (Phase 3, needs signed volume)
- [ ] 104-ticker panel when Dubach CDN returns
