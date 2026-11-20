"""SAVED.GAM / INIT.GAM (4,192-byte) binary state container with exact round-trip fidelity."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

SAVED_GAM_SIZE = 4192


@dataclass
class CharacterRecord:
    """32-byte character record (SAVED.GAM + 0x0002 + idx*32)."""

    name: str
    gender: int      # 0x0B = Male, 0x0C = Female
    char_class: str  # 'A', 'F', 'B', 'M'
    status: str      # 'G', 'P', 'D', etc.
    strength: int
    dexterity: int
    intelligence: int
    mp: int
    hp: int
    max_hp: int
    exp: int
    level: int
    months_in_party: int
    unknown_18: int
    party_slot: int  # 0xFF = not in party
    equipped: bytearray  # 6 bytes (helm, armour, weapon, shield, ring, amulet)

    @classmethod
    def from_bytes(cls, data: bytes) -> CharacterRecord:
        if len(data) != 32:
            raise ValueError(f"Expected 32 bytes for CharacterRecord, got {len(data)}")
        raw_name = data[0:9].split(b"\x00", 1)[0].decode("ascii", errors="replace")
        hp, max_hp, exp = struct.unpack_from("<HHH", data, 0x10)
        return cls(
            name=raw_name,
            gender=data[0x09],
            char_class=chr(data[0x0A]) if data[0x0A] else "\x00",
            status=chr(data[0x0B]) if data[0x0B] else "\x00",
            strength=data[0x0C],
            dexterity=data[0x0D],
            intelligence=data[0x0E],
            mp=data[0x0F],
            hp=hp,
            max_hp=max_hp,
            exp=exp,
            level=data[0x16],
            months_in_party=data[0x17],
            unknown_18=data[0x18],
            party_slot=data[0x19],
            equipped=bytearray(data[0x1A:0x20]),
        )

    def to_bytes(self) -> bytes:
        buf = bytearray(32)
        name_b = self.name.encode("ascii", errors="replace")[:8]
        buf[0 : len(name_b)] = name_b
        buf[0x09] = self.gender
        buf[0x0A] = ord(self.char_class) if self.char_class != "\x00" else 0
        buf[0x0B] = ord(self.status) if self.status != "\x00" else 0
        buf[0x0C] = self.strength
        buf[0x0D] = self.dexterity
        buf[0x0E] = self.intelligence
        buf[0x0F] = self.mp
        struct.pack_into("<HHH", buf, 0x10, self.hp, self.max_hp, self.exp)
        buf[0x16] = self.level
        buf[0x17] = self.months_in_party
        buf[0x18] = self.unknown_18
        buf[0x19] = self.party_slot
        buf[0x1A:0x20] = self.equipped[:6]
        return bytes(buf)


class SaveGame:
    """In-memory representation of SAVED.GAM (DS:0x55a6..0x6606)."""

    def __init__(self, raw: bytes) -> None:
        if len(raw) != SAVED_GAM_SIZE:
            raise ValueError(f"Expected {SAVED_GAM_SIZE} bytes, got {len(raw)}")
        self.raw = bytearray(raw)
        self.characters: list[CharacterRecord] = [
            CharacterRecord.from_bytes(self.raw[2 + i * 32 : 2 + (i + 1) * 32])
            for i in range(16)
        ]

    @classmethod
    def from_file(cls, path: Path) -> SaveGame:
        return cls(path.read_bytes())

    def to_bytes(self) -> bytes:
        out = bytearray(self.raw)
        for i, ch in enumerate(self.characters):
            out[2 + i * 32 : 2 + (i + 1) * 32] = ch.to_bytes()
        return bytes(out)

    def save(self, path: Path) -> None:
        path.write_bytes(self.to_bytes())

    def _u16(self, off: int) -> int:
        return struct.unpack_from("<H", self.raw, off)[0]

    def _set_u16(self, off: int, val: int) -> None:
        struct.pack_into("<H", self.raw, off, val & 0xFFFF)

    @property
    def food(self) -> int:
        return self._u16(0x0202)

    @food.setter
    def food(self, val: int) -> None:
        self._set_u16(0x0202, val)

    @property
    def gold(self) -> int:
        return self._u16(0x0204)

    @gold.setter
    def gold(self, val: int) -> None:
        self._set_u16(0x0204, val)

    @property
    def keys(self) -> int:
        return self._u16(0x0206)

    @keys.setter
    def keys(self, val: int) -> None:
        self._set_u16(0x0206, val)

    @property
    def gems(self) -> int:
        return self._u16(0x0208)

    @gems.setter
    def gems(self, val: int) -> None:
        self._set_u16(0x0208, val)

    @property
    def torches(self) -> int:
        return self._u16(0x020A)

    @torches.setter
    def torches(self, val: int) -> None:
        self._set_u16(0x020A, val)

    @property
    def equipment(self) -> memoryview:
        return memoryview(self.raw)[0x021A : 0x021A + 48]

    @property
    def prepared_spells(self) -> memoryview:
        return memoryview(self.raw)[0x024A : 0x024A + 48]

    @property
    def reagents(self) -> memoryview:
        return memoryview(self.raw)[0x02AA : 0x02AA + 8]

    @property
    def year(self) -> int:
        return self._u16(0x02CE)

    @year.setter
    def year(self, val: int) -> None:
        self._set_u16(0x02CE, val)

    @property
    def active_spell(self) -> int:
        return self.raw[0x02D4]

    @active_spell.setter
    def active_spell(self, val: int) -> None:
        self.raw[0x02D4] = val & 0xFF

    @property
    def month(self) -> int:
        return self.raw[0x02D7]

    @month.setter
    def month(self, val: int) -> None:
        self.raw[0x02D7] = val & 0xFF

    @property
    def day(self) -> int:
        return self.raw[0x02D8]

    @day.setter
    def day(self, val: int) -> None:
        self.raw[0x02D8] = val & 0xFF

    @property
    def hour(self) -> int:
        return self.raw[0x02D9]

    @hour.setter
    def hour(self, val: int) -> None:
        self.raw[0x02D9] = val & 0xFF

    @property
    def minute(self) -> int:
        return self.raw[0x02DB]

    @minute.setter
    def minute(self, val: int) -> None:
        self.raw[0x02DB] = val & 0xFF

    @property
    def karma(self) -> int:
        return self.raw[0x02E2]

    @karma.setter
    def karma(self, val: int) -> None:
        self.raw[0x02E2] = max(0, min(99, val))

    @property
    def location_id(self) -> int:
        return self.raw[0x02ED]

    @location_id.setter
    def location_id(self, val: int) -> None:
        self.raw[0x02ED] = val & 0xFF

    @property
    def z(self) -> int:
        return self.raw[0x02EF]

    @z.setter
    def z(self, val: int) -> None:
        self.raw[0x02EF] = val & 0xFF

    @property
    def x(self) -> int:
        return self.raw[0x02F0]

    @x.setter
    def x(self, val: int) -> None:
        self.raw[0x02F0] = val & 0xFF

    @property
    def y(self) -> int:
        return self.raw[0x02F1]

    @y.setter
    def y(self, val: int) -> None:
        self.raw[0x02F1] = val & 0xFF
