"""Dream-symbol Trends fetcher + ratio analysis.

Each "<symbol> dream meaning" query and the generic "dream meaning" baseline
are pulled INDEPENDENTLY (one query per Trends request), each getting its own
full 0-100 resolution based on its own search volume. This matters: an earlier
version batched symbols together with the baseline in one request so they'd
share a scale, but "dream meaning" has vastly higher volume than any single
symbol phrase, so Trends floors the rare symbols down to near-zero (or exactly
zero, for the rarest) when forced onto the baseline's scale -- a crowding
artifact, not a real absence of signal.

Instead we divide two *independently*-normalized series: ratio = symbol_series
/ baseline_series. This ratio's absolute height is not comparable across
symbols (each symbol's own 100 means something different), but that's fine for
what we actually do with it -- flag months where a symbol's ratio deviates from
*its own* historical median (robust z-score), which is invariant to whatever
constant scale factor each series carries.

Reuses src/trends.py's FullHistoryFetcher (long-window stitching + polite
backoff + per-window caching) by handing it a custom Cluster list instead of
the main symbols.yaml.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import yaml

from .config import ROOT
from .symbols import Cluster
from .trends import FullHistoryFetcher, FetchReport

DREAM_FILE = ROOT / "dream_symbols.yaml"
DREAM_EXPORT_DIR = ROOT / "data" / "trends_export" / "dreams"
BASELINE_KEY = "baseline"


@dataclass(frozen=True)
class DreamSymbol:
    key: str
    label: str
    query: str


def load_dream_symbols() -> tuple[str, list[DreamSymbol]]:
    data = yaml.safe_load(DREAM_FILE.read_text())
    baseline = data["baseline"]
    symbols = [
        DreamSymbol(key=k, label=s["label"], query=s["query"])
        for k, s in data["symbols"].items()
    ]
    return baseline, symbols


def _dream_clusters() -> list[Cluster]:
    baseline, symbols = load_dream_symbols()
    clusters = [Cluster(key=BASELINE_KEY, label="dream meaning (baseline)", queries=[baseline])]
    clusters += [Cluster(key=s.key, label=s.label, queries=[s.query]) for s in symbols]
    return clusters


def fetch_all(
    geo: str = "", pause: float = 8.0, backoff: float = 10.0, tries: int = 8
) -> FetchReport:
    fetcher = FullHistoryFetcher(
        geo=geo, pause=pause, backoff=backoff, tries=tries, export_dir=DREAM_EXPORT_DIR
    )
    return fetcher.run(clusters=_dream_clusters())


# ---------------------------------------------------------------------------
# Ratio analysis (reads what fetch_all wrote: one single-column CSV per query)
# ---------------------------------------------------------------------------


def load_ratio_frame() -> pd.DataFrame:
    """symbol_key -> (symbol's own-scale series / baseline's own-scale series)."""
    from .trends_import import read_export

    baseline_path = DREAM_EXPORT_DIR / f"{BASELINE_KEY}.csv"
    if not baseline_path.exists():
        return pd.DataFrame()
    baseline_df = read_export(baseline_path)
    baseline_series = baseline_df.iloc[:, 0].astype(float).replace(0, np.nan)

    _, symbols = load_dream_symbols()
    series = {}
    for s in symbols:
        path = DREAM_EXPORT_DIR / f"{s.key}.csv"
        if not path.exists():
            continue
        df = read_export(path)
        sym_series = df.iloc[:, 0].astype(float)
        series[s.key] = sym_series / baseline_series

    out = pd.DataFrame(series).sort_index()
    out.index.name = "date"
    return out


def robust_z(s: pd.Series) -> pd.Series:
    """Deviation from the series' own typical level, in MAD-based robust sigma.

    Invariant to any positive constant scaling of `s` -- exactly what's needed
    since each symbol's ratio carries its own, otherwise-incomparable scale.
    """
    med = s.median()
    mad = (s - med).abs().median()
    sigma = mad * 1.4826
    if not sigma or pd.isna(sigma) or sigma == 0:
        sigma = s.std()
    if not sigma or pd.isna(sigma) or sigma == 0:
        return s * 0.0
    return (s - med) / sigma
