"""World, settlement, dungeon, NPC schedule, and combat map loaders."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CombatMap:
    tiles: tuple[bytes, ...]  # 11 rows x 11 bytes
    party_start_x: bytes      # 6 bytes (row 4 cols 11..16)
    monster_types: bytes      # 16 bytes (row 5 cols 11..26)
    monster_x: bytes          # 16 bytes (row 6 cols 11..26)
    monster_y: bytes          # 16 bytes (row 7 cols 11..26)


@dataclass(frozen=True)
class NpcSchedule:
    ai_types: bytes  # 3 bytes
    x: bytes         # 3 bytes
    y: bytes         # 3 bytes
    z: bytes         # 3 bytes
    times: bytes     # 4 bytes
    sprite: int
    talk_id: int


def load_brit_map(brit_path: Path, chunk_map: bytes) -> list[bytes]:
    """Load BRIT.DAT + DATA.OVL chunk map -> 256 rows x 256 bytes."""
    raw = brit_path.read_bytes()
    grid = [bytearray(256) for _ in range(256)]
    for cy in range(16):
        for cx in range(16):
            cidx = chunk_map[cy * 16 + cx]
            if cidx == 0xFF:
                for y in range(16):
                    grid[cy * 16 + y][cx * 16 : (cx + 1) * 16] = b"\x01" * 16
            else:
                chunk = raw[cidx * 256 : (cidx + 1) * 256]
                for y in range(16):
                    grid[cy * 16 + y][cx * 16 : (cx + 1) * 16] = chunk[y * 16 : (y + 1) * 16]
    return [bytes(r) for r in grid]


def load_under_map(under_path: Path) -> list[bytes]:
    """Load UNDER.DAT -> 256 rows x 256 bytes."""
    raw = under_path.read_bytes()
    if len(raw) != 65536:
        raise ValueError(f"Expected 65536 bytes for UNDER.DAT, got {len(raw)}")
    return [raw[y * 256 : (y + 1) * 256] for y in range(256)]


def load_settlement_maps(dat_path: Path) -> list[list[bytes]]:
    """Load CASTLE/TOWNE/KEEP/DWELLING.DAT -> 16 maps x 32 rows x 32 bytes."""
    raw = dat_path.read_bytes()
    if len(raw) != 16384:
        raise ValueError(f"Expected 16384 bytes for {dat_path.name}, got {len(raw)}")
    maps: list[list[bytes]] = []
    for m in range(16):
        chunk = raw[m * 1024 : (m + 1) * 1024]
        maps.append([chunk[y * 32 : (y + 1) * 32] for y in range(32)])
    return maps


def load_dungeon_maps(dng_path: Path) -> list[list[list[bytes]]]:
    """Load DUNGEON.DAT -> 8 dungeons x 8 levels x 8 rows x 8 bytes."""
    raw = dng_path.read_bytes()
    if len(raw) != 4096:
        raise ValueError(f"Expected 4096 bytes for DUNGEON.DAT, got {len(raw)}")
    dungeons: list[list[list[bytes]]] = []
    for d in range(8):
        levels: list[list[bytes]] = []
        for lvl in range(8):
            base = (d * 8 + lvl) * 64
            levels.append([raw[base + y * 8 : base + (y + 1) * 8] for y in range(8)])
        dungeons.append(levels)
    return dungeons


def load_combat_maps(cbt_path: Path) -> list[CombatMap]:
    """Load BRIT.CBT or DUNGEON.CBT (352 bytes = 11 rows x 32 bytes per map)."""
    raw = cbt_path.read_bytes()
    if len(raw) % 352 != 0:
        raise ValueError(f"{cbt_path.name} size {len(raw)} is not a multiple of 352")
    count = len(raw) // 352
    out: list[CombatMap] = []
    for i in range(count):
        rec = raw[i * 352 : (i + 1) * 352]
        rows = [rec[r * 32 : (r + 1) * 32] for r in range(11)]
        out.append(
            CombatMap(
                tiles=tuple(r[:11] for r in rows),
                party_start_x=rows[4][11:17],
                monster_types=rows[5][11:27],
                monster_x=rows[6][11:27],
                monster_y=rows[7][11:27],
            )
        )
    return out


def load_npc_schedules(npc_path: Path) -> list[list[NpcSchedule]]:
    """Load CASTLE/TOWNE/KEEP/DWELLING.NPC -> 8 settlements x 32 NpcSchedule."""
    raw = npc_path.read_bytes()
    if len(raw) != 4608:
        raise ValueError(f"Expected 4608 bytes for {npc_path.name}, got {len(raw)}")
    settlements: list[list[NpcSchedule]] = []
    for s in range(8):
        block = raw[s * 576 : (s + 1) * 576]
        npcs: list[NpcSchedule] = []
        for n in range(32):
            rec = block[n * 16 : (n + 1) * 16]
            npcs.append(
                NpcSchedule(
                    ai_types=rec[0:3],
                    x=rec[3:6],
                    y=rec[6:9],
                    z=rec[9:12],
                    times=rec[12:16],
                    sprite=block[0x200 + n],
                    talk_id=block[0x220 + n],
                )
            )
        settlements.append(npcs)
    return settlements
