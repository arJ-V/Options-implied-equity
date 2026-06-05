from __future__ import annotations

from pathlib import Path

import pandas as pd

EARNINGS_CACHE = Path(__file__).resolve().parent.parent / "data" / "processed" / "earnings_dates.parquet"


def fetch_earnings_dates(symbols: list[str], cache_path: Path | None = None) -> pd.DataFrame:
    """
    Load earnings announcement dates via yfinance.
    ETFs typically return empty — flag stays False for them.
    """
    cache_path = cache_path or EARNINGS_CACHE
    if cache_path.exists():
        cached = pd.read_parquet(cache_path)
        cached["earnings_date"] = pd.to_datetime(cached["earnings_date"]).dt.normalize()
        missing = [s for s in symbols if s.upper() not in set(cached["underlying"])]
        if not missing:
            return cached[cached["underlying"].isin([s.upper() for s in symbols])]

    try:
        import yfinance as yf
    except ImportError:
        return pd.DataFrame(columns=["underlying", "earnings_date"])

    rows: list[dict] = []
    for symbol in symbols:
        sym = symbol.upper()
        ticker = yf.Ticker(sym.replace(".", "-"))
        try:
            dates = ticker.get_earnings_dates(limit=80)
        except Exception:
            dates = None
        if dates is None or dates.empty:
            continue
        idx = pd.to_datetime(dates.index)
        if hasattr(idx, "tz") and idx.tz is not None:
            idx = idx.tz_localize(None)
        for d in idx.normalize().unique():
            rows.append({"underlying": sym, "earnings_date": d})

    out = pd.DataFrame(rows)
    if not out.empty:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        if cache_path.exists():
            old = pd.read_parquet(cache_path)
            old["earnings_date"] = pd.to_datetime(old["earnings_date"]).dt.normalize()
            out = pd.concat([old, out], ignore_index=True).drop_duplicates()
        out.to_parquet(cache_path, index=False)
    return out


def earnings_within_window(
    panel_dates: pd.Series,
    underlying: str,
    earnings: pd.DataFrame,
    lookahead_days: int,
) -> pd.Series:
    """True when an earnings date falls in (date, date + lookahead_days]."""
    if earnings.empty or "underlying" not in earnings.columns:
        return pd.Series(False, index=panel_dates.index)

    sym_dates = earnings.loc[earnings["underlying"] == underlying.upper(), "earnings_date"]
    if sym_dates.empty:
        return pd.Series(False, index=panel_dates.index)

    earn = pd.to_datetime(sym_dates).dt.normalize()
    flags = []
    for d in pd.to_datetime(panel_dates).dt.normalize():
        end = d + pd.Timedelta(days=lookahead_days)
        hit = ((earn > d) & (earn <= end)).any()
        flags.append(bool(hit))
    return pd.Series(flags, index=panel_dates.index)


def apply_earnings_mask(
    panel: pd.DataFrame,
    earnings: pd.DataFrame,
    signal_col: str = "term_slope",
    lookahead_days: int = 30,
) -> pd.DataFrame:
    out = panel.copy()
    out["earnings_window"] = False
    for sym in out["underlying"].unique():
        mask = out["underlying"] == sym
        flags = earnings_within_window(out.loc[mask, "date"], sym, earnings, lookahead_days)
        out.loc[mask, "earnings_window"] = flags.values

    out.loc[out["earnings_window"], signal_col] = float("nan")
    return out
