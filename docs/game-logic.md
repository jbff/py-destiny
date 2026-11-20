# Ultima V (DOS) — Game Logic & Memory State

Notes from disassembling `ULTIMA.EXE` and `*.OVL` overlays. All `DS:` offsets are relative to `DATA.OVL` (`0x0f64`).

## 1. In-Memory Game State (`DS:0x55a6` – `0x6606`)

`SAVED.GAM` (`4,192` bytes = `0x1060`) is loaded directly into `DS:0x55a6` (`SAVED.GAM + offset == DS:(0x55a6 + offset)`).

| `DS:` Address | `SAVED.GAM` Offset | Size | Meaning |
|---|---|---|---|
| `0x55a8` | `+0x0002` | 512 B | 16 character records x 32 bytes (index 0 = Avatar) |
| `0x57a8` | `+0x0202` | 2 B | Food (`uint16`) |
| `0x57aa` | `+0x0204` | 2 B | Gold (`uint16`) |
| `0x5850` | `+0x02aa` | 8 B | Reagents (Ash, Ginseng, Garlic, Silk, Moss, Pearl, Nightshade, Mandrake) |
| `0x5874` | `+0x02ce` | 2 B | Year (`uint16`, starts at `139`) |
| `0x587d` | `+0x02d7` | 4 B | Month, Day, Hour, Minute (`uint8` each) |
| `0x5888` | `+0x02e2` | 1 B | Karma (`uint8`, starts at `75`) |
| `0x5893` | `+0x02ed` | 1 B | Location ID (`0` = Overworld, `1..32` = Settlements, `33+` = Dungeons) |
| `0x5895` | `+0x02ef` | 1 B | `z` / World (`0` = Britannia, `0xff` = Underworld; floor index in settlements) |
| `0x5896` | `+0x02f0` | 1 B | Party `x` coordinate |
| `0x5897` | `+0x02f1` | 1 B | Party `y` coordinate |
| `0x5c5a` | `+0x06b4` | 256 B | Active map objects / monsters / vehicles (32 slots x 8 bytes) |
| `0x5d5e` | `+0x07b8` | 512 B | Settlement NPC state table (32 NPCs x 16 bytes) |
| `0x5f5e` | `+0x09b8` | 512 B | Settlement NPC schedule table (32 NPCs x 16 bytes) |

## 2. Overworld Loop (`MAINOUT.OVL`, `LoadSeg = 0x081d`)

- **Entry (`+0x0d22` / `0x8ef2`)**:
  1. Calls `0x81d0` (`+0x0000`) to initialize/load the overworld map (`BRIT.DAT` / `UNDER.DAT` and `*.OOL`).
  2. If `DS:[0x6605] >= 0x40` (returning from a settlement/dungeon on a ship/skiff/horse), allocates a slot in `DS:0x5c5a` via `0x0000:0x38e4` and spawns the vehicle (`0x25` ship or `0x29` skiff/horse) at `(DS:[0x5953], DS:[0x5954])`.
  3. Runs the overworld turn loop at `+0x0a84` (`0x8c54`).
- **Turn Loop (`+0x0a84` / `0x8c54`)**:
  1. Renders viewport (`0x8bea`) and reads input / checks party status (`0x0000:0x39fc`).
  2. Handles special returns: `ax == 1` (party incapacitated/pass), `ax == -1` (Blackthorn capture -> `BLCKTHRN.OVL` via `0x7a5e`).
  3. Checks castle/keep triggers (`0x0000:0x48a8` -> `CAST2.OVL` via `0x7a6a`).
  4. Exits loop if `DS:[0x5893] != 0` (entered settlement or dungeon), returning to `_main` in `ULTIMA.EXE`.
  5. Otherwise dispatches movement / command handling (`0x8768`).
- **Combat Terrain Selector (`+0x0d8c` / `0x8f5c`)**:
  - Returns `3` if `DS:[0x5895] >= 0x80` (Underworld).
  - Otherwise inspects the tile at `(DS:[0x5896], DS:[0x5897])` via `0x0000:0x4402(y, x)` to select the combat map type (`0` for water `0x20..0x26`, `2` for grass/woods `4`, `9..15`, etc.).
