"""LZW decompression for Ultima V .16, .4, and .BIT asset files."""

from __future__ import annotations

import struct


def lzw_decompress(data: bytes) -> bytes:
    """Decompress an Ultima V LZW stream (uint32 LE size + 9..12-bit LSB-first codes)."""
    uncomp_size = struct.unpack_from("<I", data, 0)[0]
    src = data[4:]
    bit_pos = 0

    def read_bits(n: int) -> int:
        nonlocal bit_pos
        val = 0
        for i in range(n):
            byte_idx = (bit_pos + i) >> 3
            if byte_idx >= len(src):
                return 0x101
            bit = (src[byte_idx] >> ((bit_pos + i) & 7)) & 1
            val |= bit << i
        bit_pos += n
        return val

    out = bytearray()
    code_len = 9
    next_code = 0x102
    table: dict[int, bytes] = {i: bytes([i]) for i in range(256)}
    prev: bytes | None = None

    while len(out) < uncomp_size:
        code = read_bits(code_len)
        if code == 0x101:
            break
        if code == 0x100:
            code_len = 9
            next_code = 0x102
            table = {i: bytes([i]) for i in range(256)}
            prev = None
            continue
        if code in table:
            entry = table[code]
        elif code == next_code and prev is not None:
            entry = prev + prev[:1]
        else:
            raise ValueError(
                f"Invalid LZW code {code:#x} at bit {bit_pos} (out={len(out)}/{uncomp_size})"
            )
        out.extend(entry)
        if prev is not None and next_code < 4096:
            table[next_code] = prev + entry[:1]
            next_code += 1
            if next_code == (1 << code_len) and code_len < 12:
                code_len += 1
        prev = entry

    return bytes(out)
