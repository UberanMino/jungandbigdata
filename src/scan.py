"""Broad exploratory scan: every term x every event -> lift, nulls, FDR.

Output is explicitly framed as HYPOTHESIS GENERATION. A term surviving FDR here
is a candidate worth a focused, pre-registered follow-up study, not a result.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .analysis import aggregate_lift, pre_event_lift
from .config import DEFAULT_WINDOWS, FDR_ALPHA, RANDOM_SEED, RESULTS_DIR, WindowConfig
from .nulls import benjamini_hochberg, empirical_null_p
from .ontology import Event, Term, load_all_terms, load_events


def _relevant_events(term: Term, events: list[Event]) -> list[Event]:
    """Literal terms are scored only against events in their own category;
    symbolic and placebo terms are scored against all events."""
    if term.channel == "literal":
        return [e for e in events if e.category == term.group]
    return events


def run_scan(
    mode: str = "synthetic",
    plant_signal: float = 0.0,
    geo: str = "",
    cfg: WindowConfig = DEFAULT_WINDOWS,
    run_nulls: bool = True,
    verbose: bool = True,
) -> pd.DataFrame:
    from .trends import get_provider

    terms = load_all_terms()
    events = load_events()
    provider = get_provider(mode, plant_signal=plant_signal, geo=geo)
    # Synthetic testing plants signal only at real event dates (never at null dates).
    if hasattr(provider, "event_dates"):
        provider.event_dates = {e.date for e in events}
    rng = np.random.default_rng(RANDOM_SEED)

    rows = []
    for i, term in enumerate(terms):
        rel = _relevant_events(term, events)
        lifts = [
            pre_event_lift(
                provider.fetch_weekly(term.query, e.date, cfg, channel=term.channel), cfg
            )
            for e in rel
        ]
        agg = aggregate_lift(lifts)
        p = np.nan
        if run_nulls and agg["n"] > 0:
            p = empirical_null_p(
                agg["mean_lift"], agg["n"], term.query, term.channel,
                events, provider, cfg, rng,
            )
        rows.append(
            {
                "query": term.query,
                "channel": term.channel,
                "group": term.group,
                "n_events": agg["n"],
                "mean_lift": agg["mean_lift"],
                "median_lift": agg["median_lift"],
                "sd_lift": agg["sd_lift"],
                "p_empirical": p,
            }
        )
        if verbose:
            print(
                f"[{i + 1:3d}/{len(terms)}] {term.channel:8s} {term.query:22s} "
                f"mean_lift={agg['mean_lift']:+.3f} p={p:.3f}"
                if not np.isnan(p)
                else f"[{i + 1:3d}/{len(terms)}] {term.channel:8s} {term.query:22s} "
                f"mean_lift={agg['mean_lift']:+.3f}"
            )

    df = pd.DataFrame(rows)

    if run_nulls:
        bh = benjamini_hochberg(df.set_index("query")["p_empirical"], FDR_ALPHA)
        df = df.merge(
            bh.rename(columns={"q": "q_value", "reject": "fdr_significant"})[
                ["q_value", "fdr_significant"]
            ],
            left_on="query",
            right_index=True,
            how="left",
        )
        df["fdr_significant"] = df["fdr_significant"].fillna(False)
    else:
        df["q_value"] = np.nan
        df["fdr_significant"] = False

    return df.sort_values("mean_lift", ascending=False).reset_index(drop=True)


def save_results(df: pd.DataFrame) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(RESULTS_DIR / "scan_summary.csv", index=False)

    # Channel comparison: symbolic lift should beat placebo to be interesting.
    channel_means = df.groupby("channel")["mean_lift"].mean()
    channel_means.to_csv(RESULTS_DIR / "channel_means.csv")

    try:
        _plot(df)
    except Exception as exc:  # plotting is a nicety, never fatal
        print(f"(skipped plot: {exc})")


def _plot(df: pd.DataFrame) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    order = {"symbolic": 0, "literal": 1, "placebo": 2}
    colors = {"symbolic": "#4C72B0", "literal": "#55A868", "placebo": "#C44E52"}
    d = df.sort_values(["channel", "mean_lift"], key=lambda s: s.map(order).fillna(s))

    fig, ax = plt.subplots(figsize=(9, max(4, 0.28 * len(d))))
    ax.barh(
        range(len(d)),
        d["mean_lift"],
        color=[colors.get(c, "#888") for c in d["channel"]],
    )
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels(d["query"], fontsize=7)
    ax.axvline(0, color="k", lw=0.8)
    ax.set_xlabel("Mean standardized pre-event lift (z)")
    ax.set_title("Pre-event lift by term (blue=symbolic, green=literal, red=placebo)")
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "pre_event_lift.png", dpi=130)
    plt.close(fig)
