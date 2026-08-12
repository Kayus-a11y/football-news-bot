"""
image_generator.py — Renders a branded PNG image for each Telegram post.

generate_post_image() draws the headline, source, and date onto a simple
dark background and saves it to a temp file, returning the file path.
Returns None if image generation fails for any reason (bot.py treats
that as "skip this slot" rather than crashing).
"""

import logging
import os
import tempfile
import textwrap

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("football_bot")

# Canvas settings
WIDTH, HEIGHT = 1080, 1080
BG_COLOR = (13, 17, 23)          # dark navy/black
ACCENT_COLOR = (0, 200, 120)     # green accent (tweak to your brand color)
TEXT_COLOR = (255, 255, 255)
MUTED_COLOR = (160, 160, 160)

# Try to use a truetype font if available, otherwise fall back to default
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_PATHS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def generate_post_image(headline: str, source: str, date: str) -> str | None:
    """
    Render a branded image containing the headline, source, and date.
    Returns the path to the saved PNG, or None if generation fails.
    """
    try:
        img = Image.new("RGB", (WIDTH, HEIGHT), color=BG_COLOR)
        draw = ImageDraw.Draw(img)

        # Top accent bar
        draw.rectangle([(0, 0), (WIDTH, 12)], fill=ACCENT_COLOR)

        # "⚽ FOOTBALL NEWS" label
        label_font = _load_font(42)
        draw.text((60, 60), "FOOTBALL NEWS", font=label_font, fill=ACCENT_COLOR)

        # Headline (wrapped, large)
        headline_font = _load_font(64)
        wrapped = textwrap.wrap(headline, width=24)[:6]  # cap at 6 lines
        y = 220
        for line in wrapped:
            draw.text((60, y), line, font=headline_font, fill=TEXT_COLOR)
            y += 78

        # Source + date at the bottom
        meta_font = _load_font(36)
        meta_text = f"{source} · {date}"
        draw.text((60, HEIGHT - 120), meta_text, font=meta_font, fill=MUTED_COLOR)

        # Bottom accent bar
        draw.rectangle([(0, HEIGHT - 12), (WIDTH, HEIGHT)], fill=ACCENT_COLOR)

        # Save to a temp file and return its path
        tmp_dir = tempfile.gettempdir()
        out_path = os.path.join(tmp_dir, "post_image.png")
        img.save(out_path, format="PNG")

        return out_path

    except Exception as exc:  # noqa: BLE001 — never crash the caller
        logger.error("Image generation failed: %s", exc)
        return None
