"""Load the brand-archetype -> ticker ontology (brands.yaml).

Mirrors src/symbols.py in spirit: a small, dependency-light loader over a
human-editable YAML file. Downstream code groups brands by archetype to build
per-archetype stock indices, so the grouping helpers live here too.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BRANDS_FILE = ROOT / "brands.yaml"


@dataclass(frozen=True)
class Brand:
    name: str
    ticker: str
    archetype: str
    archetype_desc: str = ""


def load_brands() -> list[Brand]:
    data = yaml.safe_load(BRANDS_FILE.read_text())
    out: list[Brand] = []
    for archetype, spec in data.get("archetypes", {}).items():
        desc = spec.get("description", "")
        for b in spec.get("brands", []):
            out.append(
                Brand(
                    name=b["name"],
                    ticker=b["ticker"],
                    archetype=archetype,
                    archetype_desc=desc,
                )
            )
    return out


def by_archetype(brands: list[Brand] | None = None) -> dict[str, list[Brand]]:
    """Group brands under their archetype, preserving file order."""
    brands = brands if brands is not None else load_brands()
    grouped: dict[str, list[Brand]] = {}
    for b in brands:
        grouped.setdefault(b.archetype, []).append(b)
    return grouped


def all_tickers(brands: list[Brand] | None = None) -> list[str]:
    brands = brands if brands is not None else load_brands()
    return [b.ticker for b in brands]
