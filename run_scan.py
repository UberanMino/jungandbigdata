#!/usr/bin/env python3
"""CLI entry point for the broad exploratory scan.

Examples
--------
Offline pipeline check (no network), with a planted signal so you can see the
detector separate symbolic terms from placebo terms:

    python run_scan.py --mode synthetic --plant-signal 8

Offline false-positive check (no planted signal): symbolic terms should look no
different from placebo.

    python run_scan.py --mode synthetic --plant-signal 0

Real data (unofficial Google Trends; slow and rate-limited -- results cache to
data/cache/):

    python run_scan.py --mode live --geo ""     # worldwide
"""
import argparse

from src.scan import run_scan, save_results


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["synthetic", "live"], default="synthetic")
    ap.add_argument("--plant-signal", type=float, default=0.0,
                    help="synthetic mode only: strength of planted pre-event bump")
    ap.add_argument("--geo", default="", help="live mode geo code, e.g. US (default worldwide)")
    ap.add_argument("--no-nulls", action="store_true", help="skip null model + FDR (faster)")
    args = ap.parse_args()

    df = run_scan(
        mode=args.mode,
        plant_signal=args.plant_signal,
        geo=args.geo,
        run_nulls=not args.no_nulls,
    )
    save_results(df)

    print("\n=== Top terms by mean pre-event lift ===")
    cols = ["query", "channel", "group", "n_events", "mean_lift", "p_empirical", "q_value", "fdr_significant"]
    print(df[cols].head(15).to_string(index=False))

    print("\n=== Mean lift by channel (symbolic should beat placebo to be interesting) ===")
    print(df.groupby("channel")["mean_lift"].agg(["mean", "count"]).to_string())

    sig = df[df["fdr_significant"]]
    print(f"\nFDR-significant terms: {len(sig)}")
    if len(sig):
        print(sig[["query", "channel", "mean_lift", "q_value"]].to_string(index=False))
    print("\nResults written to results/ . Treat survivors as HYPOTHESES for focused follow-up, not findings.")


if __name__ == "__main__":
    main()
