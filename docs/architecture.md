# Ultima V (DOS) — Program Architecture

This document records the binary architecture of the MS-DOS version of *Ultima V: Warriors of Destiny* found in `orig/extracted/`.

## 1. Compiler, Linker, and Overlay Manager

- **Compiler / Runtime**: Microsoft C (5.x) — `DATA.OVL` contains `MS Run-Time Library - Copyright (c) 1988, Microsoft Corp`.
- **Linker / Overlay Manager**: **Plink86** (`Copyright (C) 1984, 1985, 1986 by Phoenix Software Associates Ltd.`), embedded in `ULTIMA.EXE`.
- **Execution Model**: 16-bit real-mode MS-DOS, small/medium-style code overlays sharing a single resident `DGROUP` (`DATA.OVL`).

## 2. `ULTIMA.EXE` Layout

Inspected via [tools/exe_info.py](../tools/exe_info.py):

- **File size**: 36,592 bytes
- **MZ header**: 2,048 bytes (`0x800`)
- **MZ load image**: 34,544 bytes (`0x86f0`), 409 relocations
- **Initial MZ `CS:IP`**: `0x081d:0x0000` (relative to load segment)
- **Initial MZ `SS:SP`**: `0x096f:0x0064`

### Startup Sequence

1. `0x081d:0x0000` — Plink86 entry trampoline: sets `SS = DS + 0x1b48`, `SP = 0x0800`, and `retf`s to `0x072e:0x0322`.
2. `0x072e:0x0322` — Plink86 initialization:
   - Reads the 24-entry overlay descriptor table at segment `0x0778` (offset `0x7780` in the MZ image).
   - Preloads any entry with flag `0x4000` (`DATA.OVL`, flags `0x6000`) via `lcall 0x072e:0x0292`.
   - Jumps to `0x0000:0x017e` (Microsoft C `crt0` startup).
3. `0x0000:0x017e` — C runtime startup:
   - Sets `SS = DS = 0x0f64` (`DGROUP` / `DATA.OVL`).
   - Zeroes BSS from `DS:0xa524` to `DS:0xbd40`.
   - Calls `_main` at `0x0000:0x0000`.

## 3. Memory Map & Overlay Slots

All segments below are **relative to the MZ load segment** (`PSP + 0x10`).

| Segment Range | Role |
|---|---|
| `0x0000` – `0x072e` | Resident game engine, C runtime, and Plink86 cross-overlay thunks (`0x7a16`–`0x81ba`, 164 thunks) |
| `0x072e` – `0x081d` | Plink86 overlay manager code, data (`0x076c`), and descriptor table (`0x0778`) |
| `0x081d` – `0x0a29` | **Overlay Area 1** (max 8,384 B): `TOWN.OVL`, `MAINOUT.OVL`, `DUNGEON.OVL`, `INTRO.OVL` |
| `0x0a29` – `0x0bf8` | **Overlay Area 2** (max 7,408 B): `FLAMES.OVL`, `NPC.OVL`, `COMBAT.OVL`, `BLCKTHRN.OVL`, `LOOKOBJ.OVL`, `DNGLOOK.OVL`, `OUTSUBS.OVL`, `SHOPPES.OVL`, `ENDGAME.OVL` |
| `0x0bf8` – `0x0e1e` | **Overlay Area 3** (max 8,800 B): `SJOG.OVL`, `CMDS.OVL`, `CAST.OVL`, `TALK.OVL` |
| `0x0e1e` – `0x0f64` | **Overlay Area 4** (max 5,216 B): `CAST2.OVL`, `ZSTATS.OVL`, `COMSUBS.OVL`, `SHOPPES2.OVL`, `SHOPPES3.OVL`, `FONT.OVL` |
| `0x0f64` – `0x1bb8` | **Resident `DGROUP`**: `DATA.OVL` (48,464 bytes initialized/zeroed + BSS up to `0x1bb8`) |

### Overlay File Format

`*.OVL` files have **no file header**. Each file is a raw, pre-relocated binary image loaded directly to its fixed `LoadSeg:0000`.

Cross-overlay calls go through 12-byte Plink86 thunks in `ULTIMA.EXE` (`0x0000:0x7a16`..`0x81ba`):
```text
9A EC 02 2E 07    ; lcall 0x072e:0x02ec (Plink86 overlay dispatcher)
<ovl_id: uint16>  ; 1-based overlay index (1..24)
EA <ip:u16> <cs:u16> ; ljmp target (ip is LoadSeg*16 + offset when cs == 0)
```

## 4. Video Drivers (`*.DRV`)

`CGA.DRV`, `EGA.DRV`, `HER.DRV`, and `T1K.DRV` are flat 16-bit x86 binaries starting with a table of 3-byte `jmp` (`0xe9`) instructions at offsets `0x0000, 0x0003, 0x0006, ...`. Unimplemented entries jump to a shared `retf`.

## 5. `_main` Loop (`0x0000:0x0000`)

Observed control flow in `_main`:
1. Parses `argv[1][0]` (uppercased via `0x0000:0x2032`) for display mode flags:
   - `'C'` (CGA) -> `DS:[0x52ba]`
   - `'H'` (Hercules) -> `DS:[0x52f3]`
   - `'T'` (Tandy) -> `DS:[0x52f1]`
   - `'E'` (EGA) -> `DS:[0x52ef]`
2. Checks current DOS drive (`int 21h / ah=19h` via `0x0000:0x16a6`); if `>= 'C'`, stores drive letter in `DS:[0xa9c8..0xa9cd]` (hard-disk install detection).
3. Calls `INTRO.OVL` (`0x0000:0x7a2e` -> `ovl 4`, `+0x0976`) and `0x0000:0x2900` (initial UI/roster draw).
4. Main dispatch loop keyed on location ID `DS:[0x5893]`:
   - `== 0`: calls `MAINOUT.OVL` (`0x0000:0x7a3a` -> `ovl 2`, `+0x0d22`) — Overworld / Britannia & Underworld.
   - `1 .. 0x20`: calls `TOWN.OVL` (`0x0000:0x7a46` -> `+0x11f0`, `0x0000:0x7a52` -> `+0x141e`) — Towns, Castles, Keeps, Dwellings.
   - `>= 0x21`: calls `DUNGEON.OVL` (`0x0000:0x7a16` -> `ovl 3`, `+0x0e2e`) — Dungeons.
5. After leaving a settlement/dungeon, persists state via `OUTSUBS.OVL` (`0x0000:0x7a22`) and `0x0000:0x256e` / `0x0000:0x25d8` until quit (`[bp-2] != 0`), then exits via `0x0000:0x0878`.
