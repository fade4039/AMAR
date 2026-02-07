"""Async album asset ripper."""

import os
import textwrap
from typing import Callable, Optional

import aiofiles

from ..api.client import AsyncAppleMusicClient
from ..config import AMARConfig
from ..utils import clean_filename, convert_ms
from .downloader import AsyncDownloader
from .m3u8 import M3U8Error, resolve_m3u8_video_url

ALBUM_EXTEND_PARAMS = (
    "?extend=editorialArtwork,editorialVideo,extendedAssetUrls,offers,"
    "seoDescription,seoTitle"
    "&format[resources]=map&include=record-labels,artists"
    "&include[songs]=artists,composers,albums"
)

LogCallback = Optional[Callable[[str, str], None]]


class AlbumRipper:
    """Downloads album assets from the Apple Music API."""

    def __init__(self, client: AsyncAppleMusicClient, config: AMARConfig):
        self._client = client
        self._config = config
        self._downloader = AsyncDownloader(client, config.chunk_size)

    async def rip(
        self,
        album_id: str,
        storefront: str,
        info_only: bool = False,
        log: LogCallback = None,
        progress_callback=None,
    ) -> Optional[str]:
        """Download album assets for a single storefront.

        Returns the path to the album assets folder, or None if no data found.
        """
        _log = log or (lambda msg, lvl="INFO": None)
        _pcb = progress_callback

        url = f"/v1/catalog/{storefront}/albums/{album_id}{ALBUM_EXTEND_PARAMS}"
        data = await self._client.get(url)

        songs_data = data.get("resources", {}).get("songs", {})
        if not songs_data:
            _log(f"No song data found for album {album_id}, skipping", "WARNING")
            return None

        main_data = data["resources"]["albums"][album_id]
        artist_name = main_data["attributes"]["artistName"]
        album_name = main_data["attributes"]["name"]
        release_date = main_data["attributes"].get("releaseDate", "Unknown")

        folder = os.path.join(
            self._config.save_path,
            "Album Assets",
            clean_filename(f"{artist_name} - {album_name} - {release_date}"),
        )
        os.makedirs(folder, exist_ok=True)

        if not info_only:
            await self._download_editorial_videos(main_data, album_name, storefront, folder, _log, _pcb)
            await self._download_editorial_artwork(main_data, album_name, storefront, folder, _log, _pcb)
            await self._download_general_artwork(main_data, album_name, storefront, folder, _log, _pcb)

        await self._write_info(main_data, songs_data, album_name, storefront, folder, _log)

        status = "info" if info_only else "assets"
        _log(f"Album {status} saved to {folder}", "SUCCESS")
        return folder

    async def _download_editorial_videos(self, data, album_name, storefront, folder, log, progress_callback=None):
        editorial_video = data["attributes"].get("editorialVideo")
        if not editorial_video:
            return

        for video_key, video_data in editorial_video.items():
            # Preview frame
            try:
                preview = video_data["previewFrame"]
                w, h = preview["width"], preview["height"]
                url = preview["url"].replace("{w}", str(w)).replace("{h}", str(h))
                filename = clean_filename(f"{album_name} ({storefront}) - {video_key} - {w}x{h}.jpg")
                log(f"Downloading {filename}", "INFO")
                await self._downloader.download_file_cdn(url, os.path.join(folder, filename), progress_callback)
            except (KeyError, Exception) as e:
                log(f"Preview frame for {video_key} not available: {e}", "WARNING")

            # Video file via M3U8
            try:
                m3u8_url = video_data["video"]
                video_url = await resolve_m3u8_video_url(self._client, m3u8_url)
                filename = clean_filename(f"{album_name} ({storefront}) - {video_key}.mp4")
                log(f"Downloading {filename}", "INFO")
                await self._downloader.download_file_cdn(video_url, os.path.join(folder, filename), progress_callback)
            except (KeyError, M3U8Error, Exception) as e:
                log(f"Video {video_key} not available: {e}", "WARNING")

    async def _download_editorial_artwork(self, data, album_name, storefront, folder, log, progress_callback=None):
        editorial_artwork = data["attributes"].get("editorialArtwork")
        if not editorial_artwork:
            return

        for key, artwork in editorial_artwork.items():
            try:
                w, h = artwork["width"], artwork["height"]
                url = artwork["url"].replace("{w}", str(w)).replace("{h}", str(h))
                filename = clean_filename(f"{album_name} ({storefront}) - {key} - {w}x{h}.jpg")
                log(f"Downloading {filename}", "INFO")
                await self._downloader.download_file_cdn(url, os.path.join(folder, filename), progress_callback)
            except (KeyError, Exception) as e:
                log(f"Editorial artwork {key} not available: {e}", "WARNING")

    async def _download_general_artwork(self, data, album_name, storefront, folder, log, progress_callback=None):
        artwork = data["attributes"].get("artwork")
        if not artwork:
            return
        try:
            w, h = artwork["width"], artwork["height"]
            url = artwork["url"].replace("{w}", str(w)).replace("{h}", str(h))
            filename = clean_filename(f"{album_name} ({storefront}) - artwork - {w}x{h}.jpg")
            log(f"Downloading {filename}", "INFO")
            await self._downloader.download_file_cdn(url, os.path.join(folder, filename), progress_callback)
        except (KeyError, Exception) as e:
            log(f"General artwork not available: {e}", "WARNING")

    async def _write_info(self, data, songs_data, album_name, storefront, folder, log):
        filename = clean_filename(f"{album_name} ({storefront}) - INFO.txt")
        log(f"Writing {filename}", "INFO")
        filepath = os.path.join(folder, filename)

        attrs = data.get("attributes", {})
        lines = []

        lines.append(f"Album name: {attrs.get('name', 'Unknown')}")
        lines.append(f"Artist name: {attrs.get('artistName', 'Unknown')}")

        genres = attrs.get("genreNames")
        if genres:
            lines.append(f"Genre: {'/'.join(genres)}")

        for field, label in [
            ("copyright", "Copyright"),
            ("releaseDate", "Release Date"),
            ("upc", "UPC"),
            ("url", "URL"),
            ("recordLabel", "Record Label"),
            ("trackCount", "Track count"),
        ]:
            value = attrs.get(field)
            if value is not None:
                lines.append(f"{label}: {value}")

        audio_traits = attrs.get("audioTraits")
        if audio_traits:
            lines.append(f"Audio Traits: {', '.join(audio_traits)}")

        for field, label in [
            ("isCompilation", "Compilation"),
            ("isPrerelease", "Pre-release"),
            ("isSingle", "Single"),
        ]:
            value = attrs.get(field)
            if value is not None:
                lines.append(f"{label}: {value}")

        # Build track list
        track_list = []
        for song_id, song_item in songs_data.items():
            s_attrs = song_item.get("attributes", {})
            track_num = int(s_attrs.get("trackNumber", 0))
            name = s_attrs.get("name", "Unknown")
            duration_ms = s_attrs.get("durationInMillis")
            duration = convert_ms(duration_ms) if duration_ms else "Unknown"
            composer = s_attrs.get("composerName", "No Composer")
            isrc = s_attrs.get("isrc", "No ISRC")
            track_list.append((track_num, name, duration, composer, isrc))

        track_list.sort(key=lambda x: x[0])

        lines.append("")
        lines.append("Track list:")
        for track_num, name, duration, composer, isrc in track_list:
            lines.append(f"{track_num}. {name} - {duration} ({composer}) ({isrc})")

        # Editorial notes
        notes = attrs.get("editorialNotes", {})
        tagline = notes.get("tagline")
        if tagline:
            lines.append("")
            lines.append(f"Tagline: {tagline}")

        short = notes.get("short")
        if short:
            lines.append(f"Short phrase: {short}")

        standard = notes.get("standard")
        if standard:
            lines.append("Album bio:")
            lines.append(textwrap.fill(str(standard), width=100))

        async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
            await f.write("\n".join(lines) + "\n")
