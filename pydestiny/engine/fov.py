"""11x11 BFS flood-fill Field of View (0x0000:0x5a28, 0x5dfe)."""

from __future__ import annotations

from collections import deque
from typing import Callable

from pydestiny.assets.tables import SEMI_TRANSPARENT_TILES

VIEWPORT_SIZE = 11
VIEWPORT_CENTER = 5
UNSEEN_TILE = 0xFF


def is_tile_transparent(
    tile_id: int,
    dist: int,
    opaque_tiles: frozenset[int],
) -> bool:
    """Matches 0x0000:0x5dfe(dist, tile_id):
    - Semi-transparent tiles (0x4a, 0x4b, 0x98, 0xba, 0xbb) are transparent only at dist == 1.
    - Tiles in opaque_tiles (DATA.OVL+0x6a96) block further propagation.
    """
    if tile_id in SEMI_TRANSPARENT_TILES:
        return dist == 1
    return tile_id not in opaque_tiles


def compute_fov(
    get_tile: Callable[[int, int], int],
    center_x: int,
    center_y: int,
    light_radius: int,
    opaque_tiles: frozenset[int],
) -> list[list[int]]:
    """Compute the 11x11 visible tile grid centered on (center_x, center_y)."""
    grid = [[UNSEEN_TILE] * VIEWPORT_SIZE for _ in range(VIEWPORT_SIZE)]
    if light_radius <= 0:
        return grid

    origin_x = center_x - VIEWPORT_CENTER
    origin_y = center_y - VIEWPORT_CENTER

    visited = [[False] * VIEWPORT_SIZE for _ in range(VIEWPORT_SIZE)]
    queue: deque[tuple[int, int]] = deque([(VIEWPORT_CENTER, VIEWPORT_CENTER)])
    visited[VIEWPORT_CENTER][VIEWPORT_CENTER] = True

    while queue:
        vx, vy = queue.popleft()
        tile = get_tile(origin_x + vx, origin_y + vy)
        grid[vy][vx] = tile

        dx = vx - VIEWPORT_CENTER
        dy = vy - VIEWPORT_CENTER
        # Approximate integer Euclidean distance matching 0x0000:0x6ff0
        dist = int((dx * dx + dy * dy) ** 0.5)
        if dist >= light_radius:
            continue
        if (vx, vy) != (VIEWPORT_CENTER, VIEWPORT_CENTER) and not is_tile_transparent(
            tile, dist, opaque_tiles
        ):
            continue

        for nx, ny in ((vx, vy - 1), (vx, vy + 1), (vx - 1, vy), (vx + 1, vy)):
            if 0 <= nx < VIEWPORT_SIZE and 0 <= ny < VIEWPORT_SIZE and not visited[ny][nx]:
                visited[ny][nx] = True
                queue.append((nx, ny))

    return grid
