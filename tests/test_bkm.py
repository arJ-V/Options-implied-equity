import numpy as np

from signals.config import load_config
from signals.implied_skew import compute_implied_skew_day
from signals.synthetic import synthetic_flat_smile_chain


def test_bkm_skew_near_zero_on_flat_smile():
    cfg = load_config()
    chain = synthetic_flat_smile_chain()
    skew = compute_implied_skew_day(chain, spot=100.0, target_dte=30, risk_free_rate=0.05)
    assert np.isfinite(skew)
    assert abs(skew) < cfg.bkm.synthetic_skew_tolerance
