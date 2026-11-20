"""Tile passability and overworld/settlement movement rules (0x0000:0x2bd4, 0x2c2e)."""

from __future__ import annotations


def is_foot_passable(
    tile_id: int,
    foot_impassable_tiles: frozenset[int],
    actor_mode: int = 0,
) -> bool:
    """Matches 0x0000:0x2bd4(tile_id, mode):
    - Blocked if tile_id in foot_impassable_tiles (DATA.OVL+0x54d4).
    - Doors/barriers 0x90..0x93 are blocked unless (mode & 0xfe) == 0x1c or (mode & 0xf0) == 0x40.
    """
    if tile_id in foot_impassable_tiles:
        return False
    if (tile_id & 0xFC) == 0x90:
        if (actor_mode & 0xFE) != 0x1C and (actor_mode & 0xF0) != 0x40:
            return False
    return True


def is_water_passable(tile_id: int) -> bool:
    """Matches 0x0000:0x2c2e(tile_id): water (< 4) or bridge/moongate/whirlpool (0x60..0x6f)."""
    return tile_id < 4 or (tile_id & 0xF0) == 0x60


def wrap_world_coord(x: int, y: int) -> tuple[int, int]:
    """Britannia and Underworld wrap toroidally on 256x256."""
    return x & 0xFF, y & 0xFF
