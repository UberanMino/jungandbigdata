"""Live stock-price provider.

Withdraws daily price history straight from the public Yahoo Finance chart
endpoint -- no API key, no third-party library, just `requests` (which the repo
already depends on). This is the markets analogue of src/trends.py: one method,
`fetch_history(ticker, ...)`, returning a pandas Series of adjusted close indexed
by date, with aggressive on-disk caching.

Why Yahoo's raw endpoint and not `yfinance`/`pytrends`-style wrappers:
  * It works from this proxied cloud host (the Trends host does not).
  * Adjusted close bakes in splits/dividends, so cross-brand comparison is fair.
  * Caching is keyed to the calendar day, so a same-day re-run is instant while
    the next day's run refreshes -- prices are live, but we don't hammer Yahoo.

Failures are non-fatal: a bad or delisted ticker yields an empty Series so a
whole withdrawal isn't lost to one symbol.
"""
from __future__ import annotations

import hashlib
from datetime import date

import pandas as pd
import requests

from .config import CACHE_DIR

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
STOCK_CACHE_DIR = CACHE_DIR / "stocks"
# A browser-ish UA; the endpoint 401s bare programmatic clients.
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; jung-and-big-data/1.0)"}


class LiveStockProvider:
    """Adjusted daily closes from Yahoo Finance, cached per (ticker, range, day)."""

    def __init__(self, range_: str = "2y", interval: str = "1d", timeout: float = 20.0):
        self.range = range_
        self.interval = interval
        self.timeout = timeout

    def _cache_path(self, ticker: str) -> "pd.io.common.Path":
        # Include today's date so the cache self-expires daily.
        key = f"{ticker}|{self.range}|{self.interval}|{date.today().isoformat()}"
        digest = hashlib.sha256(key.encode()).hexdigest()[:16]
        STOCK_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        return STOCK_CACHE_DIR / f"{digest}.csv"

    def fetch_history(self, ticker: str) -> pd.Series:
        """Adjusted-close Series indexed by date; empty Series on any failure."""
        cache = self._cache_path(ticker)
        if cache.exists():
            raw = pd.read_csv(cache, parse_dates=["date"]).set_index("date")["adjclose"]
            return raw.rename(ticker)

        try:
            s = self._download(ticker)
        except Exception:  # network / parse / bad symbol -- never fatal
            return pd.Series(dtype=float, name=ticker)

        s.rename_axis("date").to_frame("adjclose").reset_index().to_csv(cache, index=False)
        return s

    def fetch_many(self, tickers: list[str]) -> dict[str, pd.Series]:
        return {t: self.fetch_history(t) for t in tickers}

    def _download(self, ticker: str) -> pd.Series:
        resp = requests.get(
            CHART_URL.format(ticker=ticker),
            params={"range": self.range, "interval": self.interval},
            headers=_HEADERS,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        result = resp.json()["chart"]["result"]
        if not result:
            return pd.Series(dtype=float, name=ticker)
        r = result[0]
        ts = r.get("timestamp")
        if not ts:
            return pd.Series(dtype=float, name=ticker)

        # Prefer adjusted close (splits/dividends folded in); fall back to close.
        adj = r["indicators"].get("adjclose", [{}])[0].get("adjclose")
        close = r["indicators"]["quote"][0].get("close")
        values = adj if adj is not None else close

        idx = pd.to_datetime(ts, unit="s").normalize()
        s = pd.Series(values, index=idx, name=ticker, dtype="float64")
        s = s[~s.index.duplicated(keep="last")].dropna()
        return s


def get_stock_provider(range_: str = "2y", interval: str = "1d") -> LiveStockProvider:
    return LiveStockProvider(range_=range_, interval=interval)
