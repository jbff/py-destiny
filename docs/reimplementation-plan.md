# Ultima V (DOS) — Python Reimplementation Plan

This plan outlines an incremental, machine-code-faithful Python reimplementation of *Ultima V: Warriors of Destiny* grounded in our disassembly and format documentation:

- [architecture.md](architecture.md) — Executable & overlay memory map
- [overlays.md](overlays.md) — 164 Plink86 cross-overlay entry points
- [file-formats.md](file-formats.md) — Binary resource & save formats
- [game-logic.md](game-logic.md) — Verified state offsets, formulas, and dispatch rules

## Guiding Principles

1. **One small, verifiable slice at a time**: Every phase produces a runnable, testable deliverable rather than a monolithic rewrite.
2. **Machine-code fidelity**: Behavior is derived from `ULTIMA.EXE` / `*.OVL` disassembly and `DATA.OVL` tables. Whenever a detail is not yet documented, we return to the original binaries before coding.
3. **Open extracted data (`data/`) & JSON saves**: Original files remain untouched in `orig/` (gitignored). All game tables, maps, NPCs, dialogues, text, and initial state are extracted once via `tools/extract_data.py` into open JSON under `data/` (committed for clones), and save games use JSON (`SaveGame.save_json()` / `load_json()`).
4. **Test-driven data & rules**: Every parser, decompressor, and formula is unit-tested against the original binary files.

---

## Phase 0: Scaffolding & Verified Asset Loaders (Headless)

**Goal**: Create the `pydestiny` Python package and port/test all binary loaders against `orig/extracted/`.

- **Deliverables**:
  - Package layout: `pydestiny/assets/`, `pydestiny/state/`, `pydestiny/engine/`, `pydestiny/ui/`, plus `tests/`.
  - `assets/lzw.py`: LZW decompressor (`*.16`, `*.4`, `*.BIT`).
  - `assets/graphics.py`: `TILES.16` (512 x 16x16 4bpp), `ITEMS.16`, `MON0–7.16`, `DNG1–3.16`, `*.BIT`, `IBM.CH` / `RUNES.CH` fonts.
  - `assets/tables.py`: `DATA.OVL` tables (48 spells + recipes `0x1cd0`, 48 monster/actor stats `0x13cc`, equipment stats `0x1614`–`0x16db`, foot-impassable bitmask `0x54d4`, opaque tile list `0x6a96`, Trammel/Felucca phases `0x1ee8`, `BRIT.DAT` chunk map `0x3886`).
  - `assets/maps.py`: `BRIT.DAT`, `UNDER.DAT`, settlement `*.DAT`, `DUNGEON.DAT`, `BRIT.CBT`, `DUNGEON.CBT`.
  - `assets/text.py`: `*.TLK` decoder, `SHOPPE.DAT`, `LOOK2.DAT`, `SIGNS.DAT`, `KARMA.DAT`, `QUESTION.DAT`, `STORY.DAT`, `END.DAT`.
  - `state/savegame.py`: `INIT.GAM` / `SAVED.GAM` (`4,192` B) and `*.OOL` (`256`/`512` B) round-tripper.
- **Open questions to resolve from binaries first**:
  - Remaining `SAVED.GAM` offsets (`0x020c`–`0x0219` quest items, `0x02b2`–`0x02cd` moonstones/shrines/Shadowlords, `0x02f2`–`0x03b3` party roster/wind, `0x0bb8`–`0x105f` talk/chest/door flags).

---

## Phase 1: Headless Simulation Core (Pure Python Rules)

**Goal**: Implement and unit-test core deterministic game rules with zero UI dependencies.

- **Deliverables**:
  - `engine/time.py`: `advance_time(minutes)` (`0x0000:0x4f7c`), 28-day/13-month calendar, Quicken/Time Stop, Trammel/Felucca phases & sky visibility (`0x4ae0`), Day/Night darkness (`0x475a`).
  - `engine/fov.py`: `11 x 11` BFS flood-fill FOV (`0x0000:0x5a28`, `0x5dfe`) with semi-transparent tiles and `DATA.OVL+0x6a96` opacity list.
  - `engine/movement.py`: Tile passability (`0x0000:0x2bd4`, `0x2c2e`, `0x2c4c`) and overworld/settlement coordinate handling.
  - `engine/karma.py`: Karma state (`0..99`) and verified modifiers.
  - `engine/magic.py`: Reagent mixing (`CMDS.OVL+0x1ad8`) and spell castability/cost checks (`CAST.OVL+0x0dba`).
  - `engine/combat_math.py`: Effective DEX (`COMBAT.OVL+0x139a`), hit/miss (`+0x14d6`), damage/death (`+0x1574`), EXP award (`+0x1934`), Euclidean distance (`COMSUBS.OVL+0x048a`).

