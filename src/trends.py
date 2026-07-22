"""Trends data providers.

Two providers share one interface, `fetch_weekly(query, center_date, cfg)`,
returning a pandas Series indexed by week offset (int) relative to `center_date`:

  * LiveTrendsProvider  -- real Google Trends via pytrends, with on-disk caching.
  * SyntheticTrendsProvider -- reproducible fake series for offline pipeline
    testing. It can optionally *plant* a pre-event signal so we can verify the
    detector finds real lift and, with signal off, that it does not hallucinate.

Google Trends is unofficial, rate-limited, and especially flaky from proxied
cloud hosts, so live pulls are cached aggressively and the synthetic provider
lets the whole pipeline run and be validated with zero network.
"""
from __future__ import annotations

import hashlib
import time
from datetime import date, timedelta

import numpy as np
import pandas as pd

from .config import CACHE_DIR, WindowConfig


def _week_index(cfg: WindowConfig) -> np.ndarray:
    return np.arange(cfg.fetch_start_week, cfg.fetch_end_week + 1)


class SyntheticTrendsProvider:
    """Deterministic fake weekly series for offline testing.

    Every (query, center_date) pair maps to a fixed RNG seed, so runs are
    reproducible. Series look like real Trends output: 0-100, a seasonal
    component, and AR(1)-ish noise. When `plant_signal > 0`, *symbolic* terms
    (channel passed in) receive a ramp in the pre-event window for a
    deterministic subset of REAL events only -- never placebo terms, and never
    at the random placebo dates used to build the null (those are not in
    `event_dates`). That last point matters: if the planted signal leaked into
    the null dates the null would absorb it and the detector could never reach
    significance -- exactly the artifact a faithful synthetic test must avoid.
    """

    def __init__(
        self,
        plant_signal: float = 0.0,
        planted_fraction: float = 0.6,
        event_dates: set | None = None,
    ):
        self.plant_signal = plant_signal
        self.planted_fraction = planted_fraction
        self.event_dates = set(event_dates or set())

    def _seed(self, query: str, center_date: date) -> int:
        h = hashlib.sha256(f"{query}|{center_date.isoformat()}".encode()).hexdigest()
        return int(h[:8], 16)

    def fetch_weekly(
        self, query: str, center_date: date, cfg: WindowConfig, channel: str = "symbolic"
    ) -> pd.Series:
        weeks = _week_index(cfg)
        rng = np.random.default_rng(self._seed(query, center_date))

        base = 30.0
        seasonal = 6.0 * np.sin(2 * np.pi * weeks / 52.0 + rng.uniform(0, 2 * np.pi))
        noise = np.zeros(len(weeks))
        noise[0] = rng.normal(0, 5)
        for i in range(1, len(weeks)):  # AR(1) so it wanders like real search data
            noise[i] = 0.6 * noise[i - 1] + rng.normal(0, 5)

        values = base + seasonal + noise

        planted = False
        if self.plant_signal > 0 and channel == "symbolic" and center_date in self.event_dates:
            # Deterministically plant on a subset of REAL events for this query.
            planted = (self._seed(query, center_date) % 100) / 100.0 < self.planted_fraction
            if planted:
                pre = (weeks >= cfg.pre_start_week) & (weeks <= cfg.pre_end_week)
                ramp = np.linspace(0, self.plant_signal, pre.sum())
                values[pre] += ramp

        values = np.clip(values, 0, 100)
        s = pd.Series(values, index=weeks, name=query)
        s.attrs["planted"] = planted
        return s


