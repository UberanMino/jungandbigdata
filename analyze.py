#!/usr/bin/env python3
"""Import whatever Trends CSVs are in data/trends_export/ and make the visuals.

    python analyze.py

Produces results/symbols_overview.png (small multiples with event markers) and,
if sun_moon.csv is present, results/sun_moon_ratio.png. Prints which clusters
still need exporting.
"""
from src.symbols import load_clusters
from src.trends_import import load_available, missing_exports
from src.visualize import plot_small_multiples, plot_sun_moon_ratio


def main() -> None:
    series = load_available()
    total = len(load_clusters())
    print(f"Loaded {len(series)}/{total} clusters from data/trends_export/")

    if not series:
        print("\nNo exports found yet. Run `python make_export_links.py`, download the")
        print("CSVs into data/trends_export/, then re-run this.")
        for c in missing_exports():
            print(f"  needed: {c.key}.csv  ({c.label})")
        return

    p1 = plot_small_multiples(series)
    print(f"Wrote {p1}")

    if "sun_moon" in series:
        p2 = plot_sun_moon_ratio(series["sun_moon"])
        if p2:
            print(f"Wrote {p2}")

    missing = missing_exports()
    if missing:
        print(f"\nStill missing {len(missing)} exports:")
        for c in missing:
            print(f"  {c.key}.csv  ({c.label})")


if __name__ == "__main__":
    main()
