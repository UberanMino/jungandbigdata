#!/usr/bin/env python3
"""Fetch '<symbol> dream meaning' queries co-normalized against the generic
'dream meaning' baseline, over 2004-present monthly. Symbol list lives in
dream_symbols.yaml. Batches of 4 symbols + baseline are pulled per Trends
request (5-term cap); each window is cached so the run is resumable, and
pulls are politely rate-limited with backoff on 429s.

Usage:
    python fetch_dream_trends.py
    python fetch_dream_trends.py --geo US
"""
from __future__ import annotations

import argparse

from src.dream_trends import DreamBatchFetcher


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--geo", default="", help="region code, e.g. US (default worldwide)")
    ap.add_argument("--pause", type=float, default=8.0)
    ap.add_argument("--backoff", type=float, default=10.0)
    ap.add_argument("--tries", type=int, default=8)
    args = ap.parse_args()

    fetcher = DreamBatchFetcher(geo=args.geo, pause=args.pause, backoff=args.backoff, tries=args.tries)
    report = fetcher.run()

    print("\n" + "=" * 60)
    print("DREAM FETCH SUMMARY")
    print("=" * 60)
    print(report.summary())


if __name__ == "__main__":
    main()
