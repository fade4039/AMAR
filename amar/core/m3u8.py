"""M3U8 HLS playlist resolution for Apple Music editorial videos."""

from ..api.client import AsyncAppleMusicClient


class M3U8Error(Exception):
    """Raised when M3U8 playlist resolution fails."""


async def resolve_m3u8_video_url(client: AsyncAppleMusicClient, m3u8_url: str) -> str:
    """Resolve an HLS M3U8 master playlist to a direct video segment URL.

    Steps:
        1. Fetch master playlist → extract the highest-quality variant URL
        2. Fetch variant playlist → extract the video segment filename
        3. Construct and return the full video URL

    Args:
        client: The async API client
        m3u8_url: URL to the master M3U8 playlist

    Returns:
        Direct URL to the video segment file

    Raises:
        M3U8Error: If resolution fails at any step
    """
    # Step 1: Fetch master playlist and find variant URL (no auth headers for CDN)
    master_text = await client.get_text_cdn(m3u8_url)

    variant_url = ""
    for line in master_text.splitlines():
        line = line.strip()
        if "https://" in line:
            variant_url = line  # Last HTTPS URL = highest bitrate

    if not variant_url:
        raise M3U8Error(f"No variant URL found in master playlist: {m3u8_url}")

    # Step 2: Fetch variant playlist and find segment (no auth headers for CDN)
    # The working version iterates ALL lines without break — the last match wins.
    # This is critical because #EXT-X-MAP tags also contain the filename prefix
    # but produce invalid URLs. We skip comment/tag lines (starting with #) and
    # only match bare segment filenames.
    link_parts = variant_url.split("/")
    variant_text = await client.get_text_cdn(variant_url)

    segment_name = ""
    prefix = link_parts[-1][:20]
    for line in variant_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if prefix in line:
            segment_name = line

    if not segment_name:
        raise M3U8Error(f"No segment found in variant playlist: {variant_url}")

    # Step 3: Construct full video URL
    link_parts[-1] = segment_name
    return "/".join(link_parts)
