"""Is an archetype basket's sector-neutralized return real, or just small-N luck?

Mirrors src/nulls.py's method for the Trends side, applied to stocks: with only
~4-5 brands per archetype, a large-looking excess-return gap (magician +119%,
sage -35%) can easily happen by chance. Each archetype gets an empirical null:
draw many random same-size baskets from the full brand universe (ignoring the
real archetype labels), score them with the identical statistic (10y
sector-neutralized excess return, daily-rebalanced equal-weight). The real
basket's return earns a two-sided empirical p-value against that null --
"how often does an arbitrary same-size grab of these 51 stocks look this
extreme" -- and Benjamini-Hochberg FDR is applied across all 12 archetypes,
exactly like the Trends side's per-term nulls.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from .brands import Brand, by_archetype
from .config import FDR_ALPHA, RANDOM_SEED
from .nulls import benjamini_hochberg


def brand_excess_return_frame(
    brands: list[Brand],
    series_by_ticker: dict[str, pd.Series],
    sector_series_by_ticker: dict[str, pd.Series],
) -> pd.DataFrame:
    """Each brand's own daily excess return (over its sector ETF), one column each."""
    cols = {}
    for b in brands:
        brand_s = series_by_ticker.get(b.ticker)
        sector_s = sector_series_by_ticker.get(b.sector) if b.sector else None
        if brand_s is None or brand_s.empty or sector_s is None or sector_s.empty:
            continue
        combined = pd.DataFrame({"brand": brand_s, "sector": sector_s}).sort_index().ffill()
        cols[b.ticker] = combined["brand"].pct_change() - combined["sector"].pct_change()
    return pd.DataFrame(cols).sort_index()


def _basket_total_return(sub: np.ndarray) -> float:
    """Total compounded return (%) of an equal-weight, daily-rebalanced basket."""
    valid = ~np.isnan(sub).all(axis=1)
    if not valid.any():
        return float("nan")
    sub = sub[np.argmax(valid):]
    # A row can still be all-NaN inside the trimmed range (e.g. a mix of US and
    # foreign-listed tickers on a day only one side trades) -- nanmean warns on
    # those and returns NaN, which nan_to_num then treats as a flat 0% day,
    # consistent with archetype_index/archetype_excess_index's own fillna(0.0).
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        row_mean = np.nanmean(sub, axis=1)
    row_mean = np.nan_to_num(row_mean, nan=0.0)
    return float((np.cumprod(1.0 + row_mean)[-1] - 1.0) * 100.0)


def archetype_significance(
    brands: list[Brand],
    series_by_ticker: dict[str, pd.Series],
    sector_series_by_ticker: dict[str, pd.Series],
    n_bootstrap: int = 2000,
    seed: int = RANDOM_SEED,
    alpha: float = FDR_ALPHA,
) -> pd.DataFrame:
    """Empirical two-sided p-value + BH q-value for each archetype's basket return.

    Null for an archetype with k members: draw a random size-k subset of tickers
    from the WHOLE brand universe (not excluding the archetype's real members --
    same independent-draw approach as the Trends side's per-term placebo dates),
    score it with the same statistic, repeat n_bootstrap times. p = how often a
    random same-size basket is at least as extreme as the real one, two-sided.
    """
    returns = brand_excess_return_frame(brands, series_by_ticker, sector_series_by_ticker)
    tickers = list(returns.columns)
    data = returns.to_numpy()
    ticker_idx = {t: i for i, t in enumerate(tickers)}
    n_tickers = len(tickers)
    rng = np.random.default_rng(seed)

    grouped = by_archetype(brands)
    rows = []
    for archetype, members in grouped.items():
        idxs = [ticker_idx[b.ticker] for b in members if b.ticker in ticker_idx]
        k = len(idxs)
        if k == 0 or k > n_tickers:
            continue
        observed = _basket_total_return(data[:, idxs])

        null_vals = np.empty(n_bootstrap)
        for i in range(n_bootstrap):
            draw = rng.choice(n_tickers, size=k, replace=False)
            null_vals[i] = _basket_total_return(data[:, draw])
        null_vals = null_vals[~np.isnan(null_vals)]
        if null_vals.size == 0:
            continue

        p_high = (np.sum(null_vals >= observed) + 1) / (null_vals.size + 1)
        p_low = (np.sum(null_vals <= observed) + 1) / (null_vals.size + 1)
        p = min(1.0, 2 * min(p_high, p_low))

        rows.append({
            "archetype": archetype,
            "n_brands": k,
            "observed_excess_return": observed,
            "null_mean": float(np.mean(null_vals)),
            "null_std": float(np.std(null_vals)),
            "p_value": p,
        })

    df = pd.DataFrame(rows).set_index("archetype")
    if df.empty:
        return df
    bh = benjamini_hochberg(df["p_value"], alpha=alpha)
    df["q_value"] = bh["q"].reindex(df.index)
    df["significant"] = bh["reject"].reindex(df.index).fillna(False)
    return df.sort_values("p_value")
