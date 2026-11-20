"""Headless Overworld game session controller (MAINOUT.OVL behavior)."""

from __future__ import annotations

import json
from pathlib import Path

from pydestiny.assets.open_data import DEFAULT_DATA_DIR, OpenTables, load_open_grid, load_open_tables
from pydestiny.engine.combat_session import CombatSession
from pydestiny.engine.dialogue import TalkSession
from pydestiny.engine.dungeon_session import DungeonSession
from pydestiny.engine.fov import compute_fov
from pydestiny.engine.karma import KARMA_LOCKPICK_SETTLEMENT, adjust_karma
from pydestiny.engine.magic_effects import execute_spell
from pydestiny.engine.movement import is_foot_passable, wrap_world_coord
from pydestiny.engine.settlement import SettlementState
from pydestiny.engine.shoppes import buy_shop_item, get_shop_menu
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
        self.awaiting_attack_dir = False
        self.awaiting_jimmy_dir = False
        self.awaiting_open_dir = False
        self.awaiting_search_dir = False
        self.shop_open = False
        self.shop_talk_id = 0
        self.shop_title = "SHOPPE MENU"
        self.combat: CombatSession | None = None
        self.talk_session: TalkSession | None = None
        self.talk_input: str = ""
        self.quit_requested = False
        self.settlement: SettlementState | None = None
        self.dungeon: DungeonSession | None = None
        if 1 <= save.location_id <= 32:
            base_idx = tables.settlement_base_maps[save.location_id - 1]
            self.settlement = SettlementState.load(
                save.location_id, save.hour, base_idx, data_dir
            )
        elif 33 <= save.location_id <= 40:
            self.dungeon = DungeonSession.load(save.location_id - 33, data_dir)
            self.dungeon.x = save.x
            self.dungeon.y = save.y
            self.dungeon.z = save.z

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
        if self.dungeon is not None:
            if dx < 0:
                self.dungeon.turn_left()
                return True
            if dx > 0:
                self.dungeon.turn_right()
                return True
            moved, event = self.dungeon.step(forward=(dy < 0))
            if not moved:
                self.log("Blocked!")
                return False
            self.save.x = self.dungeon.x
            self.save.y = self.dungeon.y
            self.save.z = self.dungeon.z
            advance_time(self.save, 2, self.tables.moon_phases)
            if event.startswith("room:"):
                room_id = int(event.split(":", 1)[1])
                self.start_dungeon_room(room_id)
            elif event == "pit":
                self.log("A pit!")
            elif event == "chest":
                self.log("A chest!")
            elif event == "fountain":
                self.log("A fountain!")
            return True

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
        if self.settlement is not None or self.dungeon is not None:
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
                base_idx = self.tables.settlement_base_maps[loc_id - 1]
                self.settlement = SettlementState.load(
                    loc_id, self.save.hour, base_idx, self.data_dir
                )
                self.log(f"Entering loc #{loc_id}")
                return True
        for dng_idx, coord in enumerate(self.tables.location_coords[32:40]):
            if (dng_idx == 7 and self.save.z < 0x80) or (dng_idx < 7 and self.save.z >= 0x80):
                continue
            if coord == pos:
                self.dungeon = DungeonSession.load(dng_idx, self.data_dir)
                self.save.location_id = 33 + dng_idx
                self.save.x = self.dungeon.x
                self.save.y = self.dungeon.y
                self.save.z = 0
                self.log(f"Entering {self.dungeon.name}")
                return True
        self.log("Nothing to enter!")
        return False

    def exit_dungeon(self) -> None:
        if self.dungeon is None:
            return
        dng_idx = self.dungeon.dungeon_idx
        ox, oy = self.tables.location_coords[32 + dng_idx]
        self.dungeon = None
        self.save.location_id = 0
        self.save.z = 0
        self.save.x = ox
        self.save.y = oy
        self.log("Exiting to Britannia")

    def klimb_dungeon(self, up: bool = True) -> bool:
        if self.dungeon is None:
            return False
        res = self.dungeon.klimb(up=up)
        if res == "exit":
            self.exit_dungeon()
            return True
        if res in ("up", "down"):
            self.save.z = self.dungeon.z
            self.log(f"Level {self.dungeon.z + 1}")
            return True
        self.log("Not here!")
        return False

    def start_dungeon_room(self, room_id: int) -> CombatSession:
        cbt_maps = json.loads(
            (self.data_dir / "maps" / "dungeon_cbt.json").read_text(encoding="utf-8")
        )
        dng_idx = self.dungeon.dungeon_idx if self.dungeon is not None else 0
        cbt_idx = min(dng_idx * 16 + room_id, len(cbt_maps) - 1)
        self.combat = CombatSession.from_cbt_dict(
            self.save, self.tables, cbt_maps[cbt_idx], default_monster_idx=32
        )
        self.log(f"Dungeon room {room_id}!")
        return self.combat

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
        if npc is None or npc.talk_id == 0:
            self.log("No response!")
            return False
        if npc.talk_id == 0xFF:
            self.log("Guard: Move along!")
            return False
        if npc.talk_id >= 0x80:
            self.shop_talk_id = npc.talk_id
            self.shop_title, _ = get_shop_menu(npc.talk_id)
            self.shop_open = True
            self.log(f"Welcome to {self.shop_title}!")
            return True
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
            self.settlement.current_floor(self.save.z)[ty][tx] = 0x44
            self.log("Unlocked!")
            return True
        self.log("Not locked!")
        return False

    def start_combat(self, cbt_index: int = 2, monster_idx: int = 32) -> CombatSession:
        cbt_list = json.loads((self.data_dir / "maps" / "brit_cbt.json").read_text(encoding="utf-8"))
        cbt_data = cbt_list[cbt_index % len(cbt_list)]
        self.combat = CombatSession.from_cbt_dict(
            self.save, self.tables, cbt_data, default_monster_idx=monster_idx
        )
        self.log("Combat!")
        return self.combat

    def finish_combat_if_done(self) -> None:
        if self.combat is not None and self.combat.finished:
            for m in self.combat.messages[-2:]:
                self.log(m)
            self.combat = None

    def klimb_settlement(self, up: bool = True) -> bool:
        if self.settlement is None:
            return False
        tile = self.settlement.get_tile(self.save.x, self.save.y, self.save.z)
        if tile not in (0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9):
            self.log("Not here!")
            return False
        if tile == 0xC8 and not up:
            self.log("Up only!")
            return False
        if tile == 0xC9 and up:
            self.log("Down only!")
            return False
        signed_z = self.save.z - 256 if self.save.z >= 0x80 else self.save.z
        new_z = signed_z + (1 if up else -1)
        new_map_idx = self.settlement.base_map_idx + new_z
        if not 0 <= new_map_idx < len(self.settlement.all_maps):
            self.log("Blocked!")
            return False
        self.save.z = new_z & 0xFF
        self.log(f"Floor {new_z}")
        return True

    def open_at(self, dx: int, dy: int) -> bool:
        if self.settlement is None:
            self.log("Nothing to open!")
            return False
        tx, ty = self.save.x + dx, self.save.y + dy
        tile = self.settlement.get_tile(tx, ty, self.save.z)
        if tile in (0xB4, 0xB5, 0xB6, 0xB7):  # unlocked door
            self.settlement.current_floor(self.save.z)[ty][tx] = 0x44
            self.log("Opened!")
            return True
        if tile == 0x8F:  # chest
            self.settlement.current_floor(self.save.z)[ty][tx] = 0x44
            self.save.gold += 15
            self.log("Found 15 gold!")
            return True
        if tile in (0xB8, 0xB9, 0x97):
            self.log("Locked!")
            return False
        self.log("Nothing to open!")
        return False

    def search_at(self, dx: int, dy: int) -> str:
        desc = self.look_at(dx, dy)
        return desc

    def shop_buy(self, slot_idx: int) -> tuple[bool, str]:
        _, items = get_shop_menu(self.shop_talk_id)
        if not 0 <= slot_idx < len(items):
            return False, "Invalid choice"
        ok, msg = buy_shop_item(self.save, items[slot_idx])
        self.log(msg)
        return ok, msg

    def cast_spell_quick(self, caster_idx: int, spell_idx: int) -> tuple[bool, str]:
        ok, msg = execute_spell(
            self.save,
            self.tables,
            caster_idx,
            spell_idx,
            in_combat=(self.combat is not None),
            combat_session=self.combat,
        )
        self.log(msg)
        if ok and spell_idx in (0, 12):  # Light spells
            self.darkness = 0
        return ok, msg

    def pass_turn(self) -> None:
        self.log("Pass")
        advance_time(self.save, 2, self.tables.moon_phases)
        self.darkness = update_darkness(self.darkness, self.save.hour)

    def look_at(self, dx: int, dy: int) -> str:
        tile = self.get_tile(self.save.x + dx, self.save.y + dy)
        desc = self.look2[tile] if 0 <= tile < len(self.look2) else f"Tile {tile}"
        self.log(f"Thou dost see {desc}")
        return desc
