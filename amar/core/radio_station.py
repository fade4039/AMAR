"""Async radio station asset ripper."""

import os
from datetime import datetime
from typing import Callable, Optional

import aiofiles

from ..api.client import AsyncAppleMusicClient
from ..config import AMARConfig
from ..utils import clean_filename
from .downloader import AsyncDownloader

LogCallback = Optional[Callable[[str, str], None]]


class RadioStationRipper:
    """Downloads radio station assets from the Apple Music API."""

    def __init__(self, client: AsyncAppleMusicClient, config: AMARConfig):
        self._client = client
        self._config = config
        self._downloader = AsyncDownloader(client, config.chunk_size)

    async def rip(
        self,
        station_id: str,
        storefront: str,
        info_only: bool = False,
        log: LogCallback = None,
        progress_callback=None,
    ) -> Optional[str]:
        """Download radio station assets for a single storefront.

        Returns the path to the assets folder, or None if no data found.
        """
        _log = log or (lambda msg, lvl="INFO": None)
        _pcb = progress_callback

        url = f"/v1/catalog/{storefront}/stations/{station_id}"
        data = await self._client.get(url)

        if "data" not in data or not data["data"]:
            _log(f"Failed to retrieve data for station ID: {station_id}", "ERROR")
            return None

        main_data = data["data"][0]
        station_name = clean_filename(main_data["attributes"]["name"])

        current_date = datetime.today().strftime("%Y-%m-%d")
        folder = os.path.join(
            self._config.save_path,
            "Radio Station Assets",
            clean_filename(f"{station_name} - {current_date}"),
        )
        os.makedirs(folder, exist_ok=True)

        if not info_only:
            await self._download_artwork(main_data, station_name, storefront, folder, _log, _pcb)

        await self._write_info(main_data, station_name, storefront, folder, _log)

        status = "info" if info_only else "assets"
        _log(f"Radio station {status} saved to {folder}", "SUCCESS")
        return folder

    async def _download_artwork(self, data, station_name, storefront, folder, log, progress_callback=None):
        artwork = data["attributes"].get("artwork")
        if not artwork:
            log("No artwork found for this station.", "WARNING")
            return
        try:
            w, h = artwork["width"], artwork["height"]
            url = artwork["url"].replace("{w}", str(w)).replace("{h}", str(h))
            filename = f"{station_name} ({storefront}) - Artwork - {w}x{h}.jpg"
            log(f"Downloading {filename}", "INFO")
            await self._downloader.download_file_cdn(url, os.path.join(folder, filename), progress_callback)
        except (KeyError, Exception) as e:
            log(f"Artwork download failed: {e}", "WARNING")

    async def _write_info(self, data, station_name, storefront, folder, log):
        filename = f"{station_name} ({storefront}) - INFO.txt"
        log(f"Writing {filename}", "INFO")
        filepath = os.path.join(folder, filename)

        attrs = data.get("attributes", {})
        lines = [
            f"Name: {attrs.get('name', 'Unknown')}",
            f"Description: {attrs.get('description', 'No description')}",
            f"URL: {attrs.get('url', 'No URL')}",
            f"Release Date: {attrs.get('releaseDate', 'Unknown')}",
        ]

        async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
            await f.write("\n".join(lines) + "\n")
