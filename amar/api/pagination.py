"""Async iterative pagination for Apple Music API."""

from typing import AsyncIterator, Dict, List, Optional

from .client import AsyncAppleMusicClient


async def paginate_all(
    client: AsyncAppleMusicClient,
    initial_path: str,
    params: Optional[Dict] = None,
) -> AsyncIterator[Dict]:
    """Iteratively fetch all pages from a paginated endpoint.

    Yields each item from the 'data' array across all pages.
    Uses the 'next' field in responses to follow pagination links.
    """
    path = initial_path
    current_params = params

    while path:
        response = await client.get(path, params=current_params, use_cache=False)
        current_params = None  # 'next' URLs include their own params

        for item in response.get("data", []):
            yield item

        path = response.get("next")


async def collect_all_ids(
    client: AsyncAppleMusicClient,
    artist_id: str,
    storefront: str,
    resource_type: str,
) -> List[str]:
    """Collect all resource IDs (albums, music-videos) for an artist.

    Args:
        client: The API client
        artist_id: Apple Music artist ID
        storefront: Storefront code (e.g. 'us')
        resource_type: 'albums' or 'music-videos'

    Returns:
        List of resource IDs
    """
    path = f"/v1/catalog/{storefront}/artists/{artist_id}/{resource_type}"
    ids = []

    async for item in paginate_all(client, path):
        ids.append(item["id"])

    return ids
