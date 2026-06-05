from __future__ import annotations

import shutil
from pathlib import Path
from urllib.request import Request, urlopen

from signals.config import AppConfig, ROOT

RELEASE_URL = "https://github.com/lambdaclass/options_portfolio_backtester/releases/download/data-v1"


def _download(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return True
    try:
        req = Request(url, headers={"User-Agent": "options-implied-equity/1.0"})
        with urlopen(req, timeout=120) as resp, open(dest, "wb") as f:
            shutil.copyfileobj(resp, f)
        return dest.stat().st_size > 0
    except Exception:
        if dest.exists():
            dest.unlink(missing_ok=True)
        return False


def ensure_options_file(symbol: str, cfg: AppConfig) -> Path | None:
    sym = symbol.upper()
    release_path = cfg.raw_data_dir / f"{sym}_options.parquet"
    if release_path.exists() and release_path.stat().st_size > 0:
        return release_path

    dubach_path = ROOT / "data" / "raw" / "dubach" / sym.lower() / "options.parquet"
    if dubach_path.exists() and dubach_path.stat().st_size > 0:
        return dubach_path

    if _download(f"{RELEASE_URL}/{sym}_options.parquet", release_path):
        return release_path

    if _download(f"{cfg.dubach_base_url}/{sym.lower()}/options.parquet", dubach_path):
        return dubach_path

    return None


def ensure_underlying_file(symbol: str, cfg: AppConfig) -> Path | None:
    sym = symbol.upper()
    release_path = cfg.raw_data_dir / f"{sym}_underlying.parquet"
    if release_path.exists() and release_path.stat().st_size > 0:
        return release_path

    dubach_path = ROOT / "data" / "raw" / "dubach" / sym.lower() / "underlying.parquet"
    if dubach_path.exists() and dubach_path.stat().st_size > 0:
        df_ok = dubach_path.stat().st_size > 10_000
        if df_ok:
            return dubach_path

    if _download(f"{RELEASE_URL}/{sym}_underlying.parquet", release_path):
        return release_path

    if _download(f"{cfg.dubach_base_url}/{sym.lower()}/underlying.parquet", dubach_path):
        if dubach_path.stat().st_size > 10_000:
            return dubach_path

    return _backfill_underlying_yfinance(sym, release_path)


def _backfill_underlying_yfinance(symbol: str, dest: Path) -> Path | None:
    try:
        import yfinance as yf
    except ImportError:
        return None

    yf_symbol = symbol.replace(".", "-")
    hist = yf.download(yf_symbol, start="2008-01-01", auto_adjust=False, progress=False)
    if hist is None or hist.empty:
        return None

    hist = hist.reset_index()
    if hasattr(hist["Date"].dt, "tz") and hist["Date"].dt.tz is not None:
        hist["Date"] = hist["Date"].dt.tz_localize(None)

    import pandas as pd

    out = pd.DataFrame(
        {
            "symbol": symbol,
            "date": hist["Date"],
            "open": hist["Open"],
            "high": hist["High"],
            "low": hist["Low"],
            "close": hist["Close"],
            "adjusted_close": hist["Adj Close"],
            "volume": hist["Volume"],
            "dividend_amount": 0.0,
            "split_coefficient": 1.0,
        }
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(dest, index=False)
    return dest
