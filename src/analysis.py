"""Core metric: standardized pre-event lift.

For one term's weekly series around one event we ask: did interest in the
pre-event lead window rise, relative to the term's own far baseline? We
standardize by the baseline's own variability so a noisy term and a calm term
are on the same scale, and so the number is comparable across terms:

    lift_z = (mean(pre_window) - mean(baseline)) / std(baseline)

A positive lift_z means the term ran hotter than usual in the ~quarter before
the event. This says nothing about causation on its own -- that is what the null
models in nulls.py are for.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import WindowConfig


def _window_mean(series: pd.Series, lo: int, hi: int) -> float:
    mask = (series.index >= lo) & (series.index <= hi)
    vals = series[mask].to_numpy(dtype=float)
    vals = vals[~np.isnan(vals)]
    return float(np.mean(vals)) if vals.size else np.nan


def pre_event_lift(series: pd.Series, cfg: WindowConfig) -> float:
    """Standardized lift of the pre-event window over the far baseline."""
    base_mask = (series.index >= cfg.baseline_start_week) & (
        series.index <= cfg.baseline_end_week
    )
    base = series[base_mask].to_numpy(dtype=float)
    base = base[~np.isnan(base)]
    if base.size < 5:
        return np.nan

    base_mean = float(np.mean(base))
    base_std = float(np.std(base, ddof=1))
    if base_std == 0:
        return np.nan

    pre_mean = _window_mean(series, cfg.pre_start_week, cfg.pre_end_week)
    if np.isnan(pre_mean):
        return np.nan
    return (pre_mean - base_mean) / base_std


def aggregate_lift(lifts: list[float]) -> dict:
    """Summarize a term's lift across many events."""
    arr = np.array([x for x in lifts if not np.isnan(x)], dtype=float)
    if arr.size == 0:
        return {"n": 0, "mean_lift": np.nan, "median_lift": np.nan, "sd_lift": np.nan}
    return {
        "n": int(arr.size),
        "mean_lift": float(np.mean(arr)),
        "median_lift": float(np.median(arr)),
        "sd_lift": float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0,
    }
