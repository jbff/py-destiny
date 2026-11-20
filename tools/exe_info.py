#!/usr/bin/env python3
"""Inspect ULTIMA.EXE MZ header, Plink86 overlay table, and cross-overlay thunks."""

from __future__ import annotations

import os
import struct
from pathlib import Path

ORIG_DIR = Path(__file__).resolve().parent.parent / "orig" / "extracted"
EXE_PATH = ORIG_DIR / "ULTIMA.EXE"

PLINK_TABLE_OFFSET = 0x7780
PLINK_THUNK_SIG = b"\x9a\xec\x02\x2e\x07"


def parse_mz_header(data: bytes) -> dict[str, int]:
    fields = struct.unpack("<2s13H", data[:28])
    magic, last_pg, pages, relocs, hdr_para, min_alloc, max_alloc, ss, sp, csum, ip, cs, reloc_off, ovl = fields
    if magic != b"MZ":
        raise ValueError(f"Not an MZ executable: {magic!r}")
    exe_size = (pages - 1) * 512 + last_pg if last_pg else pages * 512
    return {
        "exe_size": exe_size,
        "hdr_bytes": hdr_para * 16,
        "relocs": relocs,
        "min_alloc": min_alloc,
        "max_alloc": max_alloc,
        "ss": ss,
        "sp": sp,
        "cs": cs,
        "ip": ip,
        "reloc_off": reloc_off,
    }


def parse_plink_overlays(img: bytes) -> list[dict[str, object]]:
    overlays = []
    for i in range(64):
        entry = img[PLINK_TABLE_OFFSET + i * 16 : PLINK_TABLE_OFFSET + (i + 1) * 16]
        w = struct.unpack("<8H", entry)
        if w[3] == 0xFFFF:
            break
        name_off = PLINK_TABLE_OFFSET + w[7]
        end = img.find(b"\x00", name_off)
        name = img[name_off:end].decode("ascii", errors="replace")
        fpath = ORIG_DIR / name
        fsize = fpath.stat().st_size if fpath.exists() else -1
        overlays.append(
            {
                "ovl_id": i + 1,
                "name": name,
                "load_seg": w[5],
                "end_seg": w[6],
                "flags": w[3],
                "file_size": fsize,
            }
        )
    return overlays


def parse_plink_thunks(img: bytes, overlays: list[dict[str, object]]) -> list[dict[str, object]]:
    by_id = {o["ovl_id"]: o for o in overlays}
    thunks = []
    pos = 0
    while True:
        idx = img.find(PLINK_THUNK_SIG, pos)
        if idx == -1:
            break
        ovl_id, jmp_op, ip, cs = struct.unpack("<HBHH", img[idx + 5 : idx + 12])
        ovl = by_id.get(ovl_id)
        load_seg = ovl["load_seg"] if ovl else 0
        ovl_off = ip - load_seg * 16 if (ovl and cs == 0) else ip
        thunks.append(
            {
                "thunk_off": idx,
                "ovl_id": ovl_id,
                "ovl_name": ovl["name"] if ovl else "?",
                "jmp_op": jmp_op,
                "cs": cs,
                "ip": ip,
                "ovl_off": ovl_off,
            }
        )
        pos = idx + 12
    return thunks


def main() -> None:
    data = EXE_PATH.read_bytes()
    hdr = parse_mz_header(data)
    img = data[hdr["hdr_bytes"] :]

    print("=== ULTIMA.EXE MZ Header ===")
    print(f"File size:   {len(data)} bytes (MZ image: {len(img)} bytes, header: {hdr['hdr_bytes']} bytes)")
    print(f"Entry CS:IP: {hdr['cs']:#06x}:{hdr['ip']:#06x}  SS:SP: {hdr['ss']:#06x}:{hdr['sp']:#06x}")
    print(f"Relocations: {hdr['relocs']}")

    overlays = parse_plink_overlays(img)
    print(f"\n=== Plink86 Overlay Table ({len(overlays)} entries) ===")
    print(f"{'ID':>2} {'File':<14} {'LoadSeg':>7} {'EndSeg':>7} {'Span':>7} {'Flags':>6} {'FileSize':>8}")
    for o in overlays:
        span = (o["end_seg"] - o["load_seg"]) * 16
        print(
            f"{o['ovl_id']:2d} {o['name']:<14} {o['load_seg']:#06x}  {o['end_seg']:#06x}  "
            f"{span:7d} {o['flags']:#06x} {o['file_size']:8d}"
        )

    thunks = parse_plink_thunks(img, overlays)
    print(f"\n=== Plink86 Thunks ({len(thunks)} total) ===")
    for t in thunks[:20]:
        print(
            f"  0000:{t['thunk_off']:04x} -> ovl {t['ovl_id']:2d} ({t['ovl_name']:<12s}) "
            f"target={t['cs']:#06x}:{t['ip']:#06x} (ovl+{t['ovl_off']:#06x})"
        )
    if len(thunks) > 20:
        print(f"  ... ({len(thunks) - 20} more)")


if __name__ == "__main__":
    main()
