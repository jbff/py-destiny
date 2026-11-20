"""Dialogue (.TLK) and misc text/data file loaders."""

from __future__ import annotations

import struct
from pathlib import Path


def decode_tlk_bytes(buf: bytes, words: dict[int, str]) -> str:
    """Decode an Ultima V .TLK byte stream into readable text with control tokens."""
    out: list[str] = []
    p = 0
    n = len(buf)
    while p < n:
        b = buf[p]
        p += 1
        if b == 0x00:
            out.append("\n| ")
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
            if p < n and buf[p] >= 0x80:
                nc = buf[p] & 0x7F
                if chr(nc).isalnum() or nc in (ord('"'), ord("(")):
                    out.append(" ")
    return "".join(out).strip()


def load_tlk(tlk_path: Path, words: dict[int, str]) -> dict[int, str]:
    """Load a .TLK file into {npc_id: decoded_script}."""
    raw = tlk_path.read_bytes()
    count = struct.unpack_from("<H", raw, 0)[0]
    entries = [struct.unpack_from("<HH", raw, 2 + i * 4) for i in range(count)]
    result: dict[int, str] = {}
    for idx, (npc_id, off) in enumerate(entries):
        end = entries[idx + 1][1] if idx + 1 < len(entries) else len(raw)
        result[npc_id] = decode_tlk_bytes(raw[off:end], words)
    return result


def load_look2(look2_path: Path) -> list[str]:
    """Load LOOK2.DAT -> 512 tile descriptions."""
    raw = look2_path.read_bytes()
    offs = struct.unpack_from("<512H", raw, 0)
    out: list[str] = []
    for off in offs:
        end = raw.find(b"\x00", off)
        out.append(raw[off:end].decode("ascii", errors="replace"))
    return out


def load_signs(signs_path: Path) -> list[str]:
    """Load SIGNS.DAT -> list of sign strings."""
    raw = signs_path.read_bytes()
    count = struct.unpack_from("<H", raw, 0)[0]
    offs = struct.unpack_from(f"<{count}H", raw, 2)
    out: list[str] = []
    for off in offs:
        if off == 0:
            out.append("")
        else:
            end = raw.find(b"\x00", off)
            out.append(raw[off:end].decode("ascii", errors="replace"))
    return out


def load_delimited_blocks(path: Path) -> list[str]:
    """Load '{'-delimited ASCII text blocks (QUESTION.DAT, STORY.DAT, END.DAT)."""
    text = path.read_bytes().decode("ascii", errors="replace")
    return [blk for blk in text.split("{") if blk]


def load_shoppe_strings(shoppe_path: Path, words: dict[int, str]) -> list[str]:
    """Load SHOPPE.DAT null-terminated strings with 0x80+word_idx compression."""
    raw = shoppe_path.read_bytes()
    out: list[str] = []
    for chunk in raw.split(b"\x00"):
        parts: list[str] = []
        for b in chunk:
            if b >= 0x80:
                w = words.get((b - 0x80) + 1, f"[w{b}]")
                parts.append(f" {w} ")
            else:
                parts.append(chr(b))
        out.append("".join(parts).strip())
    return out
