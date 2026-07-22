"""Load the symbol clusters and build ready-to-click Google Trends export URLs."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import yaml

ROOT = Path(__file__).resolve().parent.parent
SYMBOLS_FILE = ROOT / "symbols.yaml"
EXPORT_DIR = ROOT / "data" / "trends_export"

TRENDS_EXPLORE = "https://trends.google.com/trends/explore"


@dataclass(frozen=True)
class Cluster:
    key: str          # also the expected CSV filename stem
    label: str
    queries: list[str]  # one entry for single clusters, N for co-normalized pairs

    @property
    def is_pair(self) -> bool:
        return len(self.queries) > 1


def load_clusters() -> list[Cluster]:
    data = yaml.safe_load(SYMBOLS_FILE.read_text())
    out: list[Cluster] = []
    for key, spec in data.get("clusters", {}).items():
        out.append(Cluster(key=key, label=spec["label"], queries=[spec["query"]]))
    for key, spec in data.get("pairs", {}).items():
        q = spec["query"]
        out.append(Cluster(key=key, label=spec["label"], queries=list(q)))
    return out


def explore_url(cluster: Cluster, date: str = "all", geo: str = "") -> str:
    """A direct 'Interest over time' explore link.

    date='all' -> 2004-present (monthly). geo='' -> worldwide.
    Comma-separated q compares terms on a shared scale (used for the pair).
    """
    q = ",".join(cluster.queries)
    params = f"date={quote(date)}&geo={quote(geo)}&q={quote(q)}"
    return f"{TRENDS_EXPLORE}?{params}"
