from __future__ import annotations

import numpy as np
import pandas as pd


def _trapz_integral(strikes: np.ndarray, values: np.ndarray) -> float:
    if len(strikes) < 2:
        return np.nan
    order = np.argsort(strikes)
    x = strikes[order].astype(float)
    y = values[order].astype(float)
    valid = np.isfinite(x) & np.isfinite(y)
    x, y = x[valid], y[valid]
    if len(x) < 2:
        return np.nan
    return float(np.trapezoid(y, x))


def bkm_moments(
    spot: float,
    call_strikes: np.ndarray,
    call_prices: np.ndarray,
    put_strikes: np.ndarray,
    put_prices: np.ndarray,
    tau_years: float,
    risk_free_rate: float = 0.05,
) -> tuple[float, float, float, float]:
    """Return (V, W, X, implied_skew) from BKM strike-strip integrals."""
    if spot <= 0 or tau_years <= 0:
        return (np.nan, np.nan, np.nan, np.nan)

    s = float(spot)
    er = np.exp(risk_free_rate * tau_years)

    # OTM relative to spot; need dense wings for stable BKM integrals.
    call_mask = call_strikes >= s
    put_mask = put_strikes <= s
    kc = call_strikes[call_mask]
    cc = call_prices[call_mask]
    kp = put_strikes[put_mask]
    pc = put_prices[put_mask]

    if len(kc) < 2 or len(kp) < 2:
        return (np.nan, np.nan, np.nan, np.nan)

    ln_k_s = np.log(kc / s)
    v_call = 2.0 * (1.0 - ln_k_s) / (kc**2) * cc
    w_call = (6.0 * ln_k_s - 3.0 * ln_k_s**2) / (kc**2) * cc
    x_call = (12.0 * ln_k_s**2 - 4.0 * ln_k_s**3) / (kc**2) * cc

    ln_s_k = np.log(s / kp)
    v_put = 2.0 * (1.0 + ln_s_k) / (kp**2) * pc
    w_put = -(6.0 * ln_s_k + 3.0 * ln_s_k**2) / (kp**2) * pc
    x_put = (12.0 * ln_s_k**2 + 4.0 * ln_s_k**3) / (kp**2) * pc

    v = _trapz_integral(kc, v_call) + _trapz_integral(kp, v_put)
    w = _trapz_integral(kc, w_call) + _trapz_integral(kp, w_put)
    x = _trapz_integral(kc, x_call) + _trapz_integral(kp, x_put)

    mu = er - 1.0 - (er / 2.0) * v - (er / 6.0) * w - (er / 24.0) * x
    denom = (er * v - mu**2) ** 1.5
    if not np.isfinite(denom) or abs(denom) < 1e-12:
        return (v, w, x, np.nan)

    skew = (er * w - 3.0 * mu * er * v + 2.0 * mu**3) / denom
    return (v, w, x, float(skew))


def compute_implied_skew_day(
    day_chain: pd.DataFrame,
    spot: float,
    target_dte: int = 30,
    risk_free_rate: float = 0.05,
) -> float:
    """Pick expiry nearest target_dte and compute BKM skew for one (date, underlying)."""
    if day_chain.empty or not np.isfinite(spot) or spot <= 0:
        return np.nan

    expiries = day_chain.groupby("expiration")["dte"].first().reset_index()
    expiries["dte_gap"] = (expiries["dte"] - target_dte).abs()
    expiry = expiries.nsmallest(1, "dte_gap")["expiration"].iloc[0]

    slice_ = day_chain[day_chain["expiration"] == expiry].copy()
    slice_["mid"] = (slice_["bid"] + slice_["ask"]) / 2.0

    calls = slice_[slice_["type"] == "call"]
    puts = slice_[slice_["type"] == "put"]

    tau = float(slice_["dte"].iloc[0]) / 365.0
    _, _, _, skew = bkm_moments(
        spot=spot,
        call_strikes=calls["strike"].to_numpy(),
        call_prices=calls["mid"].to_numpy(),
        put_strikes=puts["strike"].to_numpy(),
        put_prices=puts["mid"].to_numpy(),
        tau_years=tau,
        risk_free_rate=risk_free_rate,
    )
    return skew


def compute_implied_skew_panel(
    filtered: pd.DataFrame,
    target_dte: int = 30,
    risk_free_rate: float = 0.05,
) -> pd.DataFrame:
    rows = []
    grouped = filtered.groupby(["date", "underlying"], sort=False)
    for (date, underlying), grp in grouped:
        spot = grp["spot"].iloc[0]
        skew = compute_implied_skew_day(grp, spot, target_dte, risk_free_rate)
        rows.append({"date": date, "underlying": underlying, "implied_skew": skew})

    return pd.DataFrame(rows)
