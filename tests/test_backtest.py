import numpy as np
import pandas as pd

from backtest.metrics import long_short_returns, orient_signal
from backtest.returns import compute_forward_log_returns


def test_forward_returns_start_after_signal_date():
    prices = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-02", periods=5, freq="B"),
            "underlying": ["SPY"] * 5,
            "close": [100, 101, 102, 103, 104],
        }
    )
    fwd = compute_forward_log_returns(prices, horizons=(2,))
    row0 = fwd.iloc[0]
    expected = np.log(102 / 101)
    assert np.isclose(row0["fwd_ret_2d"], expected)


def test_orient_signal_inverts_smirk():
    s = pd.Series([1.0, 2.0])
    out = orient_signal(s, "smirk")
    assert out.iloc[0] == -1.0


def test_long_short_spread_direction():
    panel = pd.DataFrame(
        {
            "date": [pd.Timestamp("2024-01-02")] * 3,
            "underlying": ["A", "B", "C"],
            "risk_reversal": [-0.10, -0.05, 0.02],
            "fwd_ret_21d": [0.01, 0.02, 0.05],
        }
    )
    ls = long_short_returns(panel, "risk_reversal", "fwd_ret_21d", min_names=3)
    assert len(ls) == 1
    assert ls.iloc[0]["ls_return"] > 0
