#!/usr/bin/env python3
"""Pure-Python PNG exporter for Ultima V TILES.16, BRIT.DAT, and UNDER.DAT."""

from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path

from lzw import lzw_decompress

ORIG_DIR = Path(__file__).resolve().parent.parent / "orig" / "extracted"

# Standard 16-color EGA palette (RGB)
EGA_PALETTE: list[tuple[int, int, int]] = [
    (0x00, 0x00, 0x00),  # 0: Black
    (0x00, 0x00, 0xAA),  # 1: Blue
    (0x00, 0xAA, 0x00),  # 2: Green
    (0x00, 0xAA, 0xAA),  # 3: Cyan
    (0xAA, 0x00, 0x00),  # 4: Red
    (0xAA, 0x00, 0xAA),  # 5: Magenta
    (0xAA, 0x55, 0x00),  # 6: Brown
    (0xAA, 0xAA, 0xAA),  # 7: Light Gray
    (0x55, 0x55, 0x55),  # 8: Dark Gray
    (0x55, 0x55, 0xFF),  # 9: Bright Blue
    (0x55, 0xFF, 0x55),  # 10: Bright Green
    (0x55, 0xFF, 0xFF),  # 11: Bright Cyan
    (0xFF, 0x55, 0x55),  # 12: Bright Red
    (0xFF, 0x55, 0xFF),  # 13: Bright Magenta
    (0xFF, 0xFF, 0x55),  # 14: Yellow
    (0xFF, 0xFF, 0xFF),  # 15: White
]


def write_png_rgb(path: Path, width: int, height: int, rgb_rows: list[bytes]) -> None:
    def chunk(tag: bytes, payload: bytes) -> bytes:
        crc = zlib.crc32(tag + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", crc)

    raw = b"".join(b"\x00" + row for row in rgb_rows)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def load_tiles16() -> list[list[list[tuple[int, int, int]]]]:
    dec = lzw_decompress((ORIG_DIR / "TILES.16").read_bytes())
    tiles = []
    for tid in range(512):
        block = dec[tid * 128 : (tid + 1) * 128]
        rows = []
        for y in range(16):
            row = []
            for x in range(8):
                b = block[y * 8 + x]
                row.append(EGA_PALETTE[b >> 4])
                row.append(EGA_PALETTE[b & 0x0F])
            rows.append(row)
        tiles.append(rows)
    return tiles


def export_tilesheet(out_path: Path) -> None:
    tiles = load_tiles16()
    cols, rows_n = 32, 16
    w, h = cols * 16, rows_n * 16
    img_rows: list[bytes] = []
    for ty in range(rows_n):
        for py in range(16):
            line = bytearray()
            for tx in range(cols):
                for r, g, b in tiles[ty * cols + tx][py]:
                    line.extend((r, g, b))
            img_rows.append(bytes(line))
    write_png_rgb(out_path, w, h, img_rows)
    print(f"Wrote {out_path} ({w}x{h})")


def load_brit_grid() -> list[bytes]:
    data_ovl = (ORIG_DIR / "DATA.OVL").read_bytes()
    chunk_map = data_ovl[0x3886 : 0x3886 + 256]
    brit = (ORIG_DIR / "BRIT.DAT").read_bytes()
    grid = [bytearray(256) for _ in range(256)]
    for cy in range(16):
        for cx in range(16):
            cidx = chunk_map[cy * 16 + cx]
            if cidx == 0xFF:
                for y in range(16):
                    grid[cy * 16 + y][cx * 16 : (cx + 1) * 16] = b"\x01" * 16
            else:
                chunk = brit[cidx * 256 : (cidx + 1) * 256]
                for y in range(16):
                    grid[cy * 16 + y][cx * 16 : (cx + 1) * 16] = chunk[y * 16 : (y + 1) * 16]
    return [bytes(r) for r in grid]


def export_world_map(which: str, out_path: Path, scale1px: bool = False) -> None:
    tiles = load_tiles16()
    if which == "brit":
        grid = load_brit_grid()
    else:
        raw = (ORIG_DIR / "UNDER.DAT").read_bytes()
        grid = [raw[y * 256 : (y + 1) * 256] for y in range(256)]

    if scale1px:
        # 1x1 pixel per tile using average/center pixel color of each tile
        tile_rgb = [tiles[tid][8][8] for tid in range(512)]
        img_rows = []
        for y in range(256):
            line = bytearray()
            for tid in grid[y]:
                line.extend(tile_rgb[tid])
            img_rows.append(bytes(line))
        write_png_rgb(out_path, 256, 256, img_rows)
        print(f"Wrote {out_path} (256x256 minimap)")
    else:
        img_rows = []
        for y in range(256):
            for py in range(16):
                line = bytearray()
                for tid in grid[y]:
                    for r, g, b in tiles[tid][py]:
                        line.extend((r, g, b))
                img_rows.append(bytes(line))
        write_png_rgb(out_path, 4096, 4096, img_rows)
        print(f"Wrote {out_path} (4096x4096)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render Ultima V tileset or world maps to PNG.")
    parser.add_argument("target", choices=["tiles", "brit", "under"], help="What to render")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output PNG path")
    parser.add_argument("--minimap", action="store_true", help="Render 256x256 1px/tile minimap")
    args = parser.parse_args()

    if args.target == "tiles":
        export_tilesheet(args.output)
    else:
        export_world_map(args.target, args.output, scale1px=args.minimap)


if __name__ == "__main__":
    main()
