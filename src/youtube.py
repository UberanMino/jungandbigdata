"""YouTube trending video fetcher (a second collective-attention channel).

Where Google Trends measures what people consciously *search for* (a pull
signal), YouTube's "trending" chart measures what collective attention is
actually *landing on* right now (a push/consumption signal). It is a natural
second channel for the same "collective attention" idea this project probes --
and, unlike `trends.google.com`, the YouTube Data API is reachable from the
managed cloud env.

This uses the official **YouTube Data API v3** `videos.list` endpoint with
`chart=mostPopular`. Two realities shape the interface:

  * Trending is **per-region**, not global. You pass a `regionCode` (an ISO
    3166-1 alpha-2 code like ``US``, ``GB``, ``DE``). There is no single
    worldwide list; fetch several regions and tag each row with its own.
  * A single request returns at most 50 items, so `top_trending` paginates
    with ``nextPageToken`` until it has the requested N (the chart itself
    usually holds ~200 per region).

Auth is an **API key** only (public data, no OAuth). Create one in the Google
Cloud console with "YouTube Data API v3" enabled, then expose it as the
``YOUTUBE_API_KEY`` environment variable. Each call costs 1 quota unit against
the default 10,000 units/day, so this is effectively free.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import requests

API_URL = "https://www.googleapis.com/youtube/v3/videos"
MAX_PER_PAGE = 50  # hard cap imposed by the API for the mostPopular chart


class YouTubeAPIError(RuntimeError):
    """Raised when the YouTube Data API returns an error or no key is set."""


@dataclass(frozen=True)
class TrendingVideo:
    """A single trending video, flattened to the fields we care about."""

    rank: int
    region: str
    video_id: str
    title: str
    channel: str
    published_at: str
    category_id: str
    view_count: int
    like_count: int
    comment_count: int

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.video_id}"


def _api_key(explicit: str | None) -> str:
    key = explicit or os.environ.get("YOUTUBE_API_KEY")
    if not key:
        raise YouTubeAPIError(
            "No API key. Set YOUTUBE_API_KEY (Google Cloud -> enable 'YouTube "
            "Data API v3' -> create an API key) or pass api_key=..."
        )
    return key


def _to_int(value) -> int:
    # statistics fields are strings, and some (e.g. likeCount) can be absent
    # when the uploader has hidden them -- treat missing as 0.
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def top_trending(
    region: str = "US",
    n: int = 100,
    api_key: str | None = None,
    session: requests.Session | None = None,
    timeout: float = 30.0,
) -> list[TrendingVideo]:
    """Return up to ``n`` currently-trending videos for one ``region``.

    Paginates the mostPopular chart in pages of 50. Stops when it has ``n``
    videos or the chart runs out (it can hold fewer than ``n`` for a region).
    Rank is 1-based in the order the API returns them (its trending order).
    """
    key = _api_key(api_key)
    http = session or requests.Session()

    videos: list[TrendingVideo] = []
    page_token: str | None = None
    rank = 1

    while len(videos) < n:
        params = {
            "part": "snippet,statistics",
            "chart": "mostPopular",
            "regionCode": region,
            "maxResults": min(MAX_PER_PAGE, n - len(videos)),
            "key": key,
        }
        if page_token:
            params["pageToken"] = page_token

        resp = http.get(API_URL, params=params, timeout=timeout)
        if resp.status_code != 200:
            raise YouTubeAPIError(
                f"YouTube API {resp.status_code} for region {region!r}: {resp.text[:300]}"
            )
        payload = resp.json()

        for item in payload.get("items", []):
            snip = item.get("snippet", {})
            stats = item.get("statistics", {})
            videos.append(
                TrendingVideo(
                    rank=rank,
                    region=region,
                    video_id=item.get("id", ""),
                    title=snip.get("title", ""),
                    channel=snip.get("channelTitle", ""),
                    published_at=snip.get("publishedAt", ""),
                    category_id=snip.get("categoryId", ""),
                    view_count=_to_int(stats.get("viewCount")),
                    like_count=_to_int(stats.get("likeCount")),
                    comment_count=_to_int(stats.get("commentCount")),
                )
            )
            rank += 1

        page_token = payload.get("nextPageToken")
        if not page_token:
            break  # chart exhausted for this region

    return videos[:n]


def top_trending_multi(
    regions: list[str],
    n: int = 100,
    api_key: str | None = None,
    timeout: float = 30.0,
) -> list[TrendingVideo]:
    """Fetch ``top_trending`` for several regions, concatenated.

    There is no worldwide chart, so "global-ish" trending means sampling
    several major regions; each row carries its own ``region`` so you can keep
    them apart or aggregate as you like.
    """
    session = requests.Session()
    out: list[TrendingVideo] = []
    for region in regions:
        out.extend(
            top_trending(region=region, n=n, api_key=api_key, session=session, timeout=timeout)
        )
    return out


def to_frame(videos: list[TrendingVideo]):
    """Convert the video list to a tidy pandas DataFrame (imported lazily)."""
    import pandas as pd

    return pd.DataFrame(
        {
            "rank": v.rank,
            "region": v.region,
            "video_id": v.video_id,
            "title": v.title,
            "channel": v.channel,
            "published_at": v.published_at,
            "category_id": v.category_id,
            "view_count": v.view_count,
            "like_count": v.like_count,
            "comment_count": v.comment_count,
            "url": v.url,
        }
        for v in videos
    )
