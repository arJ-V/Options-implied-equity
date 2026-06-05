from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = ROOT / "config.yaml"


@dataclass(frozen=True)
class SurfaceConfig:
    min_bid: float
    drop_crossed_markets: bool
    max_spread_pct_of_mid: float
    min_open_interest: int
    moneyness_min: float
    moneyness_max: float
    dte_min: int
    dte_max: int
    put_deltas: tuple[float, ...]
    call_deltas: tuple[float, ...]
    maturities_days: tuple[int, ...]


@dataclass(frozen=True)
class TimingConfig:
    rv_window_trading_days: int


@dataclass(frozen=True)
class EarningsConfig:
    exclude_in_term_slope: bool
    lookahead_days: int


@dataclass(frozen=True)
class BKMConfig:
    enabled: bool
    target_dte: int
    risk_free_rate: float
    synthetic_skew_tolerance: float


@dataclass(frozen=True)
class AppConfig:
    surface: SurfaceConfig
    timing: TimingConfig
    earnings: EarningsConfig
    bkm: BKMConfig
    raw_data_dir: Path
    dubach_base_url: str
    starter_release_url: str
    starter_symbols: tuple[str, ...]


def load_config(path: Path | None = None) -> AppConfig:
    cfg_path = path or DEFAULT_CONFIG_PATH
    with open(cfg_path) as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    surface_raw = raw["surface"]
    filters = surface_raw["filters"]
    grid = surface_raw["grid"]
    data_raw = raw["data"]
    term = raw["signals"]["term_slope"]
    bkm_raw = raw["signals"]["implied_skew"]
    validation = raw.get("validation", {})

    return AppConfig(
        surface=SurfaceConfig(
            min_bid=float(filters["min_bid"]),
            drop_crossed_markets=bool(filters["drop_crossed_markets"]),
            max_spread_pct_of_mid=float(filters["max_spread_pct_of_mid"]),
            min_open_interest=int(filters["min_open_interest"]),
            moneyness_min=float(filters["moneyness_min"]),
            moneyness_max=float(filters["moneyness_max"]),
            dte_min=int(filters["dte_min"]),
            dte_max=int(filters["dte_max"]),
            put_deltas=tuple(float(x) for x in grid["put_deltas"]),
            call_deltas=tuple(float(x) for x in grid["call_deltas"]),
            maturities_days=tuple(int(x) for x in grid["maturities_days"]),
        ),
        timing=TimingConfig(
            rv_window_trading_days=int(raw["timing"]["rv_window_trading_days"]),
        ),
        earnings=EarningsConfig(
            exclude_in_term_slope=bool(term.get("exclude_earnings_in_short_window", True)),
            lookahead_days=int(term.get("earnings_lookahead_days", 30)),
        ),
        bkm=BKMConfig(
            enabled=bool(bkm_raw.get("enabled", False)),
            target_dte=30,
            risk_free_rate=float(bkm_raw.get("risk_free_rate", 0.05)),
            synthetic_skew_tolerance=float(validation.get("bkm_synthetic_skew_tolerance", 0.05)),
        ),
        raw_data_dir=ROOT / "data" / "raw" / "release",
        dubach_base_url=str(data_raw.get("dubach_base_url", "")),
        starter_release_url=str(data_raw.get("starter_release_url", "")),
        starter_symbols=tuple(str(x) for x in data_raw["starter_symbols"]),
    )
