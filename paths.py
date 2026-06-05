"""Repository path constants — single source for data and config locations."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent

DATA_DIR = ROOT / "data"
DATA_RAW = DATA_DIR / "raw"
DATA_RAW_RELEASE = DATA_RAW / "release"
DATA_PROCESSED = DATA_DIR / "processed"
DATA_SAMPLE = DATA_DIR / "sample"

SIGNALS_PARQUET = DATA_PROCESSED / "signals.parquet"
SAMPLE_SIGNALS_PARQUET = DATA_SAMPLE / "signals.parquet"

CONFIG_PATH = ROOT / "config.yaml"
