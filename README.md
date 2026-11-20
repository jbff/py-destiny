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

## Controls (Current Prototype)

- **Arrow keys / `W` `A` `S` `D`** — Move (walk off settlement edge to exit; walk off combat edge to flee)
- **`E`** — Enter settlement at current overworld tile (e.g., Britain `(81, 106)`, LB's Castle `(86, 107)`, Moonglow `(232, 135)`)
- **`T`** + direction — Talk to an adjacent NPC (type `name`, `job`, `bye`, or topic keywords)
- **`L`** + direction — Look at an adjacent tile
- **`Z`** — Toggle Party `Z`tats modal
- **`F2`** — Launch a test tactical combat encounter (`A` + direction to attack)
- **`Space`** — Pass turn
- **`Q`** — Save to JSON and quit

## Repository Layout

- `pydestiny/` — Python package (`assets/`, `state/`, `engine/`, `ui/`)
- `data/` — Extracted open JSON tables, maps, NPC schedules, dialogues, and initial save
- `assets/` — Rendered EGA tileset (`tiles.png`) and world minimaps
- `docs/` — Reverse-engineering notes ([architecture.md](docs/architecture.md), [overlays.md](docs/overlays.md), [file-formats.md](docs/file-formats.md), [game-logic.md](docs/game-logic.md), [reimplementation-plan.md](docs/reimplementation-plan.md))
- `tools/` — Extraction and binary analysis scripts
- `tests/` — Automated pytest suite
