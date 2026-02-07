"""CLI menu interface for AMAR."""

import asyncio
import os
import sys
from typing import Optional

from ..api.client import AsyncAppleMusicClient, TokenExpiredError
from ..api.token import extract_token_with_selenium
from ..config import COUNTRY_CODES, AMARConfig
from ..core.album import AlbumRipper
from ..core.artist import ArtistRipper
from ..core.charts import format_charts, get_charts
from ..core.music_video import MusicVideoRipper
from ..core.radio_station import RadioStationRipper
from ..core.search import format_search_results, search_catalog
from ..utils import parse_apple_music_url


def _log_cli(message: str, level: str = "INFO") -> None:
    prefix_map = {
        "INFO": ">>",
        "SUCCESS": "[OK]",
        "WARNING": "[!]",
        "ERROR": "[X]",
    }
    prefix = prefix_map.get(level, ">>")
    print(f"  {prefix} {message}")


def _print_menu():
    print("\n" + "=" * 60)
    print("  APPLE MUSIC API RIPPER (AMAR) V2")
    print("=" * 60)
    print("  1. Download from URL (Artist/Album/Music Video/Station)")
    print("  2. Search Catalog")
    print("  3. View Charts")
    print("  4. View Storefront Info")
    print("  5. Extract New Token (Selenium)")
    print("  6. Change Storefront")
    print("  7. Exit")
    print("=" * 60)


async def _fetch_storefront_ids(client: AsyncAppleMusicClient):
    try:
        data = await client.get("/v1/storefronts", cache_ttl=3600)
        ids = [item.get("id", "").lower() for item in data.get("data", []) if item.get("id")]
        return list(dict.fromkeys(ids))
    except Exception:
        return list(COUNTRY_CODES.keys())


async def _handle_url_download(client: AsyncAppleMusicClient, config: AMARConfig):
    url_input = input("\n  Enter Apple Music URL: ").strip()
    parsed = parse_apple_music_url(url_input)

    if not parsed:
        print("  [X] Invalid Apple Music URL.")
        return

    storefront = parsed.storefront
    item_id = parsed.item_id
    content_type = parsed.content_type

    print(f"  Detected: {content_type} | ID: {item_id} | Storefront: {storefront}")

    info_only_q = input("  Download only INFO files? (y/n): ").strip()[:1].lower()
    info_only = info_only_q == "y"

    dynamic_storefronts = await _fetch_storefront_ids(client)

    if content_type == "artist":
        rip_albums_q = input("  Rip all albums? (y/n): ").strip()[:1].lower()
        rip_videos_q = input("  Rip all music videos? (y/n): ").strip()[:1].lower()

    cc_q = input(
        f"  Country code (current: {storefront}, 'all' for every storefront, Enter to keep): "
    ).strip().lower()

    if cc_q == "all":
        rest = [c for c in dynamic_storefronts if c != storefront]
        loop_codes = [storefront] + rest
    elif cc_q in COUNTRY_CODES:
        loop_codes = [cc_q]
    else:
        loop_codes = [storefront]

    artist_ripper = ArtistRipper(client, config)
    album_ripper = AlbumRipper(client, config)
    video_ripper = MusicVideoRipper(client, config)
    station_ripper = RadioStationRipper(client, config)

    for cc in loop_codes:
        print(f"\n{'=' * 60}")
        print(f"  Storefront: {cc.upper()} - {COUNTRY_CODES.get(cc, cc).title()}")
        print(f"{'=' * 60}")

        try:
            if content_type == "artist":
                await artist_ripper.rip(item_id, cc, info_only, _log_cli)

                if rip_videos_q == "y":
                    try:
                        video_ids = await artist_ripper.get_music_video_ids(item_id, cc)
                        _log_cli(f"Found {len(video_ids)} music videos", "INFO")
                        for vid in video_ids:
                            try:
                                await video_ripper.rip(vid, cc, info_only, _log_cli)
                            except Exception as e:
                                _log_cli(f"Error downloading music video {vid}: {e}", "ERROR")
                    except TokenExpiredError:
                        raise
                    except Exception as e:
                        _log_cli(f"Error fetching music videos: {e}", "ERROR")

                if rip_albums_q == "y":
                    try:
                        album_ids = await artist_ripper.get_album_ids(item_id, cc)
                        _log_cli(f"Found {len(album_ids)} albums", "INFO")
                        for aid in album_ids:
                            try:
                                await album_ripper.rip(aid, cc, info_only, _log_cli)
                            except Exception as e:
                                _log_cli(f"Error downloading album {aid}: {e}", "ERROR")
                    except TokenExpiredError:
                        raise
                    except Exception as e:
                        _log_cli(f"Error fetching albums: {e}", "ERROR")

            elif content_type == "album":
                await album_ripper.rip(item_id, cc, info_only, _log_cli)

            elif content_type == "music-video":
                await video_ripper.rip(item_id, cc, info_only, _log_cli)

            elif content_type == "station":
                await station_ripper.rip(item_id, cc, info_only, _log_cli)

        except TokenExpiredError as e:
            print(f"\n  [X] {e}")
            print("  Please refresh your token (option 5) and try again.")
            return
        except Exception as e:
            _log_cli(f"Error processing {cc}: {e}", "ERROR")


