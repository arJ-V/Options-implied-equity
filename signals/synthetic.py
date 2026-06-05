from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm


def _bs_price(spot: float, strike: float, tau: float, sigma: float, r: float, is_call: bool) -> float:
    if tau <= 0 or sigma <= 0:
        return max(0.0, spot - strike) if is_call else max(0.0, strike - spot)
    d1 = (np.log(spot / strike) + (r + 0.5 * sigma**2) * tau) / (sigma * np.sqrt(tau))
    d2 = d1 - sigma * np.sqrt(tau)
    if is_call:
        return spot * norm.cdf(d1) - strike * np.exp(-r * tau) * norm.cdf(d2)
    return strike * np.exp(-r * tau) * norm.cdf(-d2) - spot * norm.cdf(-d1)


def synthetic_flat_smile_chain(
    spot: float = 100.0,
    sigma: float = 0.20,
    tau_days: int = 30,
    risk_free_rate: float = 0.05,
    moneyness_grid: tuple[float, ...] | None = None,
) -> pd.DataFrame:
    """Flat-vol Black-Scholes chain for BKM skew ≈ 0 validation."""
    date = pd.Timestamp("2024-06-03")
    expiry = date + pd.Timedelta(days=tau_days)
    tau = tau_days / 365.0
    rows = []

    grid = moneyness_grid if moneyness_grid is not None else tuple(np.arange(0.70, 1.305, 0.01))
    for m in grid:
        strike = spot * m
        for opt_type, is_call in [("call", True), ("put", False)]:
            if is_call and strike <= spot:
                continue
            if not is_call and strike >= spot:
                continue
            mid = _bs_price(spot, strike, tau, sigma, risk_free_rate, is_call)
            rows.append(
                {
                    "date": date,
                    "underlying": "TEST",
                    "expiration": expiry,
                    "strike": strike,
                    "type": opt_type,
                    "bid": mid * 0.99,
                    "ask": mid * 1.01,
                    "open_interest": 1000,
                    "implied_volatility": sigma,
                    "delta": np.nan,
                    "spot": spot,
                    "moneyness": m,
                    "dte": tau_days,
                }
            )

    return pd.DataFrame(rows)
