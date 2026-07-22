"""Shared configuration for the analysis pipeline.

Windows are expressed in weeks relative to an event date (week 0 = the week the
event lands). Google Trends returns weekly granularity when a query spans
roughly 9 months to 5 years, so a per-event window of ~15 months gives us clean
weekly series without cross-window normalization headaches.
"""
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
ONTOLOGY_DIR = ROOT / "ontology"
RESULTS_DIR = ROOT / "results"


@dataclass(frozen=True)
class WindowConfig:
    # Full window fetched around each event.
    fetch_start_week: int = -60
    fetch_end_week: int = 12
    # "Far" baseline the term is compared against (its own normal level).
    baseline_start_week: int = -52
    baseline_end_week: int = -13
    # The lead window: does symbolic interest rise here, BEFORE the event?
    pre_start_week: int = -12
    pre_end_week: int = -1


DEFAULT_WINDOWS = WindowConfig()

# Null model / significance settings.
N_PLACEBO_DATES = 200        # random dates per term for the empirical null
PLACEBO_GUARD_WEEKS = 26     # keep placebo dates this far from any real event
FDR_ALPHA = 0.10             # Benjamini-Hochberg false-discovery rate
RANDOM_SEED = 20260722
