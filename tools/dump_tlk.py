#!/usr/bin/env python3
"""Decode and dump Ultima V .TLK dialogue files using the DATA.OVL word table."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

ORIG_DIR = Path(__file__).resolve().parent.parent / "orig" / "extracted"

# In DATA.OVL, the word-pointer table starts at 0x24f8 and each string pointer
# requires +0x10 to align with the string pool at 0x104c+.
WORD_TABLE_OFFSET = 0x24F8
STRING_POOL_SHIFT = 0x10


def load_word_table(data_ovl: bytes) -> dict[int, str]:
    words: dict[int, str] = {}
    for i in range(1, 128):
        ptr = struct.unpack_from("<H", data_ovl, WORD_TABLE_OFFSET + i * 2)[0]
        if ptr == 0xFFFF or ptr < 0x1000 or ptr > 0x2400:
            continue
        p = ptr + STRING_POOL_SHIFT
        end = data_ovl.find(b"\x00", p)
        words[i] = data_ovl[p:end].decode("ascii", errors="replace")
    return words


def decode_tlk_entry(tlk: bytes, start: int, end_limit: int, words: dict[int, str]) -> str:
    out: list[str] = []
    p = start
    while p < end_limit:
        b = tlk[p]
        p += 1
        if b == 0x00:
            out.append("\n  | ")
        elif b >= 0x80:
            c = b & 0x7F
            if b == 0x81:
                out.append("<AVATAR>")
            elif b == 0x82:
                out.append("<END>")
            elif b == 0x83:
                out.append("<PAUSE>")
            elif b == 0x87:
                out.append(" / ")
            elif b == 0x8D or c == 0x0D:
                out.append("\n")
            elif 0x20 <= c < 0x7F:
                out.append(chr(c))
            else:
                out.append(f"<{b:#04x}>")
        else:
            w = words.get(b, f"[w{b}]")
            if out and out[-1] and not out[-1].endswith((" ", "\n", '"', "(")):
                out.append(" ")
            out.append(w)
            # Peek next byte: if it's a letter/digit with high bit set, add space
            if p < end_limit and tlk[p] >= 0x80:
                nc = tlk[p] & 0x7F
                if chr(nc).isalnum() or nc in (ord('"'), ord("(")):
                    out.append(" ")
    return "".join(out).strip()


def dump_tlk(tlk_path: Path, data_ovl: bytes, limit: int | None = None) -> None:
    words = load_word_table(data_ovl)
    tlk = tlk_path.read_bytes()
    count = struct.unpack_from("<H", tlk, 0)[0]
    entries = [struct.unpack_from("<HH", tlk, 2 + i * 4) for i in range(count)]

    print(f"=== {tlk_path.name} ({count} NPCs) ===")
    for idx, (npc_id, off) in enumerate(entries[:limit]):
        next_off = entries[idx + 1][1] if idx + 1 < len(entries) else len(tlk)
        text = decode_tlk_entry(tlk, off, next_off, words)
        print(f"\n[NPC #{npc_id} @ {off:#06x}]")
        print(f"  {text}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Dump Ultima V .TLK dialogue files.")
    parser.add_argument("tlk", type=Path, help="Path to .TLK file (e.g. orig/extracted/TOWNE.TLK)")
    parser.add_argument("-n", "--limit", type=int, default=None, help="Limit number of NPCs printed")
    args = parser.parse_args()

    data_ovl = (ORIG_DIR / "DATA.OVL").read_bytes()
    dump_tlk(args.tlk, data_ovl, args.limit)


if __name__ == "__main__":
    main()
