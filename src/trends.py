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
