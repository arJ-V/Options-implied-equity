import numpy as np
import pandas as pd

from signals.config import load_config
from signals.surface import _interp_delta, _interp_total_variance, build_surface_grid


def test_interp_delta_brackets_target():
    deltas = np.array([-0.5, -0.25, -0.1])
    ivs = np.array([0.30, 0.25, 0.22])
    assert np.isclose(_interp_delta(deltas, ivs, -0.25), 0.25)


def test_interp_delta_outside_range_is_nan():
    deltas = np.array([-0.5, -0.25])
    ivs = np.array([0.30, 0.25])
    assert np.isnan(_interp_delta(deltas, ivs, -0.1))


def test_interp_total_variance_uses_variance_not_raw_iv():
    dtes = np.array([20.0, 40.0])
    ivs = np.array([0.20, 0.22])
    iv_30 = _interp_total_variance(dtes, ivs, 30.0)
    assert not np.isnan(iv_30)
    assert 0.19 < iv_30 < 0.23


def test_build_surface_produces_atm_with_two_expiries():
    cfg = load_config().surface
    filtered = pd.DataFrame(
        {
            "date": [pd.Timestamp("2024-01-02")] * 8,
            "underlying": ["SPY"] * 8,
            "expiration": [pd.Timestamp("2024-02-02")] * 4 + [pd.Timestamp("2024-03-02")] * 4,
            "type": ["put", "put", "call", "call"] * 2,
            "dte": [28, 28, 28, 28, 45, 45, 45, 45],
            "delta": [-0.5, -0.25, 0.25, 0.5] * 2,
            "implied_volatility": [0.20, 0.22, 0.19, 0.18, 0.21, 0.23, 0.20, 0.19],
        }
    )
    surface = build_surface_grid(filtered, cfg)
    assert "iv_atm_30" in surface.columns
    assert not np.isnan(surface.loc[0, "iv_atm_30"])
