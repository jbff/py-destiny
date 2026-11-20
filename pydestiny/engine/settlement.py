"""Settlement maps, NPC schedule resolution, and active NPC state (TOWN.OVL, NPC.OVL)."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

from pydestiny.assets.open_data import DEFAULT_DATA_DIR
from pydestiny.engine.dialogue import NpcDialogue, parse_tlk_script

SETTLEMENT_CATEGORIES: tuple[str, ...] = ("towne", "dwelling", "castle", "keep")


def settlement_category_and_index(location_id: int) -> tuple[str, int]:
    """Map location_id (1..32) to (category_name, index_0_to_7)."""
    if not 1 <= location_id <= 32:
        raise ValueError(f"Invalid settlement location_id: {location_id}")
    cat_idx = (location_id - 1) >> 3
    sub_idx = (location_id - 1) & 7
    return SETTLEMENT_CATEGORIES[cat_idx], sub_idx


def resolve_schedule_slot(times: list[int] | bytes, hour: int) -> int:
    """Resolve active schedule slot (0..2) for `hour` matching NPC.OVL+0x12e0."""
    d0 = (hour - times[0]) & 0xFF
    d1 = (hour - times[1]) & 0xFF
    d2 = (hour - times[2]) & 0xFF
    d3 = (hour - times[3]) & 0xFF

    best_val, slot = d0, 0
    if d1 < best_val:
        best_val, slot = d1, 1
    if d2 < best_val:
        best_val, slot = d2, 2
    if d3 < best_val:
        slot = 1
    return slot


@dataclass
class ActiveNpc:
    index: int
    x: int
    y: int
    z: int
    target_x: int
    target_y: int
    ai_type: int
    sprite: int
    talk_id: int


class SettlementState:
    """Loaded 32x32 settlement map, active NPCs, and dialogues."""

    def __init__(
        self,
        location_id: int,
        floors: list[list[list[int]]],
        npcs: list[ActiveNpc],
        dialogues: dict[int, NpcDialogue],
    ) -> None:
        self.location_id = location_id
        self.floors = floors
        self.npcs = npcs
        self.dialogues = dialogues

    @classmethod
    def load(
        cls,
        location_id: int,
        hour: int,
        data_dir: Path = DEFAULT_DATA_DIR,
    ) -> SettlementState:
        cat, idx = settlement_category_and_index(location_id)
        all_maps = json.loads((data_dir / "maps" / f"{cat}.json").read_text(encoding="utf-8"))
        # Each settlement can have 1 or 2 floors in the 16-map file
        floors = [all_maps[idx]]
        if idx + 8 < len(all_maps):
            floors.append(all_maps[idx + 8])

        npc_groups = json.loads((data_dir / "npcs" / f"{cat}.json").read_text(encoding="utf-8"))
        raw_npcs = npc_groups[idx]
        active: list[ActiveNpc] = []
        for n_idx, rec in enumerate(raw_npcs):
            sprite = int(rec["sprite"])
            if sprite == 0:
                continue
            slot = resolve_schedule_slot(rec["times"], hour)
            tx = int(rec["x"][slot])
            ty = int(rec["y"][slot])
            tz = int(rec["z"][slot])
            active.append(
                ActiveNpc(
                    index=n_idx,
                    x=tx,
                    y=ty,
                    z=tz,
                    target_x=tx,
                    target_y=ty,
                    ai_type=int(rec["ai_types"][slot]),
                    sprite=sprite,
                    talk_id=int(rec["talk_id"]),
                )
            )

        raw_tlk: dict[str, str] = json.loads(
            (data_dir / "dialogue" / f"{cat}.json").read_text(encoding="utf-8")
        )
        dialogues = {
            int(k): parse_tlk_script(int(k), v) for k, v in raw_tlk.items()
        }
        return cls(location_id, floors, active, dialogues)

    def get_tile(self, x: int, y: int, z: int = 0) -> int:
        floor = self.floors[z % len(self.floors)]
        if 0 <= x < 32 and 0 <= y < 32:
            return floor[y][x]
        return 0x04

    def npc_at(self, x: int, y: int, z: int = 0) -> ActiveNpc | None:
        for npc in self.npcs:
            if npc.z == z and npc.x == x and npc.y == y:
                return npc
        return None

    def step_npcs(self, is_passable_fn, rng: random.Random | None = None) -> None:
        r = rng or random
        for npc in self.npcs:
            if npc.ai_type == 0:
                continue
            if npc.x != npc.target_x or npc.y != npc.target_y:
                dx = 1 if npc.target_x > npc.x else (-1 if npc.target_x < npc.x else 0)
                dy = 1 if npc.target_y > npc.y else (-1 if npc.target_y < npc.y else 0)
            elif npc.ai_type in (2, 4):
                dx, dy = r.choice([(0, -1), (0, 1), (-1, 0), (1, 0), (0, 0), (0, 0)])
            else:
                continue
            nx, ny = npc.x + dx, npc.y + dy
            if (dx or dy) and 0 <= nx < 32 and 0 <= ny < 32:
                if is_passable_fn(self.get_tile(nx, ny, npc.z)) and not self.npc_at(nx, ny, npc.z):
                    npc.x, npc.y = nx, ny
