"""Dream-symbol Trends fetcher + ratio analysis.

Each "<symbol> dream meaning" query is pulled TOGETHER with the generic "dream
meaning" baseline (Trends caps comparisons at 5 terms, so symbols batch 4-at-a-
time with the baseline riding along in every batch). Within a batch all terms
share one 0-100 scale, so symbol/baseline is a valid ratio; because the same
baseline anchors every batch, that ratio is also comparable *across* batches --
exactly the trick already used for the sun/moon pair in src/trends.py.

Reuses src/trends.py's long-window stitching (a single 2004-present pull comes
back at yearly resolution; two overlapping ~11.5yr pulls come back monthly) and
its polite-backoff live fetch.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from .config import CACHE_DIR, ROOT
from .trends import BROWSER_UA, _resolve_windows, _stitch

DREAM_FILE = ROOT / "dream_symbols.yaml"
DREAM_EXPORT_DIR = ROOT / "data" / "trends_export" / "dreams"
BATCH_SIZE = 4  # + baseline = 5 terms per Trends request (Google's cap)


@dataclass(frozen=True)
class DreamSymbol:
    key: str
    label: str
    query: str


def load_dream_symbols() -> tuple[str, list[DreamSymbol]]:
    data = yaml.safe_load(DREAM_FILE.read_text())
    baseline = data["baseline"]
    symbols = [
        DreamSymbol(key=k, label=s["label"], query=s["query"])
        for k, s in data["symbols"].items()
    ]
    return baseline, symbols


def _batches(symbols: list[DreamSymbol], size: int = BATCH_SIZE) -> list[list[DreamSymbol]]:
    return [symbols[i : i + size] for i in range(0, len(symbols), size)]


def _write_dream_export(path: Path, df: pd.DataFrame, region: str = "Worldwide") -> None:
    header = "Month," + ",".join(f"{c}: ({region})" for c in df.columns)
    lines = [
        "# source: live pytrends, stitched 2004-present monthly (src/dream_trends.py)",
        "Category: All categories",
        "",
        header,
    ]
    for ts, row in df.iterrows():
        cells = ",".join("" if pd.isna(v) else str(int(round(float(v)))) for v in row)
        lines.append(f"{ts.strftime('%Y-%m')},{cells}")
    path.write_text("\n".join(lines) + "\n")


@dataclass
class DreamFetchReport:
    live: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"live-fetched batches ({len(self.live)}): {', '.join(self.live) or '-'}\n"
            f"failed batches ({len(self.failed)}): {', '.join(self.failed) or '-'}"
        )


class DreamBatchFetcher:
    """Politely rate-limited, resumable (per-window cache) batch fetcher."""

    def __init__(
        self,
        geo: str = "",
        hl: str = "en-US",
        pause: float = 8.0,
        backoff: float = 10.0,
        backoff_cap: float = 75.0,
        tries: int = 8,
    ):
        self.geo, self.hl = geo, hl
        self.pause, self.backoff, self.backoff_cap, self.tries = pause, backoff, backoff_cap, tries
        self.windows = _resolve_windows()

    def _cache_path(self, batch_key: str, wi: int) -> Path:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        return CACHE_DIR / f"dreams_{batch_key}__w{wi}_{self.geo or 'worldwide'}.csv"

    def _pull_window(self, terms: list[str], start: str, end: str) -> pd.DataFrame:
        from pytrends.request import TrendReq

        timeframe = f"{start} {end}"
        last = None
        for attempt in range(self.tries):
            try:
                client = TrendReq(hl=self.hl, tz=0, requests_args={"headers": BROWSER_UA})
                client.build_payload(terms, timeframe=timeframe, geo=self.geo)
                df = client.interest_over_time()
                if df is None or df.empty:
                    return pd.DataFrame()
                return df
            except Exception as exc:  # pytrends grab-bag; 429 is the common one
                last = exc
                wait = min(self.backoff * (1.6**attempt), self.backoff_cap) + 3.0
                print(
                    f"    [{terms}] {start}..{end} attempt {attempt + 1}/{self.tries} "
                    f"failed ({type(exc).__name__}); backing off {wait:.0f}s",
                    flush=True,
                )
                time.sleep(wait)
        raise RuntimeError(f"all {self.tries} attempts failed: {last}")

    def _fetch_batch(self, batch_key: str, terms: list[str]) -> pd.DataFrame | None:
        raws: list[pd.DataFrame] = []
        for wi, (start, end) in enumerate(self.windows):
            cache = self._cache_path(batch_key, wi)
            if cache.exists():
                raw = pd.read_csv(cache, parse_dates=["date"]).set_index("date")
                print(f"    [{batch_key}] window {wi} from cache ({len(raw)} rows)", flush=True)
            else:
                time.sleep(self.pause)
                raw = self._pull_window(terms, start, end)
                if raw.empty:
                    return None
                raw.rename_axis("date").to_csv(cache)
                print(f"    [{batch_key}] window {wi} pulled live ({len(raw)} rows)", flush=True)
            raws.append(raw)
        return _stitch(raws)

    def run(self) -> DreamFetchReport:
        baseline, symbols = load_dream_symbols()
        DREAM_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        report = DreamFetchReport()
        for bi, batch in enumerate(_batches(symbols)):
            terms = [baseline] + [s.query for s in batch]
            batch_key = f"batch{bi}"
            print(f"[{batch_key}] {terms}", flush=True)
            try:
                stitched = self._fetch_batch(batch_key, terms)
            except Exception as exc:
                print(f"    -> failed: {exc}", flush=True)
                stitched = None
            if stitched is not None and not stitched.empty:
                stitched.columns = terms
                out = DREAM_EXPORT_DIR / f"{batch_key}.csv"
                _write_dream_export(out, stitched)
                report.live.append(batch_key)
                print(f"    -> wrote {out} ({len(stitched)} months)", flush=True)
            else:
                report.failed.append(batch_key)
                print(f"    -> FAILED, no data for batch {batch_key}", flush=True)
        return report


# ---------------------------------------------------------------------------
# Ratio analysis (reads what DreamBatchFetcher wrote)
# ---------------------------------------------------------------------------


def load_ratio_frame() -> pd.DataFrame:
    """symbol_key -> (symbol query / baseline query) monthly ratio, one df."""
    from .trends_import import read_export

    baseline, symbols = load_dream_symbols()
    series = {}
    for bi, batch in enumerate(_batches(symbols)):
        path = DREAM_EXPORT_DIR / f"batch{bi}.csv"
        if not path.exists():
            continue
        df = read_export(path)
        if baseline not in df.columns:
            continue
        base = df[baseline].astype(float).replace(0, np.nan)
        for s in batch:
            if s.query in df.columns:
                series[s.key] = df[s.query].astype(float) / base
    out = pd.DataFrame(series).sort_index()
    out.index.name = "date"
    return out


def robust_z(s: pd.Series) -> pd.Series:
    """Deviation from the series' own typical level, in MAD-based robust sigma."""
    med = s.median()
    mad = (s - med).abs().median()
    sigma = mad * 1.4826
    if not sigma or pd.isna(sigma) or sigma == 0:
        sigma = s.std()
    if not sigma or pd.isna(sigma) or sigma == 0:
        return s * 0.0
    return (s - med) / sigma
