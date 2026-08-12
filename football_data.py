"""
football_data.py — Fetches today's upcoming fixtures (top 5 European leagues)
from API-Football, used as bonus context in the post caption.
"""

import logging
from datetime import datetime, timezone
from typing import List

import aiohttp

import config

logger = logging.getLogger(__name__)


def _format_fixture(fixture: dict) -> str:
    """Render one fixture dict into a short 'Home vs Away' string."""
    teams = fixture.get("teams", {})
    home = (teams.get("home") or {}).get("name", "?")
    away = (teams.get("away") or {}).get("name", "?")
    return f"{home} vs {away}"


async def fetch_todays_top_fixtures(session: aiohttp.ClientSession, limit: int = 2) -> List[str]:
    """
    Fetch up to `limit` not-yet-started fixtures for today, restricted to the
    top 5 European leagues. Returns an empty list on any failure — this is a
    "bonus" feature, so failures here should never block the main post.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    headers = {"x-apisports-key": config.API_FOOTBALL_KEY}
    params = {"date": today, "status": "NS"}

    try:
        async with session.get(
            config.APIFOOTBALL_FIXTURES_URL,
            headers=headers,
            params=params,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                logger.error("Football data fetch failed: status %s: %s", resp.status, body[:300])
                return []

            data = await resp.json()

    except (aiohttp.ClientError, TimeoutError) as exc:
        logger.error("Football data fetch failed: network error: %s", exc)
        return []
    except Exception as exc:  # noqa: BLE001 — never crash the scheduler
        logger.error("Football data fetch failed: unexpected error: %s", exc)
        return []

    fixtures = data.get("response") or []

    top_league_fixtures = [
        f for f in fixtures
        if (f.get("league") or {}).get("id") in config.TOP_5_LEAGUE_IDS
    ]

    selected = top_league_fixtures[:limit]
    return [_format_fixture(f) for f in selected]
