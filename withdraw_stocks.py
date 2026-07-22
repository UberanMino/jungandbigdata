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
has out- or under-performed. It also prints a per-brand and per-archetype
window-return table.

This is the markets counterpart to analyze.py. Like the rest of the repo it is a
pattern-*looker*, not a claim: archetype baskets are tiny, hand-picked, and
confounded by sector -- treat any gap as a hypothesis, not a finding.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.brands import by_archetype, load_brands
from src.stocks import get_stock_provider
from src.visualize import archetype_index, plot_archetype_indices

STOCKS_DIR = Path(__file__).resolve().parent / "data" / "stocks"


def _window_return(s: pd.Series) -> float | None:
    s = s.dropna()
    if len(s) < 2 or s.iloc[0] == 0:
        return None
    return (s.iloc[-1] / s.iloc[0] - 1.0) * 100.0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--range", default="10y", help="history window (e.g. 6mo, 1y, 2y, 5y, 10y, max)")
    ap.add_argument("--interval", default="1d", help="bar interval (1d, 1wk, 1mo)")
    args = ap.parse_args()

    brands = load_brands()
    provider = get_stock_provider(range_=args.range, interval=args.interval)
    print(f"Withdrawing {len(brands)} tickers live ({args.range} @ {args.interval}) ...")

    series: dict[str, pd.Series] = {}
    STOCKS_DIR.mkdir(parents=True, exist_ok=True)
    for b in brands:
        s = provider.fetch_history(b.ticker)
        series[b.ticker] = s
        if s.empty:
            print(f"  !! {b.ticker:6s} {b.name:22s} -- no data (skipped)")
            continue
        s.rename_axis("date").to_frame("adjclose").to_csv(STOCKS_DIR / f"{b.ticker}.csv")

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
        print(f"Per-ticker CSVs in {STOCKS_DIR}/")
    else:
        print("\nNo series withdrawn -- check network egress to query1.finance.yahoo.com")


if __name__ == "__main__":
    main()
