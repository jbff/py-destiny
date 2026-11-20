# PyDestiny

A machine-code-faithful Python reimplementation of *Ultima V: Warriors of Destiny* (MS-DOS), built incrementally from reverse-engineering the original 16-bit x86 binaries (`ULTIMA.EXE`, `DATA.OVL`, `*.OVL`) and resource files.

All game data is extracted into open JSON (`data/`) and PNG (`assets/`), and save games use JSON (`save.json`) rather than proprietary binary formats.

## Running with `uv`

```bash
uv sync --extra dev
uv run pydestiny
```

Optional flags:
- `--save path/to/save.json` — Load/save a specific JSON save file (defaults to `save.json`, initialized from `data/init_save.json`).

## Running Tests

```bash
uv run pytest -v
```

## Controls

- **Arrow keys / Numpad `8`/`2`/`4`/`6`** — Move (walk off settlement edge to exit; walk off combat edge to flee; in 3D dungeons: Up/Down moves, Left/Right turns)
- **`E`** — Enter settlement or dungeon at current overworld tile (e.g., Britain `(81, 106)`, LB's Castle `(86, 107)`, Moonglow `(232, 135)`)
- **`T`** + direction — Talk to an adjacent NPC or open a merchant shoppe
- **`L`** + direction — Look at an adjacent tile
- **`J`** + direction — Jimmy a locked door (consumes a key)
- **`O`** + direction — Open an unlocked door or chest
- **`S`** + direction — Search an adjacent tile
- **`C`** — Quick-cast *In Lor* (Light)
- **`K` / `D`** — Climb up / Descend stairs & ladders (settlements & dungeons)
- **`Z`** — Toggle Party `Z`tats modal
- **`F1` / `F4`** — Preview Intro (`STORY.DAT`) / Character Creation (`--intro` / `--new-game` CLI flags also supported)
- **`F2`** — Launch a test tactical combat encounter (`A` + direction to attack)
- **`F3`** — Enter Dungeon Deceit (3D dungeon test)
- **`Space`** — Pass turn
- **`Q`** — Save to JSON and quit

## Phases & Status

- [x] **Phase 0: Asset Loaders & Open Data Extraction** — LZW decompressor, `TILES.16` / `DNG1`–`DNG3.16`, fonts, `DATA.OVL` tables, maps, NPCs, dialogues, JSON save/load
- [x] **Phase 1: Core Engine Primitives** — Time/moons/darkness, 11x11 shadowcasting FOV, foot passability, karma, spell mixing/casting, combat math
- [x] **Phase 2: Overworld & EGA Renderer** — 256x256 Britannia/Underworld loop, 320x200 EGA `pygame-ce` renderer, HUD, `L`ook, `Z`tats
- [x] **Phase 3: Settlements, NPC Schedules & Dialogue** — 32 settlements (multi-floor castles/keeps), 24h NPC schedule AI, `.TLK` keyword dialogue, `K`limb stairs, `J`immy/`O`pen
- [x] **Phase 4: Tactical 11x11 Combat** — `BRIT.CBT` / `DUNGEON.CBT` combat, DEX turn queue, ranged/melee attacks, monster AI, XP/gold, flee/victory
- [x] **Phase 5: Magic Effects & Shoppes** — Spell effect handlers, per-merchant shoppe menus (`0x81`–`0x88`)
- [x] **Phase 6: 3D Dungeons** — 8x8x8 toroidal dungeons, `DNG1`–`DNG3` perspective slice rendering, ladders, dungeon room combat
- [x] **Phase 7: Title/Intro, Character Creation, Endgame & Polish** — `STORY.DAT` intro, Gypsy virtue character creation (`QUESTION.DAT`), `END.DAT` victory epilogue, grandfather clock `Look` time display

## Repository Layout

- `pydestiny/` — Python package (`assets/`, `state/`, `engine/`, `ui/`)
- `data/` — Extracted open JSON tables, maps, NPC schedules, dialogues, and initial save
- `assets/` — Rendered EGA tileset (`tiles.png`) and world minimaps
- `docs/` — Reverse-engineering notes ([architecture.md](docs/architecture.md), [overlays.md](docs/overlays.md), [file-formats.md](docs/file-formats.md), [game-logic.md](docs/game-logic.md), [reimplementation-plan.md](docs/reimplementation-plan.md))
- `tools/` — Extraction and binary analysis scripts
- `tests/` — Automated pytest suite
