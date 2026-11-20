#!/usr/bin/env python3
"""Dump core Ultima V game tables from DATA.OVL (monsters, spells, tile passability)."""

from __future__ import annotations

from pathlib import Path

ORIG_DIR = Path(__file__).resolve().parent.parent / "orig" / "extracted"

REAGENTS = ["Ash", "Ginseng", "Garlic", "Silk", "Moss", "Pearl", "Nightshade", "Mandrake"]


def read_cstrings(data: bytes, offset: int, count: int) -> list[str]:
    out = []
    p = offset
    for _ in range(count):
        end = data.find(b"\x00", p)
        out.append(data[p:end].decode("ascii", errors="replace"))
        p = end + 1
    return out


def dump_spells(data: bytes) -> None:
    spells = read_cstrings(data, 0x0709, 48)
    masks = data[0x1CD0 : 0x1CD0 + 48]
    print("=== 48 Spells & Reagent Recipes ===")
    for i, (name, mask) in enumerate(zip(spells, masks)):
        circle = (i // 6) + 1
        reqs = [r for bit, r in enumerate(REAGENTS) if mask & (0x80 >> bit)]
        print(f"  [{i:2d}] C{circle} {name:<14s} (0x{mask:02x}): {', '.join(reqs)}")


def dump_monsters(data: bytes) -> None:
    # 48 records x 8 bytes at DATA.OVL+0x13cc (0..15 NPC/human classes, 16..47 monsters)
    # Monster names at 0x023e (32 monsters starting at Sea Horse..Shadow Lord)
    monster_names = read_cstrings(data, 0x023E, 32)
    print("\n=== Monster / Actor Stat Table (DATA.OVL+0x13cc, 48 x 8B) ===")
    print("Idx Name             STR DEX INT ARM DMG  HP Max Spc")
    for i in range(48):
        rec = data[0x13CC + i * 8 : 0x13CC + (i + 1) * 8]
        name = monster_names[i - 16] if i >= 16 else f"Class_{i:02d}"
        s, d, iq, arm, dmg, hp, mx, spc = rec
        print(f"{i:3d} {name:<16s} {s:3d} {d:3d} {iq:3d} {arm:3d} {dmg:3d} {hp:3d} {mx:3d} {spc:3d}")


def dump_tile_passability(data: bytes) -> None:
    mask = data[0x54E4 : 0x54E4 + 32]
    blocked = [tid for tid in range(256) if mask[tid >> 3] & (0x80 >> (tid & 7))]
    print(f"\n=== Foot-Impassable Tiles (DATA.OVL+0x54e4, {len(blocked)}/256 blocked) ===")
    print(" ", " ".join(f"{t:02x}" for t in blocked))


def main() -> None:
    data = (ORIG_DIR / "DATA.OVL").read_bytes()
    dump_spells(data)
    dump_monsters(data)
    dump_tile_passability(data)


if __name__ == "__main__":
    main()
