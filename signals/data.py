from __future__ import annotations

from pathlib import Path

import pandas as pd

from signals.config import AppConfig
from signals.data_sources import ensure_options_file, ensure_underlying_file


def _read_options(path: Path, start: pd.Timestamp | None, end: pd.Timestamp | None) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["expiration"] = pd.to_datetime(df["expiration"]).dt.normalize()
    df["type"] = df["type"].astype(str).str.lower()
    if start is not None:
        df = df[df["date"] >= pd.Timestamp(start).normalize()]
    if end is not None:
        df = df[df["date"] <= pd.Timestamp(end).normalize()]
    return df.reset_index(drop=True)


def _read_underlying(path: Path, start: pd.Timestamp | None, end: pd.Timestamp | None) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    if start is not None:
        df = df[df["date"] >= pd.Timestamp(start).normalize()]
    if end is not None:
        df = df[df["date"] <= pd.Timestamp(end).normalize()]
    return df.sort_values("date").reset_index(drop=True)


def load_options(
    symbol: str,
    cfg: AppConfig,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
    auto_fetch: bool = True,
) -> pd.DataFrame:
    path = ensure_options_file(symbol, cfg) if auto_fetch else cfg.raw_data_dir / f"{symbol.upper()}_options.parquet"
    if path is None or not Path(path).exists():
        raise FileNotFoundError(f"Missing options data for {symbol}")
    return _read_options(Path(path), start, end)


def load_underlying(
    symbol: str,
    cfg: AppConfig,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
    auto_fetch: bool = True,
) -> pd.DataFrame:
    path = ensure_underlying_file(symbol, cfg) if auto_fetch else cfg.raw_data_dir / f"{symbol.upper()}_underlying.parquet"
    if path is None or not Path(path).exists():
        raise FileNotFoundError(f"Missing underlying data for {symbol}")
    return _read_underlying(Path(path), start, end)


def attach_spot(chain: pd.DataFrame, underlying: pd.DataFrame) -> pd.DataFrame:
    spot = underlying[["date", "close"]].rename(columns={"close": "spot"})
    out = chain.merge(spot, on="date", how="left")
    out["moneyness"] = out["strike"] / out["spot"]
    out["dte"] = (out["expiration"] - out["date"]).dt.days
    return out
