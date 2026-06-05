from __future__ import annotations

import numpy as np
import pandas as pd


def compute_smirk(surface: pd.DataFrame, maturity_days: int = 30) -> pd.Series:
    """SMIRK = iv_p25 - iv_atm at fixed maturity."""
    p = f"iv_p25_{maturity_days}"
    a = f"iv_atm_{maturity_days}"
    if p not in surface.columns or a not in surface.columns:
        return pd.Series(np.nan, index=surface.index)

    out = surface[p] - surface[a]
    out = out.where(surface[p].notna() & surface[a].notna())
    return out
