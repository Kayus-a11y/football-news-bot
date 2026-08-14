"""
news_fetcher.py — Fetches the latest, not-already-posted football/soccer
headline from NewsAPI.

Keeps a small local JSON file of recently posted article URLs so the same
headline isn't posted repeatedly when NewsAPI's "latest" result hasn't
changed since the last check. The file lives next to this module so it
survives bot restarts (but resets on a fresh Railway redeploy, since the
container filesystem is rebuilt then -- that's fine, it just means it
starts tracking fresh after a deploy).
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional, TypedDict

import aiohttp

import config

logger = logging.getLogger(__name__)

# How many recent article URLs to remember, and how many candidate
# articles to pull from NewsAPI per check (must be >= dedup pool to have
# a chance of finding something new).
MAX_TRACKED_URLS = 50
FETCH_POOL_SIZE = 15

_TRACKER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "posted_articles.json")


class NewsItem(TypedDict):
    title: str
    source: str
    published_at: str  # human-readable date, already formatted
    url: str
    image_url: Optional[str]


def _format_date(iso_string: str) -> str:
    """Convert NewsAPI's ISO8601 publishedAt into a short human-readable date."""
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except (ValueError, AttributeError):
        return datetime.now(timezone.utc).strftime("%b %d, %Y")


def _load_posted_urls() -> list[str]:
    """Read the list of already-posted article URLs from disk. Never raises."""
    try:
        if not os.path.exists(_TRACKER_PATH):
            return []
        with open(_TRACKER_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not read posted-articles tracker, starting fresh: %s", exc)
        return []


def _save_posted_url(url: str, already_posted: list[str]) -> None:
    """Append a newly posted URL to the tracker file, capped at MAX_TRACKED_URLS. Never raises."""
    try:
        updated = already_posted + [url]
        updated = updated[-MAX_TRACKED_URLS:]  # keep only the most recent N
        with open(_TRACKER_PATH, "w", encoding="utf-8") as f:
            json.dump(updated, f)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not save posted-articles tracker: %s", exc)


async def fetch_latest_football_news(session: aiohttp.ClientSession) -> Optional[NewsItem]:
    """
    Fetch the most recent football/soccer article from NewsAPI that hasn't
    already been posted. Returns None if the request fails, the API returns
    an error status, or every candidate article has already been posted —
    callers should treat None as "skip this slot".
    """
    params = {
        "q": "football OR soccer",
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": FETCH_POOL_SIZE,
        "apiKey": config.NEWS_API_KEY,
    }
    try:
        async with session.get(config.NEWSAPI_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                body = await resp.text()
                logger.error("News fetch failed: NewsAPI returned status %s: %s", resp.status, body[:300])
                return None
            data = await resp.json()
    except (aiohttp.ClientError, TimeoutError) as exc:
        logger.error("News fetch failed: network error contacting NewsAPI: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001 — never crash the scheduler
        logger.error("News fetch failed: unexpected error: %s", exc)
        return None

    articles = data.get("articles") or []
    if not articles:
        logger.warning("News fetch: NewsAPI returned no articles for this query.")
        return None

    already_posted = _load_posted_urls()
    already_posted_set = set(already_posted)

    for article in articles:
        url = article.get("url") or ""
        title = (article.get("title") or "").strip()

        if not title or not url:
            continue
        if url in already_posted_set:
            continue  # already posted this one, try the next candidate

        # Found a fresh, not-yet-posted article.
        _save_posted_url(url, already_posted)

        return NewsItem(
            title=title,
            source=(article.get("source") or {}).get("name") or "Unknown source",
            published_at=_format_date(article.get("publishedAt", "")),
            url=url,
            image_url=article.get("urlToImage"),
        )

    # Every candidate in this pool was already posted before.
    logger.warning(
        "News fetch: all %d candidate articles were already posted. Skipping this slot.",
        len(articles),
    )
    return None
