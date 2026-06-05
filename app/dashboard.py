"""Streamlit dashboard for options-implied signals and backtests."""

from __future__ import annotations

import sys
from pathlib import Path

# Streamlit runs this file directly; ensure repo root is on sys.path.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from backtest.engine import run_backtest
from signals.constants import SIGNAL_COLS, SIGNAL_ORIENTATION


def available_signals(df: pd.DataFrame) -> list[str]:
    return [c for c in SIGNAL_COLS if c in df.columns and df[c].notna().any()]

SAMPLE_SIGNALS = ROOT / "data" / "sample" / "signals.parquet"
FULL_SIGNALS = ROOT / "data" / "processed" / "signals.parquet"


def default_signals_path() -> Path:
    if FULL_SIGNALS.exists():
        return FULL_SIGNALS
    return SAMPLE_SIGNALS


@st.cache_data(show_spinner=False)
def load_signals(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    return df


@st.cache_data(show_spinner=False)
def load_backtest(signals_path: str, horizon: int) -> dict:
    signals = load_signals(signals_path)
    return run_backtest(signals=signals, forward_horizon=horizon)


def main() -> None:
    st.set_page_config(page_title="Options-Implied Signals", layout="wide")
    st.title("Options-Implied Equity Signals")

    default_signals = st.secrets.get("data", {}).get("signals_path", str(default_signals_path()))
    signals_path = st.sidebar.text_input("Signals parquet", default_signals)
    if not Path(signals_path).exists():
        st.error(f"Signals file not found: {signals_path}. Run `python run_signals.py` first.")
        st.stop()

    using_sample = Path(signals_path).resolve() == SAMPLE_SIGNALS.resolve()
    if using_sample:
        st.info("Showing bundled 2024 sample (SPY/QQQ/IWM). Run `python run_signals.py` locally for the full panel.")

    horizon = st.sidebar.selectbox("Forward horizon (days)", [5, 21, 63], index=1)
    symbols = st.sidebar.multiselect("Symbols", ["SPY", "QQQ", "IWM"], default=["SPY", "QQQ", "IWM"])

    signals = load_signals(signals_path)
    signals = signals[signals["underlying"].isin(symbols)]
    bt = load_backtest(signals_path, horizon)

    panel = bt["panel"]
    panel = panel[panel["underlying"].isin(symbols)]
    summary = bt["summary"]
    ic_daily = bt["ic_daily"]
    ls_daily = bt["ls_daily"]
    rolling_ic = bt["rolling_ic"]

    tab1, tab2, tab3, tab4 = st.tabs(["Signals", "Backtest", "Long-Short", "Data"])

    sig_cols = available_signals(signals)
    with tab1:
        signal = st.selectbox("Signal", sig_cols, index=min(1, len(sig_cols) - 1))
        fig = px.line(
            signals,
            x="date",
            y=signal,
            color="underlying",
            title=f"{signal} over time",
        )
        st.plotly_chart(fig, use_container_width=True)

        if f"iv_atm_30" in signals.columns:
            melt = signals.melt(
                id_vars=["date", "underlying"],
                value_vars=[c for c in signals.columns if c.startswith("iv_atm_")],
                var_name="tenor",
                value_name="iv",
            )
            fig2 = px.line(melt, x="date", y="iv", color="underlying", facet_col="tenor", title="ATM IV term structure")
            st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        st.subheader(f"Summary ({horizon}d forward returns)")
        st.dataframe(summary, use_container_width=True)

        if not ic_daily.empty:
            ic_mean = ic_daily.groupby("signal")["ic"].mean().reset_index()
            fig_ic = px.bar(
                ic_mean,
                x="signal",
                y="ic",
                title="Mean cross-sectional IC (oriented)",
                color="signal",
            )
            fig_ic.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig_ic, use_container_width=True)

        if not rolling_ic.empty:
            fig_roll = px.line(
                rolling_ic,
                x="date",
                y="rolling_ic",
                color="signal",
                title="Rolling IC (126d)",
            )
            fig_roll.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig_roll, use_container_width=True)

        st.caption("Orientation: " + ", ".join(f"{k}×{v}" for k, v in SIGNAL_ORIENTATION.items()))

    with tab3:
        ls_signal = st.selectbox("Long-short signal", sig_cols, index=min(1, len(sig_cols) - 1), key="ls_signal")
        ls_sub = ls_daily[ls_daily["signal"] == ls_signal] if not ls_daily.empty else pd.DataFrame()
        if ls_sub.empty:
            st.info("Not enough cross-sectional breadth for long-short series.")
        else:
            fig_ls = go.Figure()
            fig_ls.add_trace(go.Scatter(x=ls_sub["date"], y=ls_sub["cum_ls"], mode="lines", name="Cumulative LS"))
            fig_ls.update_layout(title=f"Cumulative long-short: {ls_signal}", xaxis_title="Date", yaxis_title="Cum log return")
            st.plotly_chart(fig_ls, use_container_width=True)

    with tab4:
        st.dataframe(panel.tail(200), use_container_width=True)
        csv = panel.to_csv(index=False).encode()
        st.download_button("Download panel CSV", csv, "backtest_panel.csv", "text/csv")


if __name__ == "__main__":
    main()
