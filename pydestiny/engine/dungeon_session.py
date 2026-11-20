"""3D Dungeon state & navigation (8x8x8 grid, facing N/E/S/W, ladders, rooms)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pydestiny.assets.open_data import DEFAULT_DATA_DIR

DUNGEON_NAMES: tuple[str, ...] = (
    "Deceit",
    "Despise",
    "Destard",
    "Wrong",
    "Covetous",
    "Shame",
    "Hythloth",
    "Doom",
)

# Maps dungeon_idx (0..7) to DNG1 (cave), DNG2 (brick), or DNG3 (stone)
DUNGEON_STYLES: tuple[int, ...] = (2, 1, 3, 2, 1, 3, 3, 3)

FACING_DIRS: tuple[tuple[int, int], ...] = (
    (0, -1),  # 0: North
    (1, 0),   # 1: East
    (0, 1),   # 2: South
    (-1, 0),  # 3: West
)
FACING_NAMES: tuple[str, ...] = ("North", "East", "South", "West")


def is_wall_cell(cell: int) -> bool:
    """Return True if dungeon cell is solid rock/wall (0xB0..0xBF)."""
    return (cell & 0xF0) == 0xB0


def is_door_cell(cell: int) -> bool:
    """Return True if dungeon cell is a door or room entrance (0xC0..0xFF)."""
    return (cell & 0xF0) >= 0xC0


def is_opaque_dungeon_cell(cell: int) -> bool:
    """Return True if cell blocks line-of-sight in 3D view (walls & doors)."""
    return (cell & 0xF0) >= 0xB0


@dataclass
class DungeonSession:
    """Active 3D dungeon exploration state."""

    dungeon_idx: int  # 0..7
    grid: list[list[list[int]]]  # 8 levels x 8 rows x 8 cols
    x: int
    y: int
    z: int = 0
    facing: int = 2  # 0=N, 1=E, 2=S, 3=W

    @property
    def name(self) -> str:
        return DUNGEON_NAMES[self.dungeon_idx]

    @property
    def style(self) -> int:
        return DUNGEON_STYLES[self.dungeon_idx]

    @classmethod
    def load(
        cls,
        dungeon_idx: int,
        data_dir: Path = DEFAULT_DATA_DIR,
    ) -> DungeonSession:
        all_dng: list[list[list[list[int]]]] = json.loads(
            (data_dir / "maps" / "dungeon.json").read_text(encoding="utf-8")
        )
        grid = all_dng[dungeon_idx]
        # Spawn at ladder up (0x10) on level 0 if present, else (1, 1)
        sx, sy = 1, 1
        for ry in range(8):
            for rx in range(8):
                if (grid[0][ry][rx] & 0xF0) == 0x10:
                    sx, sy = rx, ry
                    break
            else:
                continue
            break
        # Face an adjacent open cell if possible
        facing = 2
        for f_idx, (dx, dy) in enumerate(FACING_DIRS):
            nx, ny = (sx + dx) % 8, (sy + dy) % 8
            if not is_wall_cell(grid[0][ny][nx]):
                facing = f_idx
                break
        return cls(dungeon_idx=dungeon_idx, grid=grid, x=sx, y=sy, z=0, facing=facing)

    def cell_at(self, x: int, y: int, z: int | None = None) -> int:
        lvl = self.z if z is None else z
        return self.grid[lvl][y % 8][x % 8]

    def current_cell(self) -> int:
        return self.cell_at(self.x, self.y, self.z)

    def turn_left(self) -> None:
        self.facing = (self.facing - 1) % 4

    def turn_right(self) -> None:
        self.facing = (self.facing + 1) % 4

    def turn_around(self) -> None:
        self.facing = (self.facing + 2) % 4

    def step(self, forward: bool = True) -> tuple[bool, str]:
        """Move forward or backward in facing direction. Returns (moved, event)."""
        dx, dy = FACING_DIRS[self.facing]
        if not forward:
            dx, dy = -dx, -dy
        nx = (self.x + dx) % 8
        ny = (self.y + dy) % 8
        target = self.cell_at(nx, ny)
        if is_wall_cell(target):
            return False, "Blocked!"
        self.x, self.y = nx, ny
        hi = target & 0xF0
        if hi == 0xF0:
            return True, f"room:{target & 0x0F}"
        if hi == 0x60:
            return True, "pit"
        if hi == 0x40:
            return True, "chest"
        if hi == 0x50:
            return True, "fountain"
        return True, "ok"

    def klimb(self, up: bool = True) -> str:
        """Climb ladder up or down. Returns 'exit', 'up', 'down', or 'none'."""
        hi = self.current_cell() & 0xF0
        if up and hi in (0x10, 0x30):
            if self.z == 0:
                return "exit"
            self.z -= 1
            return "up"
        if not up and hi in (0x20, 0x30):
            if self.z < 7:
                self.z += 1
                return "down"
        return "none"

    def view_slices(self, max_depth: int = 3) -> list[tuple[int, int, int, int]]:
        """Return [(depth, left_cell, center_cell, right_cell)] for depth 0..max_depth."""
        fx, fy = FACING_DIRS[self.facing]
        # Right vector is 90 deg clockwise: (-fy, fx)
        rx, ry = -fy, fx
        out: list[tuple[int, int, int, int]] = []
        for d in range(max_depth + 1):
            cx = (self.x + fx * d) % 8
            cy = (self.y + fy * d) % 8
            left_c = self.cell_at(cx - rx, cy - ry)
            center_c = self.cell_at(cx, cy)
            right_c = self.cell_at(cx + rx, cy + ry)
            out.append((d, left_c, center_c, right_c))
        return out
