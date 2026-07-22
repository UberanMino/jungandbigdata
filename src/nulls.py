"""Null models and multiple-comparison control.

The whole point of a broad scan is that it will *always* surface some terms with
large mean pre-event lift, purely by chance and autocorrelation. Two guards:

1. Empirical null per term. We draw many random "placebo" dates that are NOT
   near any real event and compute the exact same lift statistic against the
   term's own series. That gives a distribution of lifts this term produces for
   nothing in particular. The observed real-event lift earns an empirical
   p-value = P(placebo lift >= observed). Because it reuses the same term's
   series, this automatically accounts for that term's seasonality and noise.

2. Benjamini-Hochberg FDR across all terms, so "significant" means significant
   after paying for how many terms we looked at.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from .analysis import pre_event_lift
from .config import N_PLACEBO_DATES, PLACEBO_GUARD_WEEKS, WindowConfig
from .ontology import Event


def _random_placebo_dates(
    events: list[Event], n: int, rng: np.random.Generator
) -> list[date]:
    """Random dates in the events' span, kept away from real events."""
    real = [pd.Timestamp(e.date) for e in events]
    lo = min(real) + pd.Timedelta(weeks=60)   # leave room for the fetch window
    hi = max(real) - pd.Timedelta(weeks=12)
    span_days = (hi - lo).days
    guard = timedelta(weeks=PLACEBO_GUARD_WEEKS)

    out: list[date] = []
    attempts = 0
    while len(out) < n and attempts < n * 50:
        attempts += 1
        cand = (lo + pd.Timedelta(days=int(rng.integers(0, span_days)))).date()
        if all(abs((cand - e.date).days) > guard.days for e in events):
            out.append(cand)
    return out


def empirical_null_p(
    observed_mean_lift: float,
    k_events: int,
    query: str,
    channel: str,
    events: list[Event],
    provider,
    cfg: WindowConfig,
    rng: np.random.Generator,
    n: int = N_PLACEBO_DATES,
    n_bootstrap: int = 2000,
) -> float:
    """One-sided empirical p-value for a term's observed mean lift.

    Critically, the null must match the observed *statistic*. The observed value
    is a mean lift over ``k_events`` real events, so the null is a distribution
    of mean lifts over ``k_events`` random placebo dates -- built by bootstrap-
    resampling the pool of per-placebo-date lifts. Comparing the K-event mean to
    single-date lifts (a wider distribution) would understate significance.
    """
    if np.isnan(observed_mean_lift) or k_events < 1:
        return np.nan
    placebo_dates = _random_placebo_dates(events, n, rng)
    pool = []
    for d in placebo_dates:
        series = provider.fetch_weekly(query, d, cfg, channel=channel)
        pool.append(pre_event_lift(series, cfg))
    pool = np.array([x for x in pool if not np.isnan(x)], dtype=float)
    if pool.size == 0:
        return np.nan

    idx = rng.integers(0, pool.size, size=(n_bootstrap, k_events))
    null_means = pool[idx].mean(axis=1)
    # +1 smoothing so p is never exactly 0.
    return float((np.sum(null_means >= observed_mean_lift) + 1) / (null_means.size + 1))


def benjamini_hochberg(pvals: pd.Series, alpha: float) -> pd.DataFrame:
    """Return q-values and a reject flag at FDR = alpha."""
    p = pvals.dropna().sort_values()
    m = len(p)
    if m == 0:
        return pd.DataFrame(columns=["p", "q", "reject"])
    ranks = np.arange(1, m + 1)
    q_raw = p.to_numpy() * m / ranks
    q = np.minimum.accumulate(q_raw[::-1])[::-1]  # enforce monotonicity
    thresh = alpha * ranks / m
    reject = p.to_numpy() <= thresh
    return pd.DataFrame({"p": p.to_numpy(), "q": q, "reject": reject}, index=p.index)
