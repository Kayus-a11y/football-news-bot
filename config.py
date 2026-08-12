"""
config.py — Central configuration for the World Football News Telegram Bot.

All secrets are loaded from environment variables (via a local .env file in
development, or real environment variables in production). NEVER hardcode
real tokens/keys in this file — copy .env.example to .env and fill it in.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # loads variables from a local .env file, if present

# ---------------------------------------------------------------------------
# Credentials (read from environment — see .env.example)
# ---------------------------------------------------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@FootballDailyHubs")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY")

# Safety check — bot won't start if variables are missing
required = [BOT_TOKEN, NEWS_API_KEY, API_FOOTBALL_KEY]
if not all(required):
    raise ValueError(
        "Missing required environment variables! Check that BOT_TOKEN, "
        "NEWS_API_KEY, and API_FOOTBALL_KEY are all set (e.g. in your "
        ".env file locally, or in your Railway/Render Variables tab)."
    )

# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------
NEWSAPI_URL = "https://newsapi.org/v2/everything"
APIFOOTBALL_FIXTURES_URL = "https://v3.football.api-sports.io/fixtures"

# Top 5 European league IDs on API-Football (v3):
# 39 = Premier League, 140 = La Liga, 135 = Serie A,
# 78 = Bundesliga, 61 = Ligue 1
TOP_5_LEAGUE_IDS = {39, 140, 135, 78, 61}

# ---------------------------------------------------------------------------
# Image generation
# ---------------------------------------------------------------------------
IMAGE_SIZE = (1080, 1080)
IMAGE_PATH = "/tmp/football_post.png"

BG_COLOR = "#12121a"
ACCENT_COLOR = "#00e676"
WHITE = "#ffffff"
GRAY = "#9a9aa5"

HEADER_TEXT = "⚽ WORLD FOOTBALL NEWS"
FOOTER_TEXT = "via @FootballDailyHubs"
TEXT_MARGIN = 60  # px margin for headline wrapping

# Font paths — DejaVuSans ships with Pillow's default install on most Linux
# systems. Override via env vars if you bundle custom fonts.
FONT_BOLD_PATH = os.getenv("FONT_BOLD_PATH", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
FONT_REGULAR_PATH = os.getenv("FONT_REGULAR_PATH", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")

# ---------------------------------------------------------------------------
# Scheduling (UTC)
# ---------------------------------------------------------------------------
POST_TIMES_UTC = [(8, 0), (14, 0), (20, 0)]  # (hour, minute) tuples
TIMEZONE = "UTC"

# ---------------------------------------------------------------------------
# Safety / rate limits
# ---------------------------------------------------------------------------
INTER_API_CALL_DELAY_SECONDS = 2
TELEGRAM_RETRY_DELAY_SECONDS = 5
MAX_APIFOOTBALL_CALLS_PER_DAY = 3  # one per scheduled post
MAX_NEWSAPI_CALLS_PER_DAY = 100

# ---------------------------------------------------------------------------
# Hashtags appended to every caption
# ---------------------------------------------------------------------------
HASHTAGS = "#Football #Soccer #WorldFootball #FootballNews"
