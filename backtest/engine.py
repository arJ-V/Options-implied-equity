from __future__ import annotations

from pathlib import Path

import pandas as pd

from backtest.metrics import (
    cross_sectional_ic,
    cumulative_ls,
    long_short_returns,
    rolling_ic_mean,
    signal_summary,
)
from backtest.returns import compute_forward_log_returns, load_underlying_panel
from signals.config import AppConfig, load_config
from signals.constants import DEFAULT_FORWARD_HORIZONS, SIGNAL_COLS

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SIGNALS_PATH = ROOT / "data" / "processed" / "signals.parquet"
DEFAULT_BACKTEST_PATH = ROOT / "data" / "processed" / "backtest.parquet"
DEFAULT_SUMMARY_PATH = ROOT / "data" / "processed" / "backtest_summary.parquet"


def load_signals(path: Path | None = None) -> pd.DataFrame:
    path = path or DEFAULT_SIGNALS_PATH
    if not path.exists():
        raise FileNotFoundError(f"Signals file not found: {path}. Run run_signals.py first.")
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    return df


def run_backtest(
    signals: pd.DataFrame | None = None,
    signals_path: Path | None = None,
    cfg: AppConfig | None = None,
    horizons: tuple[int, ...] = DEFAULT_FORWARD_HORIZONS,
    forward_horizon: int = 21,
    ic_window: int = 126,
    min_names: int = 3,
) -> dict[str, pd.DataFrame]:
    cfg = cfg or load_config()
    signals = signals if signals is not None else load_signals(signals_path)

    symbols = sorted(signals["underlying"].unique())
    start = str(signals["date"].min().date())
    end = str(signals["date"].max().date())

    prices = load_underlying_panel(symbols, cfg=cfg, start=start, end=end)
    fwd = compute_forward_log_returns(prices, horizons=horizons)

    panel = signals.merge(fwd, on=["date", "underlying"], how="left")
    forward_col = f"fwd_ret_{forward_horizon}d"

    ic_frames = []
    ls_frames = []
    roll_frames = []
    for signal in SIGNAL_COLS:
        if signal not in panel.columns:
            continue
        ic = cross_sectional_ic(panel, signal, forward_col, min_names=min_names)
        if not ic.empty:
            ic_frames.append(ic)
            roll = rolling_ic_mean(ic, window=ic_window)
            roll_frames.append(
                pd.DataFrame({"date": roll.index, "signal": signal, "rolling_ic": roll.values})
            )
        ls = long_short_returns(panel, signal, forward_col, min_names=min_names)
        if not ls.empty:
            ls_frames.append(ls)

    ic_daily = pd.concat(ic_frames, ignore_index=True) if ic_frames else pd.DataFrame()
    ls_daily = pd.concat(ls_frames, ignore_index=True) if ls_frames else pd.DataFrame()
    ls_cum = cumulative_ls(ls_daily)
    rolling_ic = pd.concat(roll_frames, ignore_index=True) if roll_frames else pd.DataFrame()
    summary = signal_summary(panel, forward_col=forward_col, min_names=min_names)

    return {
        "panel": panel,
        "ic_daily": ic_daily,
        "ls_daily": ls_cum,
        "rolling_ic": rolling_ic,
        "summary": summary,
    }


def save_backtest(results: dict[str, pd.DataFrame], output_dir: Path | None = None) -> Path:
    output_dir = output_dir or (ROOT / "data" / "processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    results["panel"].to_parquet(output_dir / "backtest_panel.parquet", index=False)
    results["ic_daily"].to_parquet(output_dir / "backtest_ic.parquet", index=False)
    results["ls_daily"].to_parquet(output_dir / "backtest_ls.parquet", index=False)
    results["rolling_ic"].to_parquet(output_dir / "backtest_rolling_ic.parquet", index=False)
    results["summary"].to_parquet(output_dir / "backtest_summary.parquet", index=False)
    return output_dir
