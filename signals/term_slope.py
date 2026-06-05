from __future__ import annotations

import pandas as pd


def compute_term_slope(surface: pd.DataFrame, short_days: int = 30, long_days: int = 90) -> pd.Series:
    """TS_SLOPE = iv_atm_long - iv_atm_short."""
    short_col = f"iv_atm_{short_days}"
    long_col = f"iv_atm_{long_days}"
    if short_col not in surface.columns or long_col not in surface.columns:
        return pd.Series(float("nan"), index=surface.index)

    out = surface[long_col] - surface[short_col]
    return out.where(surface[short_col].notna() & surface[long_col].notna())
