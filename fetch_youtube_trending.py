#!/usr/bin/env python3
"""Fetch the top N trending YouTube videos for a region and save a dated CSV.

Requires a YouTube Data API v3 key (YOUTUBE_API_KEY env var, or --api-key).
Get one at https://console.cloud.google.com/apis/credentials.

Usage:
    python fetch_youtube_trending.py                  # top 100, region US, today's date
    python fetch_youtube_trending.py --region GB --top 50
"""
import argparse
import csv
import sys
from datetime import date, timezone, datetime
from pathlib import Path

from src.youtube_trending import YouTubeAPIError, fetch_trending

OUT_DIR = Path(__file__).resolve().parent / "data" / "youtube_trending"

FIELDS = [
    "rank", "video_id", "title", "channel_title", "published_at",
    "category_id", "view_count", "like_count", "comment_count",
    "duration", "tags", "url",
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", default="US", help="ISO 3166-1 alpha-2 region code (default US)")
    ap.add_argument("--top", type=int, default=100, help="how many videos to fetch (default 100)")
    ap.add_argument("--api-key", default=None, help="overrides YOUTUBE_API_KEY env var")
    ap.add_argument("--out", default=None, help="output CSV path (default data/youtube_trending/<region>_<date>.csv)")
    args = ap.parse_args()

    try:
        videos = fetch_trending(region_code=args.region, max_results=args.top, api_key=args.api_key)
    except YouTubeAPIError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    today = datetime.now(timezone.utc).date().isoformat()
    out_path = Path(args.out) if args.out else OUT_DIR / f"{args.region.lower()}_{today}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for v in videos:
            writer.writerow(v.to_row())

    print(f"Wrote {len(videos)} trending videos ({args.region}, {today}) -> {out_path}")


if __name__ == "__main__":
    main()
