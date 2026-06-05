from __future__ import annotations

import numpy as np
import pandas as pd


def compute_realized_vol(
    underlying: pd.DataFrame,
    window: int = 21,
    annualization: int = 252,
) -> pd.DataFrame:
    """
    Trailing realized vol ending T-1 (strictly before signal date T).

    RV = sqrt(annualization) * stdev(daily log returns over prior `window` days).
    """
    prices = underlying.sort_values("date").copy()
    prices["log_return"] = np.log(prices["close"] / prices["close"].shift(1))
    prices["rv"] = (
        prices["log_return"]
        .rolling(window=window, min_periods=window)
        .std()
        * np.sqrt(annualization)
    )
    # Signal on date T uses returns strictly before T (through prior close).
    prices["rv"] = prices["rv"].shift(1)

    symbol_col = "underlying" if "underlying" in prices.columns else "symbol"
    out = prices[["date", symbol_col, "rv"]].copy()
    if symbol_col == "symbol":
        out = out.rename(columns={"symbol": "underlying"})
    return out


def compute_vrp(surface: pd.DataFrame, rv: pd.DataFrame, maturity_days: int = 30) -> pd.Series:
    """VRP = iv_atm - RV_21."""
    iv_col = f"iv_atm_{maturity_days}"
    if iv_col not in surface.columns:
        return pd.Series(float("nan"), index=surface.index)

    merged = surface[["date", "underlying", iv_col]].merge(
        rv[["date", "underlying", "rv"]],
        on=["date", "underlying"],
        how="left",
    )
    vrp = merged[iv_col] - merged["rv"]
    return vrp.where(merged[iv_col].notna() & merged["rv"].notna())
