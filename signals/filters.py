from __future__ import annotations

import pandas as pd

from signals.config import SurfaceConfig


def apply_quote_filters(chain: pd.DataFrame, cfg: SurfaceConfig) -> pd.DataFrame:
    """Apply §0 quote filters before surface or pair-matched signals."""
    df = chain.copy()
    valid_spot = df["spot"].notna() & (df["spot"] > 0)
    df = df[valid_spot]

    mid = (df["bid"] + df["ask"]) / 2.0
    spread = df["ask"] - df["bid"]

    keep = df["bid"] >= cfg.min_bid
    keep &= df["implied_volatility"].notna() & (df["implied_volatility"] > 0)
    keep &= df["delta"].notna()

    if cfg.drop_crossed_markets:
        keep &= spread >= 0

    keep &= (mid > 0) & (spread / mid <= cfg.max_spread_pct_of_mid)
    keep &= df["open_interest"] >= cfg.min_open_interest
    keep &= df["moneyness"].between(cfg.moneyness_min, cfg.moneyness_max)
    keep &= df["dte"].between(cfg.dte_min, cfg.dte_max)

    return df.loc[keep].reset_index(drop=True)
