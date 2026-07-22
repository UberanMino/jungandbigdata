"""Loaders for the archetype and literal-control ontologies and the event list."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd
import yaml

from .config import DATA_DIR, ONTOLOGY_DIR


@dataclass(frozen=True)
class Term:
    query: str            # the actual string sent to Google Trends
    channel: str          # "symbolic" | "literal" | "placebo"
    group: str            # archetype name, event category, or "placebo"


def load_archetype_terms() -> list[Term]:
    data = yaml.safe_load((ONTOLOGY_DIR / "archetypes.yaml").read_text())
    terms: list[Term] = []
    for name, spec in data["archetypes"].items():
        for q in spec.get("symbolic", []):
            terms.append(Term(query=q, channel="symbolic", group=name))
    return terms


def load_literal_terms() -> list[Term]:
    data = yaml.safe_load((ONTOLOGY_DIR / "literal_controls.yaml").read_text())
    terms: list[Term] = []
    for category, spec in data["categories"].items():
        for q in spec.get("literal", []):
            terms.append(Term(query=q, channel="literal", group=category))
    return terms


def load_placebo_terms() -> list[Term]:
    path = DATA_DIR / "placebo_terms.txt"
    terms: list[Term] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        terms.append(Term(query=line, channel="placebo", group="placebo"))
    return terms


def load_all_terms() -> list[Term]:
    return load_archetype_terms() + load_literal_terms() + load_placebo_terms()


@dataclass(frozen=True)
class Event:
    date: date
    name: str
    category: str


def load_events() -> list[Event]:
    df = pd.read_csv(DATA_DIR / "events.csv", parse_dates=["date"])
    return [
        Event(date=row.date.date(), name=row.name, category=row.category)
        for row in df.itertuples()
    ]
