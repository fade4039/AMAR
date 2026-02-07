"""Async catalog search for Apple Music API."""

from typing import Callable, Dict, List, Optional

from ..api.client import AsyncAppleMusicClient
from ..utils import convert_ms

LogCallback = Optional[Callable[[str, str], None]]


async def search_catalog(
    client: AsyncAppleMusicClient,
    storefront: str,
    query: str,
    types: Optional[List[str]] = None,
    limit: int = 25,
) -> Dict:
    """Search the Apple Music catalog.

    Args:
        client: The async API client
        storefront: Storefront code (e.g. 'us')
        query: Search query string
        types: Resource types to search. Defaults to songs, albums, artists.
        limit: Maximum results per type

    Returns:
        Raw API response dict
    """
    if types is None:
        types = ["songs", "albums", "artists"]

    params = {
        "term": query,
        "types": ",".join(types),
        "limit": limit,
    }

    return await client.get(
        f"/v1/catalog/{storefront}/search",
        params=params,
        use_cache=True,
        cache_ttl=120,
    )


def format_search_results(results: Dict) -> List[str]:
    """Format search results into display-ready lines.

    Returns a list of formatted strings.
    """
    if not results or "results" not in results:
        return ["No results found."]

    res = results["results"]
    lines = []

    # Artists
    artists = res.get("artists", {}).get("data", [])
    if artists:
        lines.append("")
        lines.append("ARTISTS:")
        for i, artist in enumerate(artists[:10], 1):
            attrs = artist.get("attributes", {})
            name = attrs.get("name", "Unknown")
            genres = ", ".join(attrs.get("genreNames", []))
            url = attrs.get("url", "")
            lines.append(f"  {i}. {name} ({genres})")
            lines.append(f"     URL: {url}")

    # Albums
    albums = res.get("albums", {}).get("data", [])
    if albums:
        lines.append("")
        lines.append("ALBUMS:")
        for i, album in enumerate(albums[:10], 1):
            attrs = album.get("attributes", {})
            name = attrs.get("name", "Unknown")
            artist = attrs.get("artistName", "Unknown")
            year = attrs.get("releaseDate", "Unknown")[:4]
            url = attrs.get("url", "")
            lines.append(f"  {i}. {name} - {artist} ({year})")
            lines.append(f"     URL: {url}")

    # Songs
    songs = res.get("songs", {}).get("data", [])
    if songs:
        lines.append("")
        lines.append("SONGS:")
        for i, song in enumerate(songs[:10], 1):
            attrs = song.get("attributes", {})
            name = attrs.get("name", "Unknown")
            artist = attrs.get("artistName", "Unknown")
            album = attrs.get("albumName", "Unknown")
            duration_ms = attrs.get("durationInMillis")
            duration = convert_ms(duration_ms) if duration_ms else "?"
            lines.append(f"  {i}. {name} - {artist}")
            lines.append(f"     Album: {album} | Duration: {duration}")

    return lines if lines else ["No results found."]
