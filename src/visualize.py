"""Pattern-spotting visuals: symbol time-series with world events overlaid.

Deliberately light on statistics -- this is for *looking*. Each Trends export is
normalized on its own 0-100 scale, so we compare shapes and timing, not levels.
Event dates are drawn as faint vertical lines so you can eyeball whether a
symbol tends to rise into them.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

from .brands import Brand, by_archetype
from .ontology import load_events
from .symbols import load_clusters

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"


def _event_lines(ax, events, ymax):
    for e in events:
        ax.axvline(pd.Timestamp(e.date), color="crimson", alpha=0.18, lw=1, zorder=0)


def plot_small_multiples(series_by_key: dict[str, pd.DataFrame], outfile: str = "symbols_overview.png"):
    clusters = {c.key: c for c in load_clusters()}
    events = load_events()
    keys = [k for k in clusters if k in series_by_key]
    if not keys:
        raise ValueError("no imported series to plot")

    ncols = 3
    nrows = -(-len(keys) // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(15, 2.6 * nrows), squeeze=False)

    for ax, key in zip(axes.flat, keys):
        df = series_by_key[key]
        for col in df.columns:
            ax.plot(df.index, df[col], lw=1.1, label=col)
        _event_lines(ax, events, df.max().max())
        ax.set_title(clusters[key].label, fontsize=9)
        ax.tick_params(labelsize=7)
        if df.shape[1] > 1:
            ax.legend(fontsize=6, loc="upper left")
    for ax in axes.flat[len(keys):]:
        ax.set_visible(False)

    fig.suptitle("Symbol search interest vs. world events (red lines = events)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / outfile
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def archetype_index(series_by_ticker: dict[str, pd.Series], members: list[Brand]) -> pd.Series:
    """Daily-rebalanced equal-weight index of an archetype's brands, based at 100.

    Rather than requiring every member to exist on day one (which would truncate
    the basket to its youngest brand), we average the *daily returns* of whichever
    members are trading each day and compound them into an index. So a brand that
    IPOs partway through simply joins its basket from that day on -- the natural
    way to handle staggered listings (Airbnb 2020, Coinbase 2021, Reddit 2024...).
    Composition therefore grows over the window; the index reads as "growth of an
    equal-weight, daily-rebalanced basket of this archetype's brands".
    """
    cols = {t: s for t, s in ((b.ticker, series_by_ticker.get(b.ticker)) for b in members)
            if s is not None and not s.empty}
    if not cols:
        return pd.Series(dtype=float)
    frame = pd.DataFrame(cols).sort_index()
    frame = frame.ffill()  # carry prices over market-holiday gaps; pre-IPO stays NaN
    first = frame.dropna(how="all").index.min()
    frame = frame.loc[first:]
    basket_ret = frame.pct_change().mean(axis=1, skipna=True).fillna(0.0)
    return (1.0 + basket_ret).cumprod() * 100.0


def plot_archetype_indices(
    series_by_ticker: dict[str, pd.Series],
    brands: list[Brand],
    outfile: str = "brand_archetype_indices.png",
):
    """One equal-weight, rebased-to-100 stock index per brand archetype."""
    grouped = by_archetype(brands)
    indices = {a: archetype_index(series_by_ticker, members) for a, members in grouped.items()}
    indices = {a: s for a, s in indices.items() if not s.empty}
    if not indices:
        raise ValueError("no stock series to plot")

    cmap = plt.get_cmap("tab20")
    fig, ax = plt.subplots(figsize=(14, 7))
    for i, (archetype, s) in enumerate(sorted(indices.items())):
        end = float(s.iloc[-1])
        ax.plot(s.index, s.values, lw=1.6, color=cmap(i % 20),
                label=f"{archetype}  ({end - 100:+.0f}%)")
    ax.axhline(100, color="k", lw=0.8, ls="--", alpha=0.6)
    # Log y-axis: equal % moves become equal vertical distances, so runaway
    # baskets (magician) compress and the laggards stay legible.
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(mticker.ScalarFormatter())
    ax.yaxis.set_minor_formatter(mticker.NullFormatter())
    ax.set_yticks([50, 100, 200, 400, 800, 1600])
    ax.set_title("Brand-archetype stock indices (daily-rebalanced equal-weight, based at 100, log scale)")
    ax.set_ylabel("index level (100 = start, log scale)")
    ax.legend(fontsize=8, ncol=2, loc="upper left")
    ax.grid(True, which="both", alpha=0.15)

    fig.tight_layout()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / outfile
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def plot_sun_moon_ratio(df: pd.DataFrame, outfile: str = "sun_moon_ratio.png"):
    """Sun/Moon co-normalized levels and their ratio over time."""
    events = load_events()
    cols = {c.lower(): c for c in df.columns}
    if "sun" not in cols or "moon" not in cols:
        return None
    sun = df[cols["sun"]].astype(float)
    moon = df[cols["moon"]].astype(float)
    ratio = sun / moon.replace(0, float("nan"))

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(13, 6), sharex=True)
    a1.plot(df.index, sun, label="Sun", color="#E1A100", lw=1.2)
    a1.plot(df.index, moon, label="Moon", color="#3B6EA5", lw=1.2)
    _event_lines(a1, events, df.max().max())
    a1.legend(fontsize=8)
    a1.set_title("Sun & Moon search interest (co-normalized)")

    a2.plot(df.index, ratio, color="#7A3B9C", lw=1.2)
    a2.axhline(1.0, color="k", lw=0.7, ls="--")
    _event_lines(a2, events, float(ratio.max()) if ratio.notna().any() else 1)
    a2.set_title("Sun / Moon ratio (>1 = solar/consciousness dominant)")
    a2.set_ylabel("ratio")

    fig.tight_layout()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / outfile
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path
