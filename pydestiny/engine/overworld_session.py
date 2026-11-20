"""Headless Overworld game session controller (MAINOUT.OVL behavior)."""

from __future__ import annotations

import json
from pathlib import Path

from pydestiny.assets.open_data import DEFAULT_DATA_DIR, OpenTables, load_open_grid, load_open_tables
from pydestiny.engine.dialogue import TalkSession
from pydestiny.engine.fov import compute_fov
from pydestiny.engine.karma import KARMA_LOCKPICK_SETTLEMENT, adjust_karma
from pydestiny.engine.movement import is_foot_passable, wrap_world_coord
from pydestiny.engine.settlement import SettlementState
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
        data_dir: Path = DEFAULT_DATA_DIR,
    ) -> None:
        self.save = save
        self.tables = tables
        self.brit_map = brit_map
        self.under_map = under_map
        self.look2 = look2
        self.data_dir = data_dir
        self.darkness = 0 if 5 <= save.hour < 20 else 16
        self.messages: list[str] = ["Welcome to", "Britannia!"]
        self.ztats_open = False
        self.awaiting_look_dir = False
        self.awaiting_talk_dir = False
        self.talk_session: TalkSession | None = None
        self.talk_input: str = ""
        self.quit_requested = False
        self.settlement: SettlementState | None = None
        if 1 <= save.location_id <= 32:
            self.settlement = SettlementState.load(save.location_id, save.hour, data_dir)

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

        return cls(sg, tables, brit, under, look2, data_dir=data_dir)

    @property
    def current_map(self) -> list[list[int]]:
        return self.under_map if self.save.z >= 0x80 else self.brit_map

    def get_tile(self, x: int, y: int) -> int:
        if self.settlement is not None:
            return self.settlement.get_tile(x, y, self.save.z)
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
        if self.settlement is not None:
            nx, ny = self.save.x + dx, self.save.y + dy
            if not (0 <= nx < 32 and 0 <= ny < 32):
                self.exit_settlement()
                return True
            if self.settlement.npc_at(nx, ny, self.save.z) is not None:
                self.log("Blocked!")
                return False
            tile = self.settlement.get_tile(nx, ny, self.save.z)
            if not is_foot_passable(tile, self.tables.foot_impassable_tiles):
                self.log("Blocked!")
                return False
            self.save.x = nx
            self.save.y = ny
            self.settlement.step_npcs(
                lambda t: is_foot_passable(t, self.tables.foot_impassable_tiles)
            )
            advance_time(self.save, 2, self.tables.moon_phases)
            self.darkness = update_darkness(self.darkness, self.save.hour)
            return True

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

    def enter_location(self) -> bool:
        if self.settlement is not None:
            self.log("Not here!")
            return False
        pos = (self.save.x, self.save.y)
        for idx, coord in enumerate(self.tables.location_coords[:32]):
            if coord == pos:
                loc_id = idx + 1
                self.save.location_id = loc_id
                self.save.z = 0
                self.save.x = 15
                self.save.y = 30
                self.settlement = SettlementState.load(loc_id, self.save.hour, self.data_dir)
                self.log(f"Entering loc #{loc_id}")
                return True
        self.log("Nothing to enter!")
        return False

    def exit_settlement(self) -> None:
        if self.settlement is None:
            return
        loc_id = self.settlement.location_id
        ox, oy = self.tables.location_coords[loc_id - 1]
        self.settlement = None
        self.save.location_id = 0
        self.save.z = 0
        self.save.x = ox
        self.save.y = oy
        self.log("Exiting to Britannia")

    def start_talk(self, dx: int, dy: int) -> bool:
        if self.settlement is None:
            self.log("No one here!")
            return False
        npc = self.settlement.npc_at(self.save.x + dx, self.save.y + dy, self.save.z)
        if npc is None or npc.talk_id == 0 or npc.talk_id == 0xFF:
            self.log("No response!")
            return False
        if npc.talk_id >= 0x80:
            self.log("Shopkeeper busy.")
            return False
        dlg = self.settlement.dialogues.get(npc.talk_id)
        if dlg is None:
            self.log("No response!")
            return False
        avatar_name = self.save.characters[0].name or "Avatar"
        self.talk_session = TalkSession(dlg, avatar_name)
        self.talk_input = ""
        self.log(self.talk_session.opening())
        return True

    def submit_talk(self, keyword: str) -> str:
        if self.talk_session is None:
            return ""
        resp = self.talk_session.ask(keyword)
        if resp:
            self.log(resp)
        if self.talk_session.finished:
            self.talk_session = None
        self.talk_input = ""
        return resp

    def jimmy_door(self, dx: int, dy: int) -> bool:
        if self.settlement is None:
            return False
        tx, ty = self.save.x + dx, self.save.y + dy
        tile = self.settlement.get_tile(tx, ty, self.save.z)
        if tile in (0xB8, 0xB9, 0x97):  # locked door
            if self.save.keys <= 0:
                self.log("No keys!")
                return False
            self.save.keys -= 1
            adjust_karma(self.save, KARMA_LOCKPICK_SETTLEMENT)
            self.settlement.floors[self.save.z % len(self.settlement.floors)][ty][tx] = 0x44
            self.log("Unlocked!")
            return True
        self.log("Not locked!")
        return False

    def pass_turn(self) -> None:
        self.log("Pass")
        advance_time(self.save, 2, self.tables.moon_phases)
        self.darkness = update_darkness(self.darkness, self.save.hour)

    def look_at(self, dx: int, dy: int) -> str:
        tile = self.get_tile(self.save.x + dx, self.save.y + dy)
        desc = self.look2[tile] if 0 <= tile < len(self.look2) else f"Tile {tile}"
        self.log(f"Thou dost see {desc}")
        return desc
