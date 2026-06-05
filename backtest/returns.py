from __future__ import annotations

import numpy as np
import pandas as pd

from signals.config import AppConfig, load_config
from signals.data import load_underlying


def load_underlying_panel(
    symbols: list[str],
    cfg: AppConfig | None = None,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    cfg = cfg or load_config()
    start_ts = pd.Timestamp(start) if start else None
    end_ts = pd.Timestamp(end) if end else None

    frames = []
    for symbol in symbols:
        df = load_underlying(symbol, cfg, start_ts, end_ts)
        df["underlying"] = symbol.upper()
        frames.append(df)

    return pd.concat(frames, ignore_index=True).sort_values(["underlying", "date"])


def compute_forward_log_returns(
    prices: pd.DataFrame,
    horizons: tuple[int, ...] = (5, 21, 63),
) -> pd.DataFrame:
    """
    Forward log returns from T+1 close to T+h close (signal known at T close).
    """
    out = prices[["date", "underlying", "close"]].copy()
    grouped = out.groupby("underlying", sort=False)["close"]

    for h in horizons:
        entry = grouped.shift(-1)
        exit_ = grouped.shift(-h)
        out[f"fwd_ret_{h}d"] = np.log(exit_ / entry)

    return out
