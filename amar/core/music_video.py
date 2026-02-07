"""Async music video asset ripper."""

import os
from datetime import datetime
from typing import Callable, Optional

import aiofiles

from ..api.client import AsyncAppleMusicClient
from ..config import AMARConfig
from ..utils import clean_filename, convert_ms
from .downloader import AsyncDownloader

VIDEO_EXTEND_PARAMS = (
    "?extend=editorialArtwork,editorialVideo,extendedAssetUrls,offers,"
    "seoDescription,seoTitle"
    "&format[resources]=map&include=artists,albums"
)

LogCallback = Optional[Callable[[str, str], None]]


class MusicVideoRipper:
    """Downloads music video assets from the Apple Music API."""

    def __init__(self, client: AsyncAppleMusicClient, config: AMARConfig):
        self._client = client
        self._config = config
        self._downloader = AsyncDownloader(client, config.chunk_size)

    async def rip(
        self,
        video_id: str,
        storefront: str,
        info_only: bool = False,
        log: LogCallback = None,
        progress_callback=None,
    ) -> Optional[str]:
        """Download music video assets for a single storefront.

        Returns the path to the assets folder, or None if no data found.
        """
        _log = log or (lambda msg, lvl="INFO": None)
        _pcb = progress_callback

        url = f"/v1/catalog/{storefront}/music-videos/{video_id}{VIDEO_EXTEND_PARAMS}"
        data = await self._client.get(url)

        resources = data.get("resources", {})
        videos = resources.get("music-videos", {})
        if video_id not in videos:
            _log(f"Failed to retrieve data for video ID: {video_id}", "ERROR")
            return None

        main_data = videos[video_id]
        video_name = clean_filename(main_data["attributes"]["name"])
        artist_name = clean_filename(main_data["attributes"]["artistName"])

        current_date = datetime.today().strftime("%Y-%m-%d")
        folder = os.path.join(
            self._config.save_path,
            "Music Video Assets",
            f"{artist_name} - {video_name} - {current_date}",
        )
        os.makedirs(folder, exist_ok=True)

        if not info_only:
            await self._download_preview(main_data, video_name, storefront, folder, _log, _pcb)

        await self._write_info(main_data, video_name, storefront, folder, _log)

        status = "info" if info_only else "assets"
        _log(f"Music video {status} saved to {folder}", "SUCCESS")
        return folder

    async def _download_preview(self, data, video_name, storefront, folder, log, progress_callback=None):
        artwork = data["attributes"].get("artwork")
        if not artwork:
            return
        try:
            w, h = artwork["width"], artwork["height"]
            url = artwork["url"].replace("{w}", str(w)).replace("{h}", str(h))
            filename = f"{video_name} ({storefront}) - Preview Frame - {w}x{h}.jpg"
            log(f"Downloading {filename}", "INFO")
            await self._downloader.download_file_cdn(url, os.path.join(folder, filename), progress_callback)
        except (KeyError, Exception) as e:
            log(f"Failed to download preview frame: {e}", "ERROR")

    async def _write_info(self, data, video_name, storefront, folder, log):
        filename = f"{video_name} ({storefront}) - INFO.txt"
        log(f"Writing {filename}", "INFO")
        filepath = os.path.join(folder, filename)

        attrs = data.get("attributes", {})
        lines = []

        name = attrs.get("name")
        if name:
            lines.append(f"Name: {name}")

        artist = attrs.get("artistName")
        if artist:
            lines.append(f"Artist: {artist}")

        album = attrs.get("albumName", "N/A")
        lines.append(f"Album: {album}")

        release = attrs.get("releaseDate", "Unknown")
        lines.append(f"Release Date: {release}")

        duration_ms = attrs.get("durationInMillis")
        if duration_ms:
            lines.append(f"Duration: {convert_ms(duration_ms)}")

        url = attrs.get("url")
        if url:
            lines.append(f"URL: {url}")

        async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
            await f.write("\n".join(lines) + "\n")
