#!/usr/bin/env python3
"""CLI: fetch YouTube's trending chart to a dated CSV.

YouTube trending is a second collective-attention channel to sit alongside the
Google Trends work: what attention is *landing on*, not just what people search
for. Unlike trends.google.com, the YouTube Data API is reachable from the cloud
env -- it just needs an API key.

Setup (once): Google Cloud console -> enable "YouTube Data API v3" -> create an
API key, then:

    export YOUTUBE_API_KEY=your_key_here

Examples
--------
Top 100 US trending videos to data/youtube/trending_US_<date>.csv:

    python fetch_youtube.py --region US --n 100

A "global-ish" pull across several major regions (each row tagged by region;
there is no single worldwide chart):

    python fetch_youtube.py --region US,GB,DE,JP,IN,BR --n 50
"""
import argparse
from datetime import date
from pathlib import Path

from src.youtube import YouTubeAPIError, top_trending_multi, to_frame

OUT_DIR = Path(__file__).resolve().parent / "data" / "youtube"


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--region",
        default="US",
        help="ISO 3166-1 alpha-2 region code, or a comma-separated list "
        "(e.g. US or US,GB,DE). Default: US",
    )
    ap.add_argument("--n", type=int, default=100, help="videos per region (default 100)")
    ap.add_argument(
        "--out",
        default=None,
        help="output CSV path (default: data/youtube/trending_<regions>_<date>.csv)",
    )
    args = ap.parse_args()

    regions = [r.strip().upper() for r in args.region.split(",") if r.strip()]

    try:
        videos = top_trending_multi(regions, n=args.n)
    except YouTubeAPIError as exc:
        raise SystemExit(f"error: {exc}")

    df = to_frame(videos)

    if args.out:
        out_path = Path(args.out)
    else:
        tag = "-".join(regions)
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUT_DIR / f"trending_{tag}_{date.today().isoformat()}.csv"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

    print(f"Fetched {len(df)} trending videos across {len(regions)} region(s): {', '.join(regions)}")
    print(f"Written to {out_path}")
    if len(df):
        preview = df[df["region"] == regions[0]].head(10)
        print(f"\n=== Top 10 trending in {regions[0]} ===")
        for _, row in preview.iterrows():
            print(f"{row['rank']:>3}. {row['title'][:70]:<70}  ({row['view_count']:,} views)  [{row['channel']}]")


if __name__ == "__main__":
    main()
