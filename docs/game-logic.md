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
| `0x595a` | `+0x03b4` | 512 B | Current dungeon map (`8 levels x 8 x 8` cells; `((z & 0xff) << 6) | (y << 3) | x`) |
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

## 3. Town Loop (`TOWN.OVL`, `LoadSeg = 0x081d`)

- **Initialization (`+0x11f0` / `0x93c0`)**:
  1. On fresh entry (`arg != 0`), clears 31 active object slots (`DS:0x5c62`, 8 B each), sets `DS:[0x58a4] = 1`, loads settlement NPCs (`NPC.OVL+0x0000` via `0x7a76`), and updates NPC schedules for the current hour `DS:[0x587f]` (`NPC.OVL+0x00d6` via `0x7aa6`).
  2. Loads map tiles/objects (`0x85d8`, `0x847e`), initializes up to 32 NPC slots (`0x81d0` / `0x8280`), and redraws UI (`0x0000:0x2900`).
- **Turn Loop (`+0x141e` / `0x95ee`)**:
  1. Checks party status/input (`0x0000:0x39fc`): `1` = pass, `-1` = Blackthorn capture (`BLCKTHRN.OVL` via `0x7a5e`).
  2. Checks castle/keep triggers (`0x0000:0x48a8` -> `CAST2.OVL` via `0x7a6a`).
  3. Exits loop when `DS:[0x5893] == 0` (party left settlement).

## 4. Dungeon Loop (`DUNGEON.OVL`, `LoadSeg = 0x081d`)

- **Entry (`+0x0e2e` / `0x8ffe`)**:
  - Reads current dungeon cell from `DS:0x595a + ((z & 0xff) << 6) + (y << 3) + x`.
  - Upper nibble (`cell & 0xf0`) encodes cell type (open, ladders, chest, fountain, pit, trap, wall, secret door, solid rock `0xb0`, dungeon room `0xd0`); lower nibble encodes subtype/room index.
  - Selects wall/floor tile style (`DS:[0xbb14]`, `DS:[0xbb15]`, `DS:[0x6604]`) based on `location_id - 0x20` (`1..8` = Deceit..Doom).

## 5. Master Command Dispatcher (`0x0000:0x3178`)

Called from overworld/town/dungeon loops for `'A'..'Z'` commands (`'0'..'9'` go to `0x0000:0x4080`):

| Key | Command | Overworld / General | Town | Dungeon |
|---|---|---|---|---|
| `A` | Attack | `MAINOUT.OVL+0x06ec` | `TOWN.OVL+0x09e6` | `DUNGEON.OVL+0x1d4a` |
| `B` | Board | `CMDS.OVL+0x07f6` | — | — |
| `C` | Cast | `CAST.OVL+0x0dba` | `CAST.OVL+0x0dba` | `CAST.OVL+0x0dba` |
| `E` | Enter | `MAINOUT.OVL+0x08de` | — | — |
| `F` | Fire | `CMDS.OVL+0x0aea` | `CMDS.OVL+0x0aea` | — |
| `G` | Get | `SJOG.OVL+0x18ce` | `SJOG.OVL+0x18ce` | `SJOG.OVL+0x18ce` |
| `H` | Hole up | `CMDS.OVL+0x0552` | `CMDS.OVL+0x0552` | `CMDS.OVL+0x0552` |
| `I` | Ignite | `CMDS.OVL+0x0d98` | `CMDS.OVL+0x0d98` | `CMDS.OVL+0x0d98` |
| `J` | Jimmy | `SJOG.OVL+0x0d4a` | `SJOG.OVL+0x0d4a` | `SJOG.OVL+0x0d4a` |
| `K` | Klimb | `CMDS.OVL+0x1c20` | `TOWN.OVL+0x0b82` | `DUNGEON.OVL+0x1e10` |
| `L` | Look | `LOOKOBJ.OVL+0x099c` | `LOOKOBJ.OVL+0x099c` | `DNGLOOK.OVL+0x0000` |
| `M` | Mix | `CMDS.OVL+0x1ad8` | `CMDS.OVL+0x1ad8` | `CMDS.OVL+0x1ad8` |
| `N` | New order | `CMDS.OVL+0x0ddc` | `CMDS.OVL+0x0ddc` | `CMDS.OVL+0x0ddc` |
| `O` | Open | `SJOG.OVL+0x1374` | `SJOG.OVL+0x1374` | `SJOG.OVL+0x1374` |
| `P` | Push | `CMDS.OVL+0x161a` | `CMDS.OVL+0x161a` | `CMDS.OVL+0x161a` |
| `Q` | Quit/Save | `CAST2.OVL+0x10fe` | `CAST2.OVL+0x10fe` | `CAST2.OVL+0x10fe` |
| `R` | Ready | `ZSTATS.OVL+0x1296` | `ZSTATS.OVL+0x1296` | `ZSTATS.OVL+0x1296` |
| `S` | Search | `SJOG.OVL+0x095c` | `SJOG.OVL+0x095c` | `SJOG.OVL+0x095c` |
| `T` | Talk | `TALK.OVL+0x041c` | `TALK.OVL+0x041c` | — |
| `U` | Use | `CAST.OVL+0x1792` | `CAST.OVL+0x1792` | `CAST.OVL+0x1792` |
| `V` | View gem | `LOOKOBJ.OVL+0x10fc` | `LOOKOBJ.OVL+0x10fc` | `DNGLOOK.OVL+0x06a8` |
| `X` | X-it | `CMDS.OVL+0x0eb4` | — | — |
| `Y` | Yell | `CMDS.OVL+0x1418` | `CMDS.OVL+0x1418` | `CMDS.OVL+0x1418` |
| `Z` | Ztats | `ZSTATS.OVL+0x0a3a` | `ZSTATS.OVL+0x0a3a` | `ZSTATS.OVL+0x0a3a` |

