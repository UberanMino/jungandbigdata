#!/usr/bin/env python3
"""Live Google Trends fetcher for the symbol clusters in symbols.yaml.

Pulls one co-normalized 2004-present *monthly* series per cluster (stitched from
two overlapping long windows), caches raw pulls to data/cache/, and writes each
result to data/trends_export/<key>.csv in Google-Trends export format so
`analyze.py` picks it up unchanged.

Google Trends rate-limits (429) hard from datacenter IPs, so this is politely
throttled with exponential backoff, is resumable (per-window cache), and FALLS
BACK to any manual CSV already present in data/trends_export/<key>.csv for any
cluster it cannot pull live. It reports which clusters still need a manual export
rather than failing the whole run.

Usage:
    python fetch_trends.py                     # worldwide, all clusters
    python fetch_trends.py --geo US
    python fetch_trends.py --only dragon wolf_beast
    python fetch_trends.py --pause 30 --backoff 45 --tries 6
"""
from __future__ import annotations

import argparse

from src.trends import FullHistoryFetcher


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--geo", default="", help="region code, e.g. US (default worldwide)")
    ap.add_argument("--only", nargs="*", default=None, help="restrict to these cluster keys")
    ap.add_argument("--pause", type=float, default=25.0, help="seconds between live pulls")
    ap.add_argument("--backoff", type=float, default=30.0, help="base backoff after a 429")
    ap.add_argument("--tries", type=int, default=5, help="attempts per window before giving up")
    args = ap.parse_args()

    fetcher = FullHistoryFetcher(
        geo=args.geo, pause=args.pause, backoff=args.backoff, tries=args.tries
    )
    report = fetcher.run(only=args.only)

    print("\n" + "=" * 60)
    print("FETCH SUMMARY")
    print("=" * 60)
    print(report.summary())
    if report.needs_manual:
        print(
            "\nFor the clusters above, open data/trends_export/EXPORT_LINKS.md and "
            "export them manually, then re-run `python analyze.py`."
        )


if __name__ == "__main__":
    main()
