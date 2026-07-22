"""Fetch the YouTube "trending" (mostPopular) chart via the YouTube Data API v3.

Needs a real API key (YouTube Data API v3 enabled) in the `YOUTUBE_API_KEY`
env var or passed explicitly. Get one from
https://console.cloud.google.com/apis/credentials.

The API caps each page at 50 items, so getting the top 100 takes two pages.
Trending is region-scoped (there is no single global chart), hence the
`region_code` parameter -- ISO 3166-1 alpha-2, e.g. "US", "GB", "IN".
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import requests

API_URL = "https://www.googleapis.com/youtube/v3/videos"
MAX_PAGE_SIZE = 50


class YouTubeAPIError(RuntimeError):
    pass


@dataclass(frozen=True)
class TrendingVideo:
    rank: int
    video_id: str
    title: str
    channel_title: str
    published_at: str
    category_id: str
    view_count: int | None
    like_count: int | None
    comment_count: int | None
    duration: str
    tags: list[str] = field(default_factory=list)

    def to_row(self) -> dict:
        return {
            "rank": self.rank,
            "video_id": self.video_id,
            "title": self.title,
            "channel_title": self.channel_title,
            "published_at": self.published_at,
            "category_id": self.category_id,
            "view_count": self.view_count,
            "like_count": self.like_count,
            "comment_count": self.comment_count,
            "duration": self.duration,
            "tags": ";".join(self.tags),
            "url": f"https://www.youtube.com/watch?v={self.video_id}",
        }


def _get_page(api_key: str, region_code: str, page_token: str | None) -> dict:
    params = {
        "part": "snippet,statistics,contentDetails",
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": MAX_PAGE_SIZE,
        "key": api_key,
    }
    if page_token:
        params["pageToken"] = page_token

    resp = requests.get(API_URL, params=params, timeout=30)
    if not resp.ok:
        detail = resp.json().get("error", {}).get("message", resp.text)
        raise YouTubeAPIError(f"YouTube API request failed ({resp.status_code}): {detail}")
    return resp.json()


def fetch_trending(
    region_code: str = "US",
    max_results: int = 100,
    api_key: str | None = None,
) -> list[TrendingVideo]:
    """Return up to `max_results` trending videos for `region_code`, ranked."""
    key = api_key or os.environ.get("YOUTUBE_API_KEY")
    if not key or key.strip().lower() in {"", "your_key_here"}:
        raise YouTubeAPIError(
            "No valid YOUTUBE_API_KEY set. Create one at "
            "https://console.cloud.google.com/apis/credentials (enable the "
            "'YouTube Data API v3') and export it as YOUTUBE_API_KEY."
        )

    videos: list[TrendingVideo] = []
    page_token = None
    while len(videos) < max_results:
        page = _get_page(key, region_code, page_token)
        for item in page.get("items", []):
            if len(videos) >= max_results:
                break
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            content = item.get("contentDetails", {})
            videos.append(
                TrendingVideo(
                    rank=len(videos) + 1,
                    video_id=item["id"],
                    title=snippet.get("title", ""),
                    channel_title=snippet.get("channelTitle", ""),
                    published_at=snippet.get("publishedAt", ""),
                    category_id=snippet.get("categoryId", ""),
                    view_count=_to_int(stats.get("viewCount")),
                    like_count=_to_int(stats.get("likeCount")),
                    comment_count=_to_int(stats.get("commentCount")),
                    duration=content.get("duration", ""),
                    tags=snippet.get("tags", []),
                )
            )
        page_token = page.get("nextPageToken")
        if not page_token:
            break

    return videos


def _to_int(value) -> int | None:
    return int(value) if value is not None else None
