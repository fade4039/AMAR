"""Async charts fetching for Apple Music API."""

from typing import Callable, Dict, List, Optional

from ..api.client import AsyncAppleMusicClient

LogCallback = Optional[Callable[[str, str], None]]


async def get_charts(
    client: AsyncAppleMusicClient,
    storefront: str,
    chart_types: Optional[List[str]] = None,
    limit: int = 20,
) -> Dict:
    """Fetch Apple Music charts.

    Args:
        client: The async API client
        storefront: Storefront code (e.g. 'us')
        chart_types: Types of charts. Defaults to songs and albums.
        limit: Maximum results per chart

    Returns:
        Raw API response dict
    """
    if chart_types is None:
        chart_types = ["songs", "albums"]

    params = {
        "types": ",".join(chart_types),
        "limit": limit,
    }

    return await client.get(
        f"/v1/catalog/{storefront}/charts",
        params=params,
        use_cache=True,
        cache_ttl=300,
    )


def format_charts(charts_data: Dict) -> List[str]:
    """Format charts data into display-ready lines.

    Returns a list of formatted strings.
    """
    if not charts_data or "results" not in charts_data:
        return ["No charts data available."]

    results = charts_data["results"]
    lines = []

    # Songs chart
    songs_charts = results.get("songs", [])
    if songs_charts:
        lines.append("")
        lines.append("TOP SONGS:")
        for chart in songs_charts:
            for i, song in enumerate(chart.get("data", [])[:20], 1):
                attrs = song.get("attributes", {})
                name = attrs.get("name", "Unknown")
                artist = attrs.get("artistName", "Unknown")
                lines.append(f"  {i:2d}. {name} - {artist}")

    # Albums chart
    albums_charts = results.get("albums", [])
    if albums_charts:
        lines.append("")
        lines.append("TOP ALBUMS:")
        for chart in albums_charts:
            for i, album in enumerate(chart.get("data", [])[:20], 1):
                attrs = album.get("attributes", {})
                name = attrs.get("name", "Unknown")
                artist = attrs.get("artistName", "Unknown")
                lines.append(f"  {i:2d}. {name} - {artist}")

    return lines if lines else ["No charts data available."]
