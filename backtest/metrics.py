from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from signals.constants import SIGNAL_COLS, SIGNAL_ORIENTATION


def orient_signal(series: pd.Series, signal: str) -> pd.Series:
    return series * SIGNAL_ORIENTATION.get(signal, 1.0)


def cross_sectional_ic(
    panel: pd.DataFrame,
    signal: str,
    forward_col: str,
    min_names: int = 3,
) -> pd.DataFrame:
    """Daily Spearman IC between oriented signal and forward return."""
    rows = []
    for date, grp in panel.groupby("date", sort=False):
        sub = grp[[signal, forward_col]].dropna()
        if len(sub) < min_names:
            continue
        oriented = orient_signal(sub[signal], signal)
        if oriented.nunique() < 2 or sub[forward_col].nunique() < 2:
            continue
        ic, _ = stats.spearmanr(oriented, sub[forward_col])
        rows.append({"date": date, "signal": signal, "ic": ic})

    return pd.DataFrame(rows)


def rolling_ic_mean(ic_series: pd.DataFrame, window: int = 252) -> pd.Series:
    if ic_series.empty:
        return pd.Series(dtype=float)
    s = ic_series.sort_values("date").set_index("date")["ic"]
    return s.rolling(window=window, min_periods=max(20, window // 4)).mean()


def long_short_returns(
    panel: pd.DataFrame,
    signal: str,
    forward_col: str,
    min_names: int = 3,
) -> pd.DataFrame:
    """
    Long top oriented-signal names, short bottom; equal-weight spread return.
    """
    rows = []
    for date, grp in panel.groupby("date", sort=False):
        sub = grp[["underlying", signal, forward_col]].dropna()
        if len(sub) < min_names:
            continue

        sub = sub.copy()
        sub["oriented"] = orient_signal(sub[signal], signal)
        if sub["oriented"].nunique() < 2:
            continue

        top = sub.nlargest(max(1, len(sub) // 3), "oriented")
        bottom = sub.nsmallest(max(1, len(sub) // 3), "oriented")
        ls_ret = top[forward_col].mean() - bottom[forward_col].mean()
        rows.append(
            {
                "date": date,
                "signal": signal,
                "ls_return": ls_ret,
                "n_long": len(top),
                "n_short": len(bottom),
            }
        )

    return pd.DataFrame(rows)


def cumulative_ls(ls: pd.DataFrame) -> pd.DataFrame:
    if ls.empty:
        return ls
    out = ls.sort_values("date").copy()
    out["cum_ls"] = out.groupby("signal")["ls_return"].cumsum()
    return out


def signal_summary(
    panel: pd.DataFrame,
    forward_col: str = "fwd_ret_21d",
    min_names: int = 3,
) -> pd.DataFrame:
    """Summary stats per signal: mean IC, hit rate, ann. long-short Sharpe proxy."""
    summaries = []
    for signal in SIGNAL_COLS:
        if signal not in panel.columns:
            continue

        ic_df = cross_sectional_ic(panel, signal, forward_col, min_names=min_names)
        ls_df = long_short_returns(panel, signal, forward_col, min_names=min_names)

        mean_ic = ic_df["ic"].mean() if not ic_df.empty else np.nan
        ic_hit = (ic_df["ic"] > 0).mean() if not ic_df.empty else np.nan

        if not ls_df.empty:
            daily = ls_df["ls_return"]
            ann_factor = np.sqrt(252)
            sharpe = (daily.mean() / daily.std() * ann_factor) if daily.std() > 0 else np.nan
            cum = daily.sum()
        else:
            sharpe = np.nan
            cum = np.nan

        summaries.append(
            {
                "signal": signal,
                "orientation": SIGNAL_ORIENTATION[signal],
                "mean_ic": mean_ic,
                "ic_hit_rate": ic_hit,
                "ls_cum_log_return": cum,
                "ls_sharpe_proxy": sharpe,
                "n_ic_days": len(ic_df),
                "n_ls_days": len(ls_df),
            }
        )

    return pd.DataFrame(summaries)
