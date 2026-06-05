from __future__ import annotations

import numpy as np
import pandas as pd


def compute_put_call_spread(filtered: pd.DataFrame) -> pd.DataFrame:
    """
    OI-weighted average of (IV_call - IV_put) over matched (K, T) pairs.
    Uses raw filtered quotes, not interpolated grid IVs.
    """
    calls = filtered[filtered["type"] == "call"][
        ["date", "underlying", "expiration", "strike", "implied_volatility", "open_interest"]
    ].rename(
        columns={
            "implied_volatility": "iv_call",
            "open_interest": "oi_call",
        }
    )
    puts = filtered[filtered["type"] == "put"][
        ["date", "underlying", "expiration", "strike", "implied_volatility", "open_interest"]
    ].rename(
        columns={
            "implied_volatility": "iv_put",
            "open_interest": "oi_put",
        }
    )

    pairs = calls.merge(puts, on=["date", "underlying", "expiration", "strike"], how="inner")
    if pairs.empty:
        return pd.DataFrame(columns=["date", "underlying", "put_call_spread"])

    pairs["pair_oi"] = pairs["oi_call"] + pairs["oi_put"]
    pairs["spread"] = pairs["iv_call"] - pairs["iv_put"]
    pairs["weighted_spread"] = pairs["spread"] * pairs["pair_oi"]

    out = pairs.groupby(["date", "underlying"], as_index=False).agg(
        weighted_sum=("weighted_spread", "sum"),
        weight_sum=("pair_oi", "sum"),
    )
    out["put_call_spread"] = out["weighted_sum"] / out["weight_sum"]
    out.loc[out["weight_sum"] <= 0, "put_call_spread"] = np.nan
    return out[["date", "underlying", "put_call_spread"]]
