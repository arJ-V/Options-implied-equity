from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from signals.config import AppConfig, load_config
from signals.data import attach_spot, load_options, load_underlying
from signals.earnings import apply_earnings_mask, fetch_earnings_dates
from signals.filters import apply_quote_filters
from signals.implied_skew import compute_implied_skew_panel
from signals.put_call_spread import compute_put_call_spread
from signals.risk_reversal import compute_risk_reversal
from signals.smirk import compute_smirk
from signals.surface import build_surface_grid
from signals.term_slope import compute_term_slope
from signals.vrp import compute_realized_vol, compute_vrp


def compute_signals_for_symbol(
    symbol: str,
    cfg: AppConfig | None = None,
    start: str | None = None,
    end: str | None = None,
    earnings: pd.DataFrame | None = None,
) -> pd.DataFrame:
    cfg = cfg or load_config()
    start_ts = pd.Timestamp(start) if start else None
    end_ts = pd.Timestamp(end) if end else None

    options = load_options(symbol, cfg, start_ts, end_ts)
    underlying = load_underlying(symbol, cfg, start_ts, end_ts)
    underlying["underlying"] = symbol.upper()

    chain = attach_spot(options, underlying)
    chain["underlying"] = symbol.upper()
    filtered = apply_quote_filters(chain, cfg.surface)

    surface = build_surface_grid(filtered, cfg.surface)
    if surface.empty:
        return pd.DataFrame()

    pcs = compute_put_call_spread(filtered)
    rv = compute_realized_vol(underlying, window=cfg.timing.rv_window_trading_days)

    panel = surface.copy()
    panel["smirk"] = compute_smirk(panel, maturity_days=30)

    rr = compute_risk_reversal(panel, maturity_days=30)
    panel["risk_reversal"] = rr["risk_reversal"]
    panel["risk_reversal_norm"] = rr["risk_reversal_norm"]

    panel["term_slope"] = compute_term_slope(panel, short_days=30, long_days=90)
    panel["vrp"] = compute_vrp(panel, rv, maturity_days=30)
    panel = panel.merge(pcs, on=["date", "underlying"], how="left")

    if cfg.bkm.enabled:
        skew = compute_implied_skew_panel(
            filtered,
            target_dte=cfg.bkm.target_dte,
            risk_free_rate=cfg.bkm.risk_free_rate,
        )
        panel = panel.merge(skew, on=["date", "underlying"], how="left")

    if cfg.earnings.exclude_in_term_slope:
        earnings = earnings if earnings is not None else fetch_earnings_dates([symbol])
        panel = apply_earnings_mask(
            panel,
            earnings,
            signal_col="term_slope",
            lookahead_days=cfg.earnings.lookahead_days,
        )

    return panel.sort_values("date").reset_index(drop=True)


def compute_signals(
    symbols: list[str],
    cfg: AppConfig | None = None,
    start: str | None = None,
    end: str | None = None,
    parallel: bool = True,
) -> pd.DataFrame:
    cfg = cfg or load_config()
    earnings = fetch_earnings_dates(symbols) if cfg.earnings.exclude_in_term_slope else pd.DataFrame()

    frames: list[pd.DataFrame] = []

    def _run(sym: str) -> pd.DataFrame:
        print(f"Computing signals for {sym}...")
        frame = compute_signals_for_symbol(sym, cfg=cfg, start=start, end=end, earnings=earnings)
        if not frame.empty:
            print(f"  {len(frame)} dates")
        else:
            print("  no output")
        return frame

    if parallel and len(symbols) > 1:
        with ThreadPoolExecutor(max_workers=min(3, len(symbols))) as pool:
            futures = {pool.submit(_run, sym): sym for sym in symbols}
            for fut in as_completed(futures):
                frame = fut.result()
                if not frame.empty:
                    frames.append(frame)
    else:
        for sym in symbols:
            frame = _run(sym)
            if not frame.empty:
                frames.append(frame)

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True).sort_values(["date", "underlying"]).reset_index(drop=True)
