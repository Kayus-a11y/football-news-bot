# World Football News Telegram Bot

Fetches the latest football/soccer headline (NewsAPI), optionally pulls today's
upcoming fixtures from the top 5 European leagues (API-Football), renders a
branded 1080×1080 image, and posts it to a Telegram channel three times a day
(08:00, 14:00, 20:00 UTC).

## Files

| File | Purpose |
|---|---|
| `bot.py` | Entry point — scheduler, posting pipeline, retry/error handling |
| `news_fetcher.py` | NewsAPI request logic |
| `football_data.py` | API-Football fixtures request logic |
| `image_generator.py` | Pillow-based branded image rendering |
| `config.py` | All constants; reads credentials from environment variables |
| `requirements.txt` | Python dependencies |
| `.env.example` | Template for your `.env` file |
| `Procfile` | For Render/Railway worker deployment |
| `football-bot.service.example` | Example systemd unit for a VPS |

## 1. Prerequisites

- Python 3.11+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- Your bot added as an **admin** of the target channel (e.g. `@FootballDailyHubs`), with permission to post messages
- A free API key from [newsapi.org](https://newsapi.org)
- A free API key from [api-sports.io](https://api-sports.io) (API-Football)

## 2. Local setup

```bash
git clone <your-repo-url>
cd football_bot

python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# now edit .env and fill in your real BOT_TOKEN, NEWS_API_KEY, API_FOOTBALL_KEY
```

### Fonts

`image_generator.py` looks for DejaVu Sans fonts at the paths in `config.py`
(default: `/usr/share/fonts/truetype/dejavu/...`), which are preinstalled on
most Debian/Ubuntu systems. On other systems, either install the `fonts-dejavu`
package or set `FONT_BOLD_PATH` / `FONT_REGULAR_PATH` in `.env` to point at
any TrueType fonts you have available. If a font can't be loaded, the bot
falls back to Pillow's built-in default font rather than crashing.

```bash
# Debian/Ubuntu
sudo apt-get install fonts-dejavu
```

## 3. Run locally

```bash
python bot.py
```

The process stays running and posts automatically at 08:00, 14:00, and 20:00
UTC. Leave it running in a terminal, `tmux`/`screen` session, or use one of
the deployment options below for something more durable.

To sanity-check the pipeline without waiting for a scheduled time, you can
temporarily call `asyncio.run(run_post_job())` from a Python shell, or add a
one-off `scheduler.add_job(run_post_job, next_run_time=...)` line in `bot.py`.

## 4. Production deployment

### Option A — Render / Railway (Procfile)

1. Push this project to a GitHub repo.
2. Create a new **Background Worker** service on Render or Railway pointing at the repo.
3. It will detect `Procfile` (`worker: python bot.py`) automatically.
4. Set `BOT_TOKEN`, `CHANNEL_ID`, `NEWS_API_KEY`, `API_FOOTBALL_KEY` as environment variables in the service's dashboard (e.g. Railway's Variables tab) — do **not** commit your `.env` file.
5. Deploy. The worker runs `python bot.py` indefinitely; APScheduler handles the timing internally, so no external cron is needed.

### Option B — VPS with systemd

```bash
# on your server
sudo mkdir -p /opt/football-bot
sudo cp -r . /opt/football-bot
cd /opt/football-bot
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env   # then fill in real values

sudo useradd -r -s /bin/false footballbot
sudo chown -R footballbot:footballbot /opt/football-bot

sudo cp football-bot.service.example /etc/systemd/system/football-bot.service
# edit paths/user inside the unit file if you changed them above

sudo systemctl daemon-reload
sudo systemctl enable --now football-bot
sudo systemctl status football-bot
```

View logs with `journalctl -u football-bot -f`.

## 5. Rate limits & safety

- **NewsAPI free tier:** 100 requests/day. This bot makes at most 3/day (one per scheduled post).
- **API-Football free tier:** 100 requests/day, but this bot self-limits to **3/day** (one per post) as required.
- A 2-second delay is inserted between the NewsAPI and API-Football calls within each post job.
- If NewsAPI fails or returns no articles, that slot is skipped entirely (no post, no crash).
- If image generation fails, that slot is skipped.
- If the Telegram send fails, the bot retries once after 5 seconds; if that also fails, it logs the error and moves on — the scheduler is never taken down by a single failed post.

## 6. Customization

- Change posting times: edit `POST_TIMES_UTC` in `config.py`.
- Change colors/branding: edit `BG_COLOR`, `ACCENT_COLOR`, `HEADER_TEXT`, `FOOTER_TEXT` in `config.py`.
- Change which leagues count as "top 5": edit `TOP_5_LEAGUE_IDS` in `config.py` (IDs are API-Football league IDs).
- Change hashtags: edit `HASHTAGS` in `config.py`.

## 7. Security note

`config.py` never contains real credentials — it only reads them from
environment variables. Keep your real `.env` file out of version control
(it's a good idea to add `.env` to `.gitignore`), and only set real secrets
as environment variables in your hosting provider's dashboard or a
`systemd` `EnvironmentFile`.
