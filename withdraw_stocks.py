#!/usr/bin/env python3
"""Withdraw live stock prices for archetype-branded companies, grouped by archetype.

    python withdraw_stocks.py                 # 10y of daily prices, worldwide brands
    python withdraw_stocks.py --range 5y      # shorter window
    python withdraw_stocks.py --range 6mo --interval 1d

The premise (see brands.yaml): modern brands are built on the twelve Jungian
brand archetypes. This pulls each brand's adjusted daily price straight from
Yahoo Finance (no API key), writes one CSV per ticker into data/stocks/, and
renders results/brand_archetype_indices.png -- an equal-weight, rebased-to-100
stock index per archetype -- so you can eyeball whether an archetype's basket
has out- or under-performed. It also fetches each brand's SPDR sector ETF
benchmark and renders results/brand_archetype_excess_indices.png -- the same
baskets built from *excess* return over sector, isolating "this archetype's
brands beat their own industry" from "tech/growth had a good decade." Prints
per-brand and per-archetype tables for both views.

Both cumulative indices are anchored to the (somewhat arbitrary) start of the
window, so "how much has this basket gained since 2016" can obscure "how is it
doing lately." The CLI also renders each index's *rolling `--window`-day
return* -- brand_archetype_growth_rates.png and
brand_archetype_excess_growth_rates.png -- the discrete derivative of the
cumulative curves, showing trend rather than cumulative level.

The 12 baskets visibly move together (2020 crash, 2022 drawdown hit every
line). That's expected -- equities share market beta -- but it means "these
archetypes correlate" is not itself evidence of an archetype effect. The CLI
quantifies it directly: it fetches SPY as a market benchmark, prints the
average pairwise correlation between archetype baskets (raw and
sector-neutralized) and each basket's correlation with the market, and renders
brand_archetype_correlation.png / brand_archetype_excess_correlation.png --
diverging heatmaps of the full pairwise matrix.

This is the markets counterpart to analyze.py. Like the rest of the repo it is a
pattern-*looker*, not a claim: archetype baskets are tiny, hand-picked, and
confounded by sector and shared market beta -- treat any gap as a hypothesis,
not a finding.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.brands import by_archetype, load_brands, unique_sectors
from src.stocks import get_stock_provider
from src.visualize import (
    archetype_excess_index,
    archetype_index,
    archetype_return_matrix,
    plot_archetype_excess_growth_rates,
    plot_archetype_excess_indices,
    plot_archetype_growth_rates,
    plot_archetype_indices,
    plot_correlation_heatmap,
)

STOCKS_DIR = Path(__file__).resolve().parent / "data" / "stocks"
MARKET_TICKER = "SPY"  # broad-market benchmark, not tied to any archetype/sector


def _mean_offdiag(corr: pd.DataFrame) -> float:
    n = len(corr)
    if n < 2:
        return float("nan")
    total, count = 0.0, 0
    for i in range(n):
        for j in range(n):
            if i != j and pd.notna(corr.values[i, j]):
                total += corr.values[i, j]
                count += 1
    return total / count if count else float("nan")


def _window_return(s: pd.Series) -> float | None:
    s = s.dropna()
    if len(s) < 2 or s.iloc[0] == 0:
        return None
    return (s.iloc[-1] / s.iloc[0] - 1.0) * 100.0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--range", default="10y", help="history window (e.g. 6mo, 1y, 2y, 5y, 10y, max)")
    ap.add_argument("--interval", default="1d", help="bar interval (1d, 1wk, 1mo)")
    ap.add_argument("--window", type=int, default=63,
                     help="rolling window in trading days for the growth-rate charts (default 63 ~= 1 quarter)")
    args = ap.parse_args()

    brands = load_brands()
    provider = get_stock_provider(range_=args.range, interval=args.interval)
    sectors = unique_sectors(brands)
    print(f"Withdrawing {len(brands)} tickers + {len(sectors)} sector benchmarks "
          f"live ({args.range} @ {args.interval}) ...")

    series: dict[str, pd.Series] = {}
    STOCKS_DIR.mkdir(parents=True, exist_ok=True)
    for b in brands:
        s = provider.fetch_history(b.ticker)
        series[b.ticker] = s
        if s.empty:
            print(f"  !! {b.ticker:6s} {b.name:22s} -- no data (skipped)")
            continue
        s.rename_axis("date").to_frame("adjclose").to_csv(STOCKS_DIR / f"{b.ticker}.csv")

    sector_series = provider.fetch_many(sectors)
    for t, s in sector_series.items():
        if s.empty:
            print(f"  !! {t:6s} (sector ETF)         -- no data (skipped)")
            continue
        s.rename_axis("date").to_frame("adjclose").to_csv(STOCKS_DIR / f"{t}.csv")

    market_series = provider.fetch_history(MARKET_TICKER)
    if not market_series.empty:
        market_series.rename_axis("date").to_frame("adjclose").to_csv(STOCKS_DIR / f"{MARKET_TICKER}.csv")
    market_ret = market_series.pct_change()

    # Per-brand window returns (each brand over its own available history).
    print("\nWindow return by archetype (per brand, over each brand's own history):")
    grouped = by_archetype(brands)
    arch_rows = []
    for archetype, members in grouped.items():
        for b in members:
            r = _window_return(series.get(b.ticker, pd.Series(dtype=float)))
            tag = f"{r:+8.1f}%" if r is not None else "     n/a"
            print(f"  {archetype:10s} {b.ticker:6s} {b.name:24s} {tag}")
        # Basket total return = the daily-rebalanced equal-weight index end value.
        idx = archetype_index(series, members)
        if not idx.empty:
            arch_rows.append((archetype, float(idx.iloc[-1]) - 100.0, len(idx)))

    if arch_rows:
        print("\nArchetype basket (daily-rebalanced equal-weight index), best -> worst:")
        for archetype, ret, n in sorted(arch_rows, key=lambda x: x[1], reverse=True):
            print(f"  {archetype:10s} {ret:+8.1f}%   ({n} trading days)")

    have = {t: s for t, s in series.items() if not s.empty}
    if have:
        path = plot_archetype_indices(series, brands)
        print(f"\nWrote {path}")
        growth_path = plot_archetype_growth_rates(series, brands, window=args.window)
        print(f"Wrote {growth_path}")
    else:
        print("\nNo series withdrawn -- check network egress to query1.finance.yahoo.com")

    # Sector-neutralized view: each brand's return minus its own sector ETF's.
    have_sectors = {t: s for t, s in sector_series.items() if not s.empty}
    if have and have_sectors:
        excess_rows = []
        for archetype, members in grouped.items():
            idx = archetype_excess_index(series, sector_series, members)
            if not idx.empty:
                excess_rows.append((archetype, float(idx.iloc[-1]) - 100.0, len(idx)))
        if excess_rows:
            print("\nArchetype basket, sector-neutralized (excess over own sector ETF), best -> worst:")
            for archetype, ret, n in sorted(excess_rows, key=lambda x: x[1], reverse=True):
                print(f"  {archetype:10s} {ret:+8.1f}%   ({n} trading days)")
        excess_path = plot_archetype_excess_indices(series, sector_series, brands)
        print(f"\nWrote {excess_path}")
        excess_growth_path = plot_archetype_excess_growth_rates(series, sector_series, brands, window=args.window)
        print(f"Wrote {excess_growth_path}")

    # How correlated are the 12 baskets, really -- and how much of that is just
    # shared market beta? (raw view)
    if have:
        raw_matrix = archetype_return_matrix(brands, series)
        raw_corr = raw_matrix.corr()
        avg_raw = _mean_offdiag(raw_corr)
        print(f"\nArchetype-vs-archetype correlation (raw daily returns): "
              f"avg pairwise = {avg_raw:+.2f}")
        if not market_ret.empty:
            market_corr_raw = {a: raw_matrix[a].corr(market_ret) for a in raw_matrix.columns}
            avg_market_raw = sum(market_corr_raw.values()) / len(market_corr_raw)
            print(f"Archetype-vs-{MARKET_TICKER} (market) correlation: avg = {avg_market_raw:+.2f}")
        corr_path = plot_correlation_heatmap(
            raw_corr,
            title="Archetype basket correlation matrix (raw daily returns)",
            outfile="brand_archetype_correlation.png",
        )
        print(f"Wrote {corr_path}")

    # Sector-neutralized view: does controlling for sector reduce the correlation?
    if have and have_sectors:
        excess_matrix = archetype_return_matrix(brands, series, sector_series, excess=True)
        excess_corr = excess_matrix.corr()
        avg_excess = _mean_offdiag(excess_corr)
        print(f"\nArchetype-vs-archetype correlation (sector-neutralized excess returns): "
              f"avg pairwise = {avg_excess:+.2f}")
        if not market_ret.empty:
            market_corr_excess = {a: excess_matrix[a].corr(market_ret) for a in excess_matrix.columns}
            avg_market_excess = sum(market_corr_excess.values()) / len(market_corr_excess)
            print(f"Archetype-vs-{MARKET_TICKER} (market), excess returns: avg = {avg_market_excess:+.2f}")
        excess_corr_path = plot_correlation_heatmap(
            excess_corr,
            title="Archetype basket correlation matrix (sector-neutralized excess returns)",
            outfile="brand_archetype_excess_correlation.png",
        )
        print(f"Wrote {excess_corr_path}")

    print(f"\nPer-ticker CSVs in {STOCKS_DIR}/")


if __name__ == "__main__":
    main()
