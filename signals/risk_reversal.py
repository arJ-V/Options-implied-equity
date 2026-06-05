from __future__ import annotations

import pandas as pd


def compute_risk_reversal(surface: pd.DataFrame, maturity_days: int = 30) -> pd.DataFrame:
    """RR = iv_c25 - iv_p25; normalized by iv_atm."""
    c = f"iv_c25_{maturity_days}"
    p = f"iv_p25_{maturity_days}"
    a = f"iv_atm_{maturity_days}"

    rr = surface[c] - surface[p]
    rr = rr.where(surface[c].notna() & surface[p].notna())

    rr_norm = rr / surface[a]
    rr_norm = rr_norm.where(surface[a].notna() & (surface[a] != 0))

    return pd.DataFrame({"risk_reversal": rr, "risk_reversal_norm": rr_norm})
