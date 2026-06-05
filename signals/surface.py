from __future__ import annotations

import numpy as np
import pandas as pd

from signals.config import SurfaceConfig


def _interp_delta(deltas: np.ndarray, ivs: np.ndarray, target: float) -> float:
    if len(deltas) < 2:
        return np.nan
    order = np.argsort(deltas)
    x = deltas[order]
    y = ivs[order]
    if target < x.min() or target > x.max():
        return np.nan
    return float(np.interp(target, x, y))


def _interp_total_variance(dtes: np.ndarray, ivs: np.ndarray, target_dte: float) -> float:
    if len(dtes) < 2:
        return np.nan
    if target_dte < dtes.min() or target_dte > dtes.max():
        return np.nan

    t_years = dtes.astype(float) / 365.0
    target_t = target_dte / 365.0
    total_var = (ivs.astype(float) ** 2) * t_years

    order = np.argsort(t_years)
    x = t_years[order]
    y = total_var[order]
    w = float(np.interp(target_t, x, y))
    if w <= 0 or target_t <= 0:
        return np.nan
    return float(np.sqrt(w / target_t))


def _delta_label(side: str, target: float) -> str:
    pct = int(round(abs(target) * 100))
    prefix = "p" if side == "put" else "c"
    return f"iv_{prefix}{pct}"


def build_surface_grid(filtered: pd.DataFrame, cfg: SurfaceConfig) -> pd.DataFrame:
    """
    Standardized IV surface per (date, underlying).

    Interpolate within each expiry on delta, then across maturity in total variance.
    """
    if filtered.empty:
        return pd.DataFrame(columns=["date", "underlying"])

    per_expiry_rows: list[dict] = []

    grouped = filtered.groupby(["date", "underlying", "expiration", "type"], sort=False)
    for (date, underlying, _expiration, opt_type), grp in grouped:
        deltas = grp["delta"].to_numpy(dtype=float)
        ivs = grp["implied_volatility"].to_numpy(dtype=float)
        dte = int(grp["dte"].iloc[0])

        if opt_type == "put":
            targets = cfg.put_deltas
        else:
            targets = cfg.call_deltas

        for target in targets:
            iv = _interp_delta(deltas, ivs, target)
            if np.isnan(iv):
                continue
            per_expiry_rows.append(
                {
                    "date": date,
                    "underlying": underlying,
                    "dte": dte,
                    "type": opt_type,
                    "target_delta": target,
                    "iv": iv,
                }
            )

    if not per_expiry_rows:
        return pd.DataFrame(columns=["date", "underlying"])

    per_expiry = pd.DataFrame(per_expiry_rows)

    surface_rows: list[dict] = []
    maturity_groups = per_expiry.groupby(["date", "underlying", "type", "target_delta"], sort=False)
    for (date, underlying, opt_type, target_delta), grp in maturity_groups:
        dtes = grp["dte"].to_numpy(dtype=float)
        ivs = grp["iv"].to_numpy(dtype=float)
        label = _delta_label(opt_type, target_delta)

        row = {"date": date, "underlying": underlying}
        complete = True
        for maturity in cfg.maturities_days:
            iv_mat = _interp_total_variance(dtes, ivs, float(maturity))
            row[f"{label}_{maturity}"] = iv_mat
            if np.isnan(iv_mat):
                complete = False
        row["_complete"] = complete
        surface_rows.append(row)

    if not surface_rows:
        return pd.DataFrame(columns=["date", "underlying"])

    wide = pd.DataFrame(surface_rows)
    index_cols = ["date", "underlying"]
    value_cols = [c for c in wide.columns if c.startswith("iv_")]

    merged: list[dict] = []
    for (date, underlying), grp in wide.groupby(index_cols, sort=False):
        row: dict = {"date": date, "underlying": underlying}
        for col in value_cols:
            vals = grp[col].dropna()
            row[col] = float(vals.iloc[0]) if len(vals) else np.nan
        merged.append(row)
    wide = pd.DataFrame(merged)

    for maturity in cfg.maturities_days:
        c50 = f"iv_c50_{maturity}"
        p50 = f"iv_p50_{maturity}"
        if c50 in wide.columns and p50 in wide.columns:
            wide[f"iv_atm_{maturity}"] = wide[[c50, p50]].mean(axis=1, skipna=True)
            missing_leg = wide[c50].isna() | wide[p50].isna()
            wide.loc[missing_leg, f"iv_atm_{maturity}"] = np.nan

    return wide.sort_values(["date", "underlying"]).reset_index(drop=True)