async def _handle_search(client: AsyncAppleMusicClient, config: AMARConfig):
    query = input("\n  Enter search query: ").strip()
    if not query:
        print("  [X] Search query cannot be empty.")
        return

    print("\n  Search types:")
    print("  1. All (songs, albums, artists)")
    print("  2. Songs only")
    print("  3. Albums only")
    print("  4. Artists only")
    print("  5. Music videos")
    print("  6. Custom")

    choice = input("  Select option (1-6): ").strip()

    types_map = {
        "1": ["songs", "albums", "artists"],
        "2": ["songs"],
        "3": ["albums"],
        "4": ["artists"],
        "5": ["music-videos"],
    }

    if choice in types_map:
        types = types_map[choice]
    elif choice == "6":
        custom = input("  Enter types (comma-separated): ").strip()
        types = [t.strip() for t in custom.split(",")]
    else:
        types = ["songs", "albums", "artists"]

    print(f"\n  Searching for '{query}' in storefront {config.storefront}...")
    results = await search_catalog(client, config.storefront, query, types)
    for line in format_search_results(results):
        print(line)


async def _handle_charts(client: AsyncAppleMusicClient, config: AMARConfig):
    print("\n  Chart types:")
    print("  1. Songs")
    print("  2. Albums")
    print("  3. Both")
    print("  4. Music Videos")

    choice = input("  Select option (1-4): ").strip()

    types_map = {
        "1": ["songs"],
        "2": ["albums"],
        "3": ["songs", "albums"],
        "4": ["music-videos"],
    }

    chart_types = types_map.get(choice, ["songs", "albums"])

    print(f"\n  Fetching charts for storefront {config.storefront}...")
    charts_data = await get_charts(client, config.storefront, chart_types)
    for line in format_charts(charts_data):
        print(line)


async def _handle_storefront_info(client: AsyncAppleMusicClient, config: AMARConfig):
    try:
        data = await client.get(f"/v1/storefronts/{config.storefront}")
        if "data" in data and data["data"]:
            attrs = data["data"][0]["attributes"]
            print(f"\n  Storefront: {attrs.get('name', 'Unknown')}")
            print(f"  Language: {attrs.get('defaultLanguageTag', 'Unknown')}")
            langs = attrs.get("supportedLanguageTags", [])
            print(f"  Supported Languages: {', '.join(langs)}")
        else:
            print("  No storefront data available.")
    except Exception as e:
        print(f"  [X] Storefront error: {e}")


async def run_cli(config: AMARConfig) -> None:
    """Run the CLI menu loop."""
    # Ensure save path is set
    if not config.save_path:
        try:
            import tkinter
            import tkinter.filedialog
            root = tkinter.Tk()
            root.withdraw()
            config.save_path = tkinter.filedialog.askdirectory(title="Select save location")
            root.destroy()
            if not config.save_path:
                print("  [X] No save location selected. Exiting.")
                return
            config.save()
        except Exception:
            config.save_path = os.getcwd()
            print(f"  Using current directory: {config.save_path}")

    print(f"\n  Initializing Apple Music API Ripper...")
    print(f"  Save location: {config.save_path}")

    async with AsyncAppleMusicClient(config) as client:
        client.set_log_callback(_log_cli)

        while True:
            _print_menu()
            choice = input("\n  Select option: ").strip()

            if choice == "1":
                await _handle_url_download(client, config)
            elif choice == "2":
                await _handle_search(client, config)
            elif choice == "3":
                await _handle_charts(client, config)
            elif choice == "4":
                await _handle_storefront_info(client, config)
            elif choice == "5":
                try:
                    print("  Extracting token from Apple Music...")
                    new_token = extract_token_with_selenium(config.base_path)
                    if new_token:
                        config.save_token(new_token)
                        # Re-create the session with new headers
                        await client.close()
                        client._config = config
                        print("  [OK] Token updated successfully!")
                except RuntimeError as e:
                    print(f"  [X] {e}")
            elif choice == "6":
                print(f"\n  Current storefront: {config.storefront}")
                new_cc = input("  Enter new country code (2 letters): ").strip().lower()
                if new_cc in COUNTRY_CODES:
                    config.storefront = new_cc
                    config.save()
                    print(f"  [OK] Storefront changed to {new_cc.upper()} - {COUNTRY_CODES[new_cc]}")
                else:
                    print("  [X] Invalid country code.")
            elif choice == "7":
                print("\n  Thanks for using AMAR! Goodbye!")
                break
            else:
                print("  [X] Invalid option. Please try again.")
