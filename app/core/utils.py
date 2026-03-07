"""Utility functions for AMAR."""

import re
from pathlib import Path
from typing import Optional


def parse_apple_music_url(url: str) -> Optional[dict]:
    """Parse an Apple Music URL into its components.

    Supports:
        - https://music.apple.com/{storefront}/artist/{name}/{id}
        - https://music.apple.com/{storefront}/album/{name}/{id}
        - https://music.apple.com/{storefront}/music-video/{name}/{id}
        - https://music.apple.com/{storefront}/playlist/{name}/{id}
        - https://music.apple.com/{storefront}/station/{name}/{id}
        - https://music.apple.com/{storefront}/song/{name}/{id}
    """
    patterns = [
        (r"music\.apple\.com/(\w{2})/artist/[^/]+/(\d+)", "artist"),
        (r"music\.apple\.com/(\w{2})/album/[^/]*/(\d+)(?:\?i=(\d+))?", "album"),
        (r"music\.apple\.com/(\w{2})/music-video/[^/]+/(\d+)", "music-video"),
        (r"music\.apple\.com/(\w{2})/playlist/[^/]*/([a-zA-Z0-9.]+)", "playlist"),
        (r"music\.apple\.com/(\w{2})/station/[^/]+/([a-zA-Z0-9.]+)", "station"),
        (r"music\.apple\.com/(\w{2})/song/[^/]+/(\d+)", "song"),
    ]

    for pattern, resource_type in patterns:
        m = re.search(pattern, url)
        if m:
            result = {
                "storefront": m.group(1),
                "type": resource_type,
                "id": m.group(2),
            }
            if resource_type == "album" and m.group(3):
                result["song_id"] = m.group(3)
            return result
    return None


def clean_filename(name: str, max_len: int = 200) -> str:
    """Sanitize a string for use as a filename."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    name = re.sub(r'_+', '_', name).strip('. _')
    return name[:max_len] if name else "unknown"


def convert_ms(ms: int) -> str:
    """Convert milliseconds to MM:SS format."""
    seconds = ms // 1000
    return f"{seconds // 60}:{seconds % 60:02d}"


def ensure_dir(path: str) -> Path:
    """Ensure a directory exists and return the Path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
