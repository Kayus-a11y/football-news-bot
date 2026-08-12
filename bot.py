"""
bot.py — Main entry point for the World Football News Telegram Bot.

Fetches the latest football news + today's top fixtures, renders a branded
image, and posts it to the configured Telegram channel. Runs on a schedule
(08:00, 14:00, 20:00 UTC by default) via APScheduler, and keeps the asyncio
event loop alive indefinitely.

Run with:  python bot.py
"""

import asyncio
import logging
import sys

import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
from telegram.error import TelegramError

import config
from news_fetcher import fetch_latest_football_news
from football_data import fetch_todays_top_fixtures
from image_generator import generate_post_image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("football_bot")


def build_caption(headline: str, source: str, date: str, url: str, fixtures: list[str]) -> str:
    """Assemble the Telegram caption in the required format."""
    lines = [f"⚽ {headline}", "", f"📰 {source} • {date}"]

    if fixtures:
        lines.append(f"🏆 Today's Fixtures: {', '.join(fixtures)}")

    lines.append(f"🔗 Read more: {url}")
    lines.append("")
    lines.append(config.HASHTAGS)

    return "\n".join(lines)


async def send_with_retry(bot: Bot, image_path: str, caption: str) -> bool:
    """
    Send the photo to the Telegram channel. On failure, retry once after a
    short delay. Returns True on success, False if both attempts failed.
    """
    for attempt in (1, 2):
        try:
            with open(image_path, "rb") as photo:
                await bot.send_photo(
                    chat_id=config.CHANNEL_ID,
                    photo=photo,
                    caption=caption,
                    disable_notification=False,
                )
            logger.info("Posted successfully to %s (attempt %d).", config.CHANNEL_ID, attempt)
            return True

        except TelegramError as exc:
            logger.error("Telegram send failed on attempt %d: %s", attempt, exc)
            if attempt == 1:
                await asyncio.sleep(config.TELEGRAM_RETRY_DELAY_SECONDS)
        except Exception as exc:  # noqa: BLE001 — never crash the scheduler
            logger.error("Unexpected error sending to Telegram on attempt %d: %s", attempt, exc)
            if attempt == 1:
                await asyncio.sleep(config.TELEGRAM_RETRY_DELAY_SECONDS)

    logger.error("Telegram send failed after retry. Skipping this slot.")
    return False


async def run_post_job() -> None:
    """
    The full pipeline for a single scheduled post:
    fetch news -> (delay) -> fetch fixtures -> generate image -> post -> log.
    Every stage is wrapped so a failure anywhere just skips this slot rather
    than crashing the scheduler.
    """
    logger.info("Starting scheduled post job.")

    async with aiohttp.ClientSession() as session:
        news_item = await fetch_latest_football_news(session)
        if news_item is None:
            logger.error("News fetch failed or returned nothing. Skipping this slot.")
            return

        await asyncio.sleep(config.INTER_API_CALL_DELAY_SECONDS)

        fixtures = await fetch_todays_top_fixtures(session, limit=2)

    image_path = generate_post_image(
        headline=news_item["title"],
        source=news_item["source"],
        date=news_item["published_at"],
    )
    if image_path is None:
        logger.error("Image generation failed. Skipping this slot.")
        return

    caption = build_caption(
        headline=news_item["title"],
        source=news_item["source"],
        date=news_item["published_at"],
        url=news_item["url"],
        fixtures=fixtures,
    )

    bot = Bot(token=config.BOT_TOKEN)
    success = await send_with_retry(bot, image_path, caption)

    if not success:
        logger.error("Post job ended without a successful send for this slot.")
    else:
        logger.info("Post job completed successfully.")


def build_scheduler() -> AsyncIOScheduler:
    """Configure an AsyncIOScheduler with the 3 daily UTC posting times."""
    scheduler = AsyncIOScheduler(timezone=config.TIMEZONE)

    for hour, minute in config.POST_TIMES_UTC:
        scheduler.add_job(
            run_post_job,
            trigger=CronTrigger(hour=hour, minute=minute, timezone=config.TIMEZONE),
            id=f"post_{hour:02d}{minute:02d}",
            misfire_grace_time=300,  # allow up to 5 min late if the process was busy
            coalesce=True,
        )
        logger.info("Scheduled daily post at %02d:%02d UTC", hour, minute)

    return scheduler


async def main() -> None:
    # config.py already validated that BOT_TOKEN, NEWS_API_KEY, and
    # API_FOOTBALL_KEY are set — it raises ValueError at import time if not,
    # so by the time we get here the bot is safe to run.
    scheduler = build_scheduler()
    scheduler.start()

    logger.info("Bot is running. Waiting for scheduled post times (Ctrl+C to stop).")

    # Keep the event loop alive indefinitely.
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown signal received. Stopping scheduler.")
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