class LiveTrendsProvider:
    """Real Google Trends via pytrends, cached per (query, center window)."""

    def __init__(self, geo: str = "", hl: str = "en-US", pause: float = 1.5, retries: int = 3):
        self.geo = geo
        self.hl = hl
        self.pause = pause
        self.retries = retries
        self._pytrends = None

    def _client(self):
        if self._pytrends is None:
            from pytrends.request import TrendReq  # imported lazily

            self._pytrends = TrendReq(hl=self.hl, tz=0)
        return self._pytrends

    def _cache_path(self, query: str, start: date, end: date):
        key = f"{query}|{start}|{end}|{self.geo}"
        digest = hashlib.sha256(key.encode()).hexdigest()[:16]
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        return CACHE_DIR / f"{digest}.csv"

    def fetch_weekly(
        self, query: str, center_date: date, cfg: WindowConfig, channel: str = "symbolic"
    ) -> pd.Series:
        start = center_date + timedelta(weeks=int(cfg.fetch_start_week))
        end = center_date + timedelta(weeks=int(cfg.fetch_end_week))
        cache = self._cache_path(query, start, end)

        if cache.exists():
            raw = pd.read_csv(cache, parse_dates=["date"]).set_index("date")[query]
        else:
            raw = self._download(query, start, end)
            raw.rename_axis("date").to_frame(query).reset_index().to_csv(cache, index=False)

        # Map calendar weeks to integer offsets relative to the event week.
        offsets = ((raw.index - pd.Timestamp(center_date)).days // 7).astype(int)
        s = pd.Series(raw.values, index=offsets, name=query)
        s = s[~s.index.duplicated(keep="first")]
        return s.reindex(_week_index(cfg))

    def _download(self, query: str, start: date, end: date) -> pd.Series:
        client = self._client()
        timeframe = f"{start.isoformat()} {end.isoformat()}"
        last_err = None
        for attempt in range(self.retries):
            try:
                client.build_payload([query], timeframe=timeframe, geo=self.geo)
                df = client.interest_over_time()
                time.sleep(self.pause)
                if df.empty:
                    return pd.Series(dtype=float, name=query)
                return df[query].astype(float)
            except Exception as exc:  # pytrends raises a grab-bag of errors
                last_err = exc
                time.sleep(self.pause * (2 ** attempt))
        raise RuntimeError(f"Google Trends fetch failed for {query!r}: {last_err}")


def get_provider(mode: str, plant_signal: float = 0.0, geo: str = ""):
    if mode == "synthetic":
        return SyntheticTrendsProvider(plant_signal=plant_signal)
    if mode == "live":
        return LiveTrendsProvider(geo=geo)
    raise ValueError(f"unknown provider mode: {mode!r}")


# ---------------------------------------------------------------------------
# Full-history cluster fetcher (feeds the visualization pipeline)
#
# The scan pipeline above fetches short per-event windows. The pattern-hunt
# visuals in analyze.py instead want ONE long, co-normalized 0-100 monthly
# series per cluster spanning 2004-present -- the same thing a manual Google
# Trends "all" export gives you. Two wrinkles make a naive single pull useless:
#
#   1. A single 2004-present pull degrades to *yearly* granularity (~23 points),
#      far too coarse to see a rise in the months before an event.
#   2. pytrends 429s hard from datacenter IPs.
#
# So we pull two overlapping ~11.5-year windows (which Google still returns at
# monthly resolution), chain-rescale the later window onto the earlier one using
# their 6-month overlap, and renormalize the stitched series back to 0-100. Each
# raw window pull is cached to data/cache/ so a mid-run rate-limit never discards
# progress, and any cluster we cannot pull live falls back to a manual CSV export
# already sitting in data/trends_export/<key>.csv.
# ---------------------------------------------------------------------------

import random
from dataclasses import dataclass, field
from pathlib import Path

from .symbols import EXPORT_DIR, Cluster, load_clusters

# A real browser UA materially reduces Google's 429 rate from datacenter hosts.
BROWSER_UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

# (start, end) window edges. end=None means "today". The 6-month overlap in the
# first half of 2015 is the anchor used to stitch the two windows onto one scale.
FULL_HISTORY_WINDOWS: list[tuple[str, str | None]] = [
    ("2004-01-01", "2015-06-30"),
    ("2015-01-01", None),
]


def _resolve_windows() -> list[tuple[str, str]]:
    today = date.today().isoformat()
    return [(s, e or today) for s, e in FULL_HISTORY_WINDOWS]


def _to_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse a raw Trends frame to a clean month-start-indexed frame.

    Windows in FULL_HISTORY_WINDOWS come back monthly already, but resampling to
    month-start makes the overlap indices line up exactly for stitching (and
    tolerates a window that Google happens to return at weekly resolution).
    """
    out = df.copy()
    out.index = pd.to_datetime(out.index)
    out = out[[c for c in out.columns if c.lower() != "ispartial"]]
    return out.resample("MS").mean()


def _rescale_factor(ref: pd.Series, nxt: pd.Series) -> float:
    """Least-squares factor f minimizing ||ref - f*nxt|| on the shared index."""
    overlap = ref.index.intersection(nxt.index)
    if len(overlap) == 0:
        return 1.0
    a, b = ref.loc[overlap].to_numpy(float), nxt.loc[overlap].to_numpy(float)
    denom = float((b * b).sum())
    if denom > 0:
        return float((a * b).sum()) / denom
    # Degenerate overlap (later window ~0 there): fall back to a mean ratio.
    return float(a.mean() / b.mean()) if b.mean() > 0 else 1.0


def _stitch(windows: list[pd.DataFrame]) -> pd.DataFrame:
    """Chain-rescale later windows onto the first and renormalize to 0-100.

    All columns of a window share one factor, so within-window relationships
    (e.g. the sun/moon ratio) are preserved exactly across the seam.
    """
    ref = _to_monthly(windows[0])
    for raw in windows[1:]:
        nxt = _to_monthly(raw)
        # Use combined column magnitude so multi-term pairs stitch on total level.
        f = _rescale_factor(ref.sum(axis=1), nxt.sum(axis=1))
        nxt = nxt * f
        new_idx = nxt.index.difference(ref.index)
        ref = pd.concat([ref, nxt.loc[new_idx]]).sort_index()
    peak = float(ref.to_numpy(float).max())
    if peak > 0:
        ref = ref / peak * 100.0
    return ref


def _write_export(path: Path, df: pd.DataFrame, region: str = "Worldwide") -> None:
    """Write a stitched frame in Google-Trends 'Interest over time' CSV format.

    trends_import.read_export skips any preamble before the Month header row, so
    the provenance comment is safely ignored by the importer.
    """
    header = "Month," + ",".join(f"{c}: ({region})" for c in df.columns)
    lines = [
        "# source: live pytrends, stitched 2004-present monthly (src/trends.py)",
        "Category: All categories",
        "",
        header,
    ]
    for ts, row in df.iterrows():
        cells = ",".join("" if pd.isna(v) else str(int(round(float(v)))) for v in row)
        lines.append(f"{ts.strftime('%Y-%m')},{cells}")
    path.write_text("\n".join(lines) + "\n")


@dataclass
class FetchReport:
    live: list[str] = field(default_factory=list)          # pulled fresh from Trends
    manual_fallback: list[str] = field(default_factory=list)  # live failed, used existing CSV
    needs_manual: list[str] = field(default_factory=list)   # live failed, no CSV present

    def summary(self) -> str:
        def line(label, keys):
            return f"{label} ({len(keys)}): " + (", ".join(keys) if keys else "-")
        return "\n".join([
            line("live-fetched", self.live),
            line("manual fallback used", self.manual_fallback),
            line("STILL NEEDS MANUAL EXPORT", self.needs_manual),
        ])


class FullHistoryFetcher:
    """Pull one co-normalized 2004-present monthly series per cluster.

    Politely rate-limited with exponential backoff on 429s. Per-window caching
    (data/cache/) makes runs resumable; per-cluster manual-CSV fallback keeps a
    throttled run from failing wholesale.
    """

    def __init__(
        self,
        geo: str = "",
        hl: str = "en-US",
        pause: float = 8.0,       # polite gap between successful live pulls
        backoff: float = 10.0,    # base wait after a rate-limit; grows gently, capped
        backoff_cap: float = 75.0,
        tries: int = 8,
        export_dir: Path = EXPORT_DIR,
    ):
        self.geo = geo
        self.hl = hl
        self.pause = pause
        self.backoff = backoff
        self.backoff_cap = backoff_cap
        self.tries = tries
        self.export_dir = export_dir
        self.windows = _resolve_windows()

    def _cache_path(self, key: str, wi: int) -> Path:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        return CACHE_DIR / f"{key}__w{wi}_{self.geo or 'worldwide'}.csv"

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
            except Exception as exc:  # pytrends raises a grab-bag; 429 is the common one
                last = exc
                # 429s here are transient, not bans -- a short retry usually clears
                # them, so grow gently and cap so a flaky pull costs seconds not
                # minutes. (Empirically a long exponential wait was pure dead time.)
                wait = min(self.backoff * (1.6 ** attempt), self.backoff_cap) + random.uniform(0, 4)
                print(f"    [{terms}] {start}..{end} attempt {attempt+1}/{self.tries} "
                      f"failed ({type(exc).__name__}); backing off {wait:.0f}s", flush=True)
                time.sleep(wait)
        raise RuntimeError(f"all {self.tries} attempts failed: {last}")

    def _fetch_cluster(self, cluster: Cluster) -> pd.DataFrame | None:
        raws: list[pd.DataFrame] = []
        for wi, (start, end) in enumerate(self.windows):
            cache = self._cache_path(cluster.key, wi)
            if cache.exists():
                raw = pd.read_csv(cache, parse_dates=["date"]).set_index("date")
                print(f"    [{cluster.key}] window {wi} from cache ({len(raw)} rows)", flush=True)
            else:
                time.sleep(self.pause + random.uniform(0, 5))  # rate-limit before a live hit
                raw = self._pull_window(cluster.queries, start, end)
                if raw.empty:
                    return None
                raw.rename_axis("date").to_csv(cache)
                print(f"    [{cluster.key}] window {wi} pulled live ({len(raw)} rows)", flush=True)
            raws.append(raw)
        return _stitch(raws)

    def run(self, only: list[str] | None = None, clusters: list[Cluster] | None = None) -> FetchReport:
        """`clusters` overrides the default symbols.yaml cluster list -- lets
        other pipelines (e.g. src/dream_trends.py) reuse this fetcher's
        windowing/stitching/backoff/caching for their own query sets."""
        report = FetchReport()
        self.export_dir.mkdir(parents=True, exist_ok=True)
        pool = clusters if clusters is not None else load_clusters()
        clusters = [c for c in pool if only is None or c.key in only]
        for cluster in clusters:
            print(f"[{cluster.key}] {cluster.label} :: {cluster.queries}", flush=True)
            export_csv = self.export_dir / f"{cluster.key}.csv"
            try:
                stitched = self._fetch_cluster(cluster)
            except Exception as exc:
                print(f"    -> live fetch failed: {exc}", flush=True)
                stitched = None
            if stitched is not None and not stitched.empty:
                # Name columns after the actual queries so the importer/legend read right.
                stitched.columns = list(cluster.queries)
                _write_export(export_csv, stitched)
                report.live.append(cluster.key)
                print(f"    -> wrote {export_csv} ({len(stitched)} months)", flush=True)
            elif export_csv.exists():
                report.manual_fallback.append(cluster.key)
                print(f"    -> using existing manual export {export_csv}", flush=True)
            else:
                report.needs_manual.append(cluster.key)
                print(f"    -> NO data; needs manual export -> {export_csv}", flush=True)
        return report
