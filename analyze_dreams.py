#!/usr/bin/env python3
"""Build the dream-symbol ratio series and look for periods where a symbol's
share of dream-interpretation search deviated from its own typical level.

    python analyze_dreams.py

Reads data/trends_export/dreams/batch*.csv (written by fetch_dream_trends.py),
computes <symbol>/"dream meaning" for each symbol, and writes:

  results/dream_symbols_ratio.png    small multiples, one panel per symbol
  results/dream_symbols_heatmap.png  symbol x month heatmap of robust z-score

...then prints the top deviation months per symbol so you can eyeball whether
any line up across symbols or with known events. Exploratory only -- no null
model, no FDR; see README's "Known limitations" for the same discipline as the
rest of this repo.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.dream_trends import load_dream_symbols, load_ratio_frame, robust_z

RESULTS_DIR = Path(__file__).resolve().parent / "results"
Z_FLAG = 2.5  # |robust z| at/above this counts as a notable deviation month

# "<symbol> dream meaning" as an exact-phrase search pattern barely existed
# before ~2009-2012 (dream-interpretation SEO content proliferated later) --
# every symbol has long literal-zero runs before then (flood's last zero month
# is as late as 2012-04). That's a real regime change in the query genre
# itself, not a content signal, and z-scoring across it manufactures fake
# "co-spikes" out of a flat-zero run meeting real data. Deviation detection is
# restricted to the reliable window (with margin past every symbol's last-zero
# month); the raw small-multiples plot still shows full history with the
# cutoff marked so you can see the emergence for yourself.
ANALYSIS_START = "2013-01-01"

# Google Trends' most recent ~2-3 months are provisional and get revised as
# more data comes in (a documented pytrends/Trends quirk) -- confirmed here:
# in 2026-05/06 BOTH "water dream meaning" and the baseline itself spike to
# ~100 together, an edge effect, not a content signal. Trim the unstable tail.
ANALYSIS_END_MARGIN_MONTHS = 3


def plot_small_multiples(ratio: pd.DataFrame, labels: dict[str, str]) -> Path:
    keys = list(ratio.columns)
    ncols = 3
    nrows = -(-len(keys) // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(15, 2.6 * nrows), squeeze=False)

    cutoff = pd.Timestamp(ANALYSIS_START)
    for ax, key in zip(axes.flat, keys):
        s = ratio[key].dropna()
        ax.plot(s.index, s.values, lw=1.1, color="#3B6EA5")
        reliable = s[s.index >= cutoff]
        if len(reliable):
            ax.axhline(reliable.median(), color="black", lw=0.6, ls="--", alpha=0.5)
        ax.axvspan(s.index.min(), cutoff, color="grey", alpha=0.12, lw=0, zorder=0)
        ax.set_title(labels[key], fontsize=9)
        ax.tick_params(labelsize=7)
    for ax in axes.flat[len(keys):]:
        ax.set_visible(False)

    fig.suptitle(
        "Dream-symbol share of “dream meaning” search (each symbol ÷ baseline, "
        f"dashed = median since {ANALYSIS_START[:7]}; shaded = pre-reliable-data)",
        fontsize=12,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / "dream_symbols_ratio.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def plot_heatmap(z: pd.DataFrame, labels: dict[str, str]) -> Path:
    keys = list(z.columns)
    mat = z[keys].to_numpy(dtype=float).T  # rows=symbols, cols=months

    fig_w = max(12, 0.06 * len(z.index))
    fig, ax = plt.subplots(figsize=(fig_w, 0.55 * len(keys) + 1.2))
    vmax = 4.0
    im = ax.imshow(mat, aspect="auto", cmap="RdBu_r", vmin=-vmax, vmax=vmax)

    ax.set_yticks(range(len(keys)))
    ax.set_yticklabels([labels[k] for k in keys], fontsize=9)

    year_starts = [i for i, d in enumerate(z.index) if d.month == 1]
    ax.set_xticks(year_starts)
    ax.set_xticklabels([z.index[i].year for i in year_starts], rotation=90, fontsize=7)

    cbar = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.01)
    cbar.set_label("robust z (deviation from the symbol's own typical share)", fontsize=8)

    ax.set_title(
        "When did each dream symbol run hotter/colder than its own norm? "
        f"(|z| ≥ {Z_FLAG} ≈ notable; {ANALYSIS_START[:7]}-present only)",
        fontsize=11,
    )
    fig.tight_layout()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / "dream_symbols_heatmap.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def main() -> None:
    baseline, symbols = load_dream_symbols()
    labels = {s.key: s.label for s in symbols}

    ratio = load_ratio_frame()
    if ratio.empty:
        print("No dream-symbol data found. Run `python fetch_dream_trends.py` first.")
        return

    have = list(ratio.columns)
    missing = [s.key for s in symbols if s.key not in have]
    print(f"Loaded {len(have)}/{len(symbols)} dream symbols: {', '.join(have)}")
    if missing:
        print(f"Missing (re-run fetch_dream_trends.py): {', '.join(missing)}")

    p1 = plot_small_multiples(ratio, labels)
    print(f"Wrote {p1}")

    end_cutoff = ratio.index.max() - pd.DateOffset(months=ANALYSIS_END_MARGIN_MONTHS)
    reliable = ratio[(ratio.index >= pd.Timestamp(ANALYSIS_START)) & (ratio.index <= end_cutoff)]
    print(
        f"\nRestricting deviation/spike detection to {ANALYSIS_START[:7]}..{end_cutoff:%Y-%m} "
        f"({len(reliable)} months) -- see ANALYSIS_START/_END_MARGIN comments in this file for why."
    )
    z = reliable.apply(robust_z)
    p2 = plot_heatmap(z, labels)
    print(f"Wrote {p2}")

    print(f"\n=== Notable months per symbol (|robust z| >= {Z_FLAG}) ===")
    for key in have:
        s = z[key].dropna()
        hot = s[s.abs() >= Z_FLAG].sort_values(key=lambda x: x.abs(), ascending=False)
        if hot.empty:
            print(f"  {labels[key]:14s} -- none")
            continue
        top = ", ".join(f"{d.strftime('%Y-%m')} (z={v:+.1f})" for d, v in hot.head(5).items())
        print(f"  {labels[key]:14s} {top}")

    print("\n=== Months where multiple symbols spiked together (>=3 symbols, |z|>=2.0) ===")
    co = (z.abs() >= 2.0).sum(axis=1)
    co_hits = co[co >= 3].sort_values(ascending=False)
    for d, n in co_hits.items():
        hot_syms = [labels[k] for k in have if abs(z.loc[d, k]) >= 2.0]
        print(f"  {d.strftime('%Y-%m')}  ({n} symbols): {', '.join(hot_syms)}")
    if co_hits.empty:
        print("  none")


if __name__ == "__main__":
    main()
