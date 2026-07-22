"""Read Google Trends 'Interest over time' CSV exports into tidy DataFrames.

The export format looks like::

    Category: All categories

    Month,snake + serpent: (Worldwide)
    2004-01,45
    2004-02,47
    ...

The first column is Day / Week / Month depending on the timeframe; low-volume
cells come through as the literal string "<1". We parse defensively: skip the
metadata preamble, take the first column as the date, strip the ": (Region)"
suffix from series names, and coerce "<1" to 0.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .symbols import EXPORT_DIR, Cluster, load_clusters

_DATE_HEADERS = {"day", "week", "month", "time"}


def _find_header_row(lines: list[str]) -> int:
    for i, line in enumerate(lines):
        first = line.split(",", 1)[0].strip().strip('"').lower()
        if first in _DATE_HEADERS:
            return i
    raise ValueError("no Day/Week/Month header row found -- is this a Trends export?")


def read_export(path: Path) -> pd.DataFrame:
    """Return a DataFrame indexed by date, one column per series in the file."""
    lines = path.read_text().splitlines()
    header = _find_header_row(lines)
    df = pd.read_csv(path, skiprows=header)
    date_col = df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).set_index(date_col)
    df.index.name = "date"

    # Clean series: "<1" -> 0, everything numeric.
    df = df.apply(lambda s: pd.to_numeric(s.replace("<1", 0), errors="coerce"))
    # Strip ": (Worldwide)" / ": (United States)" suffixes from column names.
    df.columns = [str(c).split(":", 1)[0].strip() for c in df.columns]
    return df


def load_available(export_dir: Path = EXPORT_DIR) -> dict[str, pd.DataFrame]:
    """Load every cluster whose CSV export is present on disk.

    Matches files by cluster key: data/trends_export/<key>.csv
    """
    clusters = {c.key: c for c in load_clusters()}
    found: dict[str, pd.DataFrame] = {}
    if not export_dir.exists():
        return found
    for path in sorted(export_dir.glob("*.csv")):
        key = path.stem
        if key in clusters:
            found[key] = read_export(path)
    return found


def missing_exports(export_dir: Path = EXPORT_DIR) -> list[Cluster]:
    have = set(load_available(export_dir).keys())
    return [c for c in load_clusters() if c.key not in have]
