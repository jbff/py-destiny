"""Headless Overworld game session controller (MAINOUT.OVL behavior)."""

from __future__ import annotations

import json
from pathlib import Path

from pydestiny.assets.open_data import DEFAULT_DATA_DIR, OpenTables, load_open_grid, load_open_tables
from pydestiny.engine.fov import compute_fov
from pydestiny.engine.movement import is_foot_passable, wrap_world_coord
from pydestiny.engine.time import advance_time, get_moon_phases, update_darkness
from pydestiny.state.savegame import SaveGame

AVATAR_TILE_ID = 284  # 0x11c: Avatar on foot in TILES.16


class OverworldSession:
    """Testable, UI-independent Overworld state & turn controller."""

    def __init__(
        self,
        save: SaveGame,
        tables: OpenTables,
        brit_map: list[list[int]],
        under_map: list[list[int]],
        look2: list[str],
    ) -> None:
        self.save = save
        self.tables = tables
        self.brit_map = brit_map
        self.under_map = under_map
        self.look2 = look2
        self.darkness = 0 if 5 <= save.hour < 20 else 16
        self.messages: list[str] = ["Welcome to", "Britannia!"]
        self.ztats_open = False
        self.awaiting_look_dir = False
        self.quit_requested = False

    @classmethod
    def from_data_dir(
        cls,
        data_dir: Path = DEFAULT_DATA_DIR,
        save_path: Path | None = None,
    ) -> OverworldSession:
        tables = load_open_tables(data_dir)
        brit = load_open_grid(data_dir / "maps" / "brit.json")
        under = load_open_grid(data_dir / "maps" / "under.json")
        look2 = json.loads((data_dir / "text" / "look2.json").read_text(encoding="utf-8"))

        if save_path and save_path.exists():
            sg = SaveGame.load_json(save_path)
        else:
            sg = SaveGame.load_json(data_dir / "init_save.json")
            # Place on Britannia overworld outside Iolo's hut if starting fresh overworld
            if sg.location_id != 0:
                sg.location_id = 0
                sg.z = 0
                sg.x = 74
                sg.y = 95

        return cls(sg, tables, brit, under, look2)

    @property
    def current_map(self) -> list[list[int]]:
        return self.under_map if self.save.z >= 0x80 else self.brit_map

    def get_tile(self, x: int, y: int) -> int:
        wx, wy = wrap_world_coord(x, y)
        return self.current_map[wy][wx]

    def log(self, msg: str) -> None:
        # Wrap to 16-char lines for the 320x200 right-hand log panel
        words = msg.split()
        line = ""
        for w in words:
            if not line:
                line = w
            elif len(line) + 1 + len(w) <= 16:
                line = f"{line} {w}"
            else:
                self.messages.append(line)
                line = w
        if line:
            self.messages.append(line)
        self.messages = self.messages[-40:]

    def light_radius(self) -> int:
        return max(1, 5 - (self.darkness // 4))

    def get_viewport_fov(self) -> list[list[int]]:
        return compute_fov(
            self.get_tile,
            self.save.x,
            self.save.y,
            self.light_radius(),
            self.tables.opaque_tiles,
        )

    def moon_phases(self) -> tuple[int, int]:
        return get_moon_phases(self.save.day, self.tables.moon_phases)

    def step_move(self, dx: int, dy: int) -> bool:
        nx, ny = wrap_world_coord(self.save.x + dx, self.save.y + dy)
        tile = self.get_tile(nx, ny)
        if not is_foot_passable(tile, self.tables.foot_impassable_tiles):
            self.log("Blocked!")
            return False
        self.save.x = nx
        self.save.y = ny
        advance_time(self.save, 2, self.tables.moon_phases)
        self.darkness = update_darkness(self.darkness, self.save.hour)
        return True

    def pass_turn(self) -> None:
        self.log("Pass")
        advance_time(self.save, 2, self.tables.moon_phases)
        self.darkness = update_darkness(self.darkness, self.save.hour)

    def look_at(self, dx: int, dy: int) -> str:
        tile = self.get_tile(self.save.x + dx, self.save.y + dy)
        desc = self.look2[tile] if 0 <= tile < len(self.look2) else f"Tile {tile}"
        self.log(f"Thou dost see {desc}")
        return desc