---

## Phase 2: Minimal Playable Overworld Viewport

**Goal**: Render the `320x200` EGA screen (scaled cleanly) and walk around Britannia & the Underworld with save/load.

- **Deliverables**:
  - `ui/` renderer (`pygame-ce` or SDL2) drawing `TILES.16`, `IBM.CH` text, party roster, date/moon bar, and scrolling message log.
  - `MAINOUT.OVL` loop: movement, `L`ook (`LOOK2.DAT`), `Z`tats (`ZSTATS.OVL`), `Q`uit & Save (`SAVED.GAM` / `SAVED.OOL`).
- **Open questions to resolve from binaries first**:
  - Exact UI layout coordinates (`0x0000:0x2900`), tile animations (`0x0000:0x5910`), and keyboard mapping.
  - Vehicle/wind mechanics (`B`oard, `X`-it, horses, skiffs, frigates, whirlpools) in `MAINOUT.OVL` / `CMDS.OVL`.

---

## Phase 3: Settlements, NPCs, & Dialogue

**Goal**: Make all 32 Castles, Towns, Keeps, and Dwellings explorable with live NPC schedules and full dialogue.

- **Deliverables**:
  - `E`nter / exit settlements (`location_id 1..32`, multi-floor `z`).
  - Hourly NPC schedule resolution (`NPC.OVL+0x00d6`, `*.NPC`) and NPC movement/wandering.
  - `T`alk engine (`TALK.OVL` + `*.TLK`): keyword matching, `<AVATAR>`, `<PAUSE>`, `<0x90..0x9F>` branching.
  - `O`pen / `J`immy / `G`et / `S`earch / `P`ush (`SJOG.OVL`, `CMDS.OVL`) + Karma & Guard hostility triggers.
- **Open questions to resolve from binaries first**:
  - Exact NPC movement/pathfinding AI in `NPC.OVL` and `0x90..0x9F` script opcodes in `TALK.OVL`.
  - Blackthorn capture & guard arrest triggers (`BLCKTHRN.OVL`).

---

## Phase 4: Tactical Combat & Monster AI

**Goal**: Full `11 x 11` tactical combat on overworld, settlement, and dungeon encounter maps.

- **Deliverables**:
  - Encounter setup from `BRIT.CBT` / `DUNGEON.CBT` (`11 x 32` B/row).
  - Turn order, `A`ttack / `F`ire / `C`ast / pass / flee off-map, ranged targeting (`COMSUBS.OVL+0x0504`).
  - Monster AI, special abilities (`DATA.OVL+0x154c`), loot/chests, and EXP/leveling.
- **Open questions to resolve from binaries first**:
  - Exact monster AI loop and special attack handlers in `COMBAT.OVL` / `COMSUBS.OVL`.
  - Level-up thresholds and Shrine/Lord British stat-gain rules (`CAST2.OVL` / `OUTSUBS.OVL`).

---

## Phase 5: Complete Magic Effects & Shoppes

**Goal**: Implement all 48 spells, special `U`se items, and all merchant/service shoppes.

- **Deliverables**:
  - All 48 spell handlers from `CAST.OVL+0x1146` + `CAST2.OVL`, plus `U`se item (`CAST.OVL+0x1792`).
  - All Shoppe types (`SHOPPES.OVL`–`SHOPPES3.OVL`, `SHOPPE.DAT`).
- **Open questions to resolve from binaries first**:
  - Exact item stock & price tables in `DATA.OVL` / `SHOPPES*.OVL`.

---

## Phase 6: 3D Dungeons

**Goal**: Full 3D first-person dungeon exploration and dungeon rooms.

- **Deliverables**:
  - 3D perspective renderer using `DNG1`–`DNG3.16` (28 slices) and ceiling/floor colors (`DUNGEON.OVL+0x0332`).
  - Dungeon movement (`K`limb ladders, traps, fountains, pits, secret doors, `DNGLOOK.OVL`, `DUNGEON.CBT` rooms).
- **Open questions to resolve from binaries first**:
  - Exact slice-to-cell mapping in `DUNGEON.OVL` for depths 1–4.

---

## Phase 7: Intro, Character Creation, Endgame, & Audio

**Goal**: Complete start-to-finish playthrough experience.

- **Deliverables**:
  - Title screen, `STORY.DAT` intro, gypsy virtue interview (`INTRO.OVL`, `QUESTION.DAT`).
  - `ENDGAME.OVL` sequence (`END.DAT`, `ENDMSG.DAT`).
  - PC speaker SFX synthesis matching `0x0000:0x21fc`–`0x2315`.
