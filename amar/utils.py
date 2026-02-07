"""AMAR utility functions."""

import re
from dataclasses import dataclass
from typing import Optional


def convert_ms(milliseconds: int) -> str:
    """Convert milliseconds to MM:SS format."""
    total_sec = milliseconds / 1000
    minutes = int(total_sec // 60)
    seconds = int(total_sec % 60)
    return f"{minutes}:{seconds:02d}"


def clean_filename(name: str) -> str:
    """Sanitize a string for safe use as a filesystem name."""
    return re.sub(r'[/\\?%*:|"<>\x7F\x00-\x1F]', "-", name)


@dataclass
class ParsedAppleMusicURL:
    content_type: str  # 'artist', 'album', 'music-video', 'station'
    item_id: str
    storefront: str
    raw_url: str


_URL_PATTERN = re.compile(
    r"https?://music\.apple\.com/([a-z]{2})/(artist|album|music-video|station)/[^/]+/(\d+)"
)


def parse_apple_music_url(url: str) -> Optional[ParsedAppleMusicURL]:
    """Parse an Apple Music URL into its components.

    Supported formats:
        https://music.apple.com/{storefront}/artist/{name}/{id}
        https://music.apple.com/{storefront}/album/{name}/{id}
        https://music.apple.com/{storefront}/music-video/{name}/{id}
        https://music.apple.com/{storefront}/station/{name}/{id}

    Returns None if the URL doesn't match any supported format.
    """
    match = _URL_PATTERN.match(url.strip())
    if not match:
        return None

    return ParsedAppleMusicURL(
        content_type=match.group(2),
        storefront=match.group(1),
        item_id=match.group(3),
        raw_url=url.strip(),
    )
