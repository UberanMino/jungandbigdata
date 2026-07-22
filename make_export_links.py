#!/usr/bin/env python3
"""Generate click-ready Google Trends export links for every symbol cluster.

Writes data/trends_export/EXPORT_LINKS.md. For each cluster: open the link,
click the download (arrow) icon on the 'Interest over time' panel, and save the
CSV into data/trends_export/ as <key>.csv  (the filename column tells you which).

Usage:
    python make_export_links.py                 # worldwide, 2004-present
    python make_export_links.py --geo US --date all
"""
import argparse

from src.symbols import EXPORT_DIR, explore_url, load_clusters


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--geo", default="", help="region code, e.g. US (default worldwide)")
    ap.add_argument("--date", default="all", help="'all' (2004-now) or 'today 5-y', etc.")
    args = ap.parse_args()

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Google Trends export links",
        "",
        f"Geo: `{args.geo or 'worldwide'}`  ·  Date range: `{args.date}`",
        "",
        "For each row: open the link → on the **Interest over time** card click the",
        "download (↓) icon → save the CSV into this folder as the **Save as** name.",
        "",
        "| Cluster | Query | Save as | Link |",
        "|---|---|---|---|",
    ]
    for c in load_clusters():
        url = explore_url(c, date=args.date, geo=args.geo)
        q = " , ".join(c.queries)
        lines.append(f"| {c.label} | `{q}` | `{c.key}.csv` | [open]({url}) |")

    out = EXPORT_DIR / "EXPORT_LINKS.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"Wrote {out}")
    print("\nOpen these and drop the CSVs next to EXPORT_LINKS.md:\n")
    for c in load_clusters():
        print(f"  {c.key + '.csv':22s} {explore_url(c, date=args.date, geo=args.geo)}")


if __name__ == "__main__":
    main()
