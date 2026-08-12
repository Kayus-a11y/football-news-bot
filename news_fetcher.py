"""
news_fetcher.py — Fetches the latest football/soccer headline from NewsAPI.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, TypedDict

import aiohttp

import config

logger = logging.getLogger(__name__)


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


async def fetch_latest_football_news(session: aiohttp.ClientSession) -> Optional[NewsItem]:
    """
    Fetch the single most recent football/soccer article from NewsAPI.

    Returns None if the request fails, the API returns an error status,
    or no articles are found — callers should treat None as "skip this slot".
    """
    params = {
        "q": "football OR soccer",
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": 1,
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

    article = articles[0]
    title = (article.get("title") or "").strip()
    if not title:
        logger.warning("News fetch: top article had no title, skipping.")
        return None

    return NewsItem(
        title=title,
        source=(article.get("source") or {}).get("name") or "Unknown source",
        published_at=_format_date(article.get("publishedAt", "")),
        url=article.get("url") or "",
        image_url=article.get("urlToImage"),
    )
