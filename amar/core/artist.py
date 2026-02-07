"""Async artist asset ripper."""

import os
import textwrap
from typing import Callable, List, Optional

from ..api.client import AsyncAppleMusicClient
from ..api.pagination import collect_all_ids
from ..config import AMARConfig
from ..utils import clean_filename
from .downloader import AsyncDownloader
from .m3u8 import M3U8Error, resolve_m3u8_video_url

ARTIST_EXTEND_PARAMS = (
    "extend=artistBio,bornOrFormed,editorialArtwork,editorialVideo,"
    "extendedAssetUrls,hero,isGroup,origin,plainEditorialNotes,"
    "seoDescription,seoTitle"
    "&format[resources]=map&include=record-labels,artists"
    "&include[songs]=artists&l=en-US&platform=web"
)


LogCallback = Optional[Callable[[str, str], None]]


class ArtistRipper:
    """Downloads artist assets from the Apple Music API."""

    def __init__(self, client: AsyncAppleMusicClient, config: AMARConfig):
        self._client = client
        self._config = config
        self._downloader = AsyncDownloader(client, config.chunk_size)

    async def rip(
        self,
        artist_id: str,
        storefront: str,
        info_only: bool = False,
        log: LogCallback = None,
        progress_callback=None,
    ) -> str:
        """Download artist assets for a single storefront.

        Returns the path to the artist assets folder.
        """
        _log = log or (lambda msg, lvl="INFO": None)
        _pcb = progress_callback

        url = f"/v1/catalog/{storefront}/artists/{artist_id}?{ARTIST_EXTEND_PARAMS}"
        data = await self._client.get(url)

        main_data = data["resources"]["artists"][artist_id]
        artist_name = clean_filename(main_data["attributes"]["name"])

        from datetime import datetime
        current_date = datetime.today().strftime("%Y-%m-%d")
        folder = os.path.join(
            self._config.save_path,
            f"{artist_name} - Artist Assets - {current_date}",
        )
        os.makedirs(folder, exist_ok=True)

        if not info_only:
            await self._download_hero(main_data, artist_name, storefront, folder, _log, _pcb)
            await self._download_editorial_videos(main_data, artist_name, storefront, folder, _log, _pcb)
            await self._download_editorial_artwork(main_data, artist_name, storefront, folder, _log, _pcb)
            await self._download_general_artwork(main_data, artist_name, storefront, folder, _log, _pcb)

        await self._write_info(main_data, artist_name, storefront, folder, _log)

        status = "info" if info_only else "assets"
        _log(f"Artist {status} saved to {folder}", "SUCCESS")
        return folder

    async def get_album_ids(self, artist_id: str, storefront: str) -> List[str]:
        """Get all album IDs for an artist using iterative pagination."""
        return await collect_all_ids(self._client, artist_id, storefront, "albums")

    async def get_music_video_ids(self, artist_id: str, storefront: str) -> List[str]:
        """Get all music video IDs for an artist using iterative pagination."""
        return await collect_all_ids(self._client, artist_id, storefront, "music-videos")

    # --- Private download helpers ---

    async def _download_hero(self, data, artist_name, storefront, folder, log, progress_callback=None):
        hero_list = data["attributes"].get("hero")
        if not hero_list:
            return
        try:
            artwork = hero_list[0]["content"][0]["artwork"]
            w, h = artwork["width"], artwork["height"]
            url = artwork["url"].replace("{w}", str(w)).replace("{h}", str(h))
            filename = clean_filename(f"{artist_name} ({storefront}) - Hero - {w}x{h}.jpg")
            log(f"Downloading {filename}", "INFO")
            await self._downloader.download_file_cdn(url, os.path.join(folder, filename), progress_callback)
        except (KeyError, IndexError, Exception) as e:
            log(f"Hero artwork not available: {e}", "WARNING")

    async def _download_editorial_videos(self, data, artist_name, storefront, folder, log, progress_callback=None):
        editorial_video = data["attributes"].get("editorialVideo")
        if not editorial_video:
            return

        for video_key, video_data in editorial_video.items():
            # Preview frame
            try:
                preview = video_data["previewFrame"]
                w, h = preview["width"], preview["height"]
                url = preview["url"].replace("{w}", str(w)).replace("{h}", str(h))
                filename = clean_filename(f"{artist_name} ({storefront}) - {video_key} - {w}x{h}.jpg")
                log(f"Downloading {filename}", "INFO")
                await self._downloader.download_file_cdn(url, os.path.join(folder, filename), progress_callback)
            except (KeyError, Exception) as e:
                log(f"Preview frame for {video_key} not available: {e}", "WARNING")

            # Video file via M3U8
            try:
                m3u8_url = video_data["video"]
                video_url = await resolve_m3u8_video_url(self._client, m3u8_url)
                filename = clean_filename(f"{artist_name} ({storefront}) - {video_key}.mp4")
                log(f"Downloading {filename}", "INFO")
                await self._downloader.download_file_cdn(video_url, os.path.join(folder, filename), progress_callback)
            except (KeyError, M3U8Error, Exception) as e:
                log(f"Video {video_key} not available: {e}", "WARNING")

    async def _download_editorial_artwork(self, data, artist_name, storefront, folder, log, progress_callback=None):
        editorial_artwork = data["attributes"].get("editorialArtwork")
        if not editorial_artwork:
            return

        for key, artwork in editorial_artwork.items():
            try:
                w, h = artwork["width"], artwork["height"]
                url = artwork["url"].replace("{w}", str(w)).replace("{h}", str(h))
                filename = clean_filename(f"{artist_name} ({storefront}) - {key} - {w}x{h}.jpg")
                log(f"Downloading {filename}", "INFO")
                await self._downloader.download_file_cdn(url, os.path.join(folder, filename), progress_callback)
            except (KeyError, Exception) as e:
                log(f"Editorial artwork {key} not available: {e}", "WARNING")

    async def _download_general_artwork(self, data, artist_name, storefront, folder, log, progress_callback=None):
        artwork = data["attributes"].get("artwork")
        if not artwork:
            return
        try:
            w, h = artwork["width"], artwork["height"]
            url = artwork["url"].replace("{w}", str(w)).replace("{h}", str(h))
            filename = clean_filename(f"{artist_name} ({storefront}) - artwork - {w}x{h}.jpg")
            log(f"Downloading {filename}", "INFO")
            await self._downloader.download_file_cdn(url, os.path.join(folder, filename), progress_callback)
        except (KeyError, Exception) as e:
            log(f"General artwork not available: {e}", "WARNING")

    async def _write_info(self, data, artist_name, storefront, folder, log):
        filename = f"{artist_name} ({storefront}) - INFO.txt"
        log(f"Downloading {filename}", "INFO")
        filepath = os.path.join(folder, filename)

        attrs = data.get("attributes", {})
        lines = []

        name = attrs.get("name")
        if name:
            lines.append(f"Name: {name}")

        genres = attrs.get("genreNames")
        if genres:
            lines.append(f"Genre: {'/'.join(genres)}")

        born = attrs.get("bornOrFormed")
        if born:
            lines.append(f"Born or formed: {born}")

        origin = attrs.get("origin")
        if origin:
            lines.append(f"Origin: {origin}")

        is_group = attrs.get("isGroup")
        if is_group is not None:
            lines.append(f"Group: {is_group}")

        url = attrs.get("url")
        if url:
            lines.append(f"Apple Music URL: {url}")

        bio = attrs.get("artistBio")
        if bio:
            lines.append("")
            lines.append("Artist Bio:")
            lines.append(textwrap.fill(str(bio), width=100))

        import aiofiles
        async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
            await f.write("\n".join(lines) + "\n")
