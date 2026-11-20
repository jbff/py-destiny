"""Graphics, tileset, sprite, and bitmap font loaders for Ultima V."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

from pydestiny.assets.lzw import lzw_decompress

EGA_PALETTE: tuple[tuple[int, int, int], ...] = (
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
)


@dataclass(frozen=True)
class SubImage:
    width: int
    height: int
    data: bytes  # raw packed pixel bytes (4bpp, 2bpp, or 1bpp)


def load_tileset16(path: Path) -> list[bytes]:
    """Load TILES.16 -> 512 tiles, each 256 bytes of 4-bit palette indices (0..15)."""
    dec = lzw_decompress(path.read_bytes())
    if len(dec) != 512 * 128:
        raise ValueError(f"Expected 65536 bytes for TILES.16, got {len(dec)}")
    tiles: list[bytes] = []
    for tid in range(512):
        block = dec[tid * 128 : (tid + 1) * 128]
        pixels = bytearray(256)
        for i, b in enumerate(block):
            pixels[i * 2] = b >> 4
            pixels[i * 2 + 1] = b & 0x0F
        tiles.append(bytes(pixels))
    return tiles


def load_font_8x8(path: Path) -> list[bytes]:
    """Load IBM.CH or RUNES.CH -> 128 glyphs, each 8 bytes (MSB-first 1bpp)."""
    raw = path.read_bytes()
    if len(raw) != 1024:
        raise ValueError(f"Expected 1024 bytes for 8x8 font, got {len(raw)}")
    return [raw[i * 8 : (i + 1) * 8] for i in range(128)]


def load_image_container(path: Path, compressed: bool = True) -> list[SubImage]:
    """Load a .16, .4, or .BIT sub-image container."""
    raw = lzw_decompress(path.read_bytes()) if compressed else path.read_bytes()
    count = struct.unpack_from("<H", raw, 0)[0]
    first_u32 = struct.unpack_from("<I", raw, 2)[0]
    first_u16 = struct.unpack_from("<H", raw, 2)[0]

    if first_u32 == 2 + count * 4:
        offsets = list(struct.unpack_from(f"<{count}I", raw, 2))
    elif first_u16 == 2 + count * 4:
        # Paired uint16 offsets (image + mask)
        offsets = list(struct.unpack_from(f"<{count * 2}H", raw, 2))
    elif first_u16 == 2 + count * 2:
        offsets = list(struct.unpack_from(f"<{count}H", raw, 2))
    else:
        raise ValueError(f"Unrecognized image container header in {path.name}: count={count}")

    sorted_offs = sorted(set(offsets))
    images: list[SubImage] = []
    for off in offsets:
        w, h = struct.unpack_from("<HH", raw, off)
        idx = sorted_offs.index(off)
        end = sorted_offs[idx + 1] if idx + 1 < len(sorted_offs) else len(raw)
        images.append(SubImage(width=w, height=h, data=raw[off + 4 : end]))
    return images
