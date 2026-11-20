# Ultima V (DOS) — Game Logic & Memory State

Notes from disassembling `ULTIMA.EXE` and `*.OVL` overlays. All `DS:` offsets are relative to `DATA.OVL` (`0x0f64`).

## 1. In-Memory Game State (`DS:0x55a6` – `0x6606`)

`SAVED.GAM` (`4,192` bytes = `0x1060`) is loaded directly into `DS:0x55a6` (`SAVED.GAM + offset == DS:(0x55a6 + offset)`).

| `DS:` Address | `SAVED.GAM` Offset | Size | Meaning |
|---|---|---|---|
| `0x55a8` | `+0x0002` | 512 B | 16 character records x 32 bytes (index 0 = Avatar) |
| `0x57a8` | `+0x0202` | 2 B | Food (`uint16`) |
| `0x57aa` | `+0x0204` | 2 B | Gold (`uint16`) |
| `0x57f0` | `+0x024a` | 48 B | Prepared spell counts (48 spells, capped at `99`) |
| `0x5850` | `+0x02aa` | 8 B | Reagents (Ash, Ginseng, Garlic, Silk, Moss, Pearl, Nightshade, Mandrake) |
| `0x5874` | `+0x02ce` | 2 B | Year (`uint16`, starts at `139`) |
| `0x587a` | `+0x02d4` | 1 B | Active spell effect (`'Q'` Quicken, `'T'` Time Stop, etc.) |
| `0x587d` | `+0x02d7` | 5 B | Month (`1..13`), Day (`1..28`), Hour (`0..23`), PrevHour, Minute (`0..59`) |
| `0x5888` | `+0x02e2` | 1 B | Karma (`uint8`, starts at `75`) |
| `0x5893` | `+0x02ed` | 1 B | Location ID (`0` = Overworld, `1..32` = Settlements, `33+` = Dungeons) |
| `0x5895` | `+0x02ef` | 1 B | `z` / World (`0` = Britannia, `0xff` = Underworld; floor index in settlements) |
| `0x5896` | `+0x02f0` | 1 B | Party `x` coordinate |
| `0x5897` | `+0x02f1` | 1 B | Party `y` coordinate |
| `0x58a6` | `+0x0300` | 2 B | Active spell duration (`0x58a6`) and torch duration (`0x58a7`) |
| `0x595a` | `+0x03b4` | 512 B | Current dungeon map (`8 levels x 8 x 8` cells; `((z & 0xff) << 6) | (y << 3) | x`) |
| `0x5c5a` | `+0x06b4` | 256 B | Active map objects / monsters / vehicles (32 slots x 8 bytes) |
| `0x5d5e` | `+0x07b8` | 512 B | Settlement NPC schedule table from `*.NPC` (32 NPCs x 16 bytes) |
| `0x5f5e` | `+0x09b8` | 512 B | Settlement NPC runtime state table (32 NPCs x 16 bytes) |

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

## 6. Magic & Reagent Mixing (`CMDS.OVL+0x1ad8`, `CAST.OVL`)

- **Spell List (`DATA.OVL+0x0709`)**: 48 null-terminated spell names (8 circles x 6 spells, starting with `In Lor`, `Grav Por`, `An Zu`, `An Nox`, `Mani`, ...).
- **Reagent Recipes (`DATA.OVL+0x1cd0`)**: 48-byte bitmask table (1 byte per spell; bit `7` = Ash `0x80` down to bit `0` = Mandrake `0x01`, matching `DS:0x5850[0..7]`). Dumpable via [dump_tables.py](../tools/dump_tables.py).
- **Mixing (`CMDS.OVL+0x1ad8`)**:
  1. Verifies total reagent count across `DS:0x5850..0x5857 > 0`.
  2. Prompts spell selection (`ZSTATS.OVL` via `0x808e`) and reagent selection (`0xd83e`), then computes max mixable quantity (`0xd9f0`).
  3. Subtracts consumed reagents from `DS:0x5850[0..7]` and, if the reagent bitmask matches the recipe (`DS:[0x1cc0 + spell_id]` in code / `DATA.OVL+0x1cd0`), increments prepared count `DS:[0x57f0 + spell_id]` (capped at `0x63` = 99).

## 7. Sound & Timing (`ULTIMA.EXE`)

- **PC Speaker SFX (`0x0000:0x21fc`–`0x2315`)**: Drives the PC speaker directly via `in/out 0x61` (and PIT timer). The DOS version of Ultima V has PC speaker sound effects only (no AdLib/MT-32 music).
- **Animation / Delay Tick (`0x0000:0x3ae6`)**: Runs `n` ticks of `0x0000:0x5910` (animation/world tick) + `0x0000:0x20fa(1)` (delay).

## 8. Tile Passability (`0x0000:0x2bd4`, `0x2c2e`, `0x2c4c`)

- **Transport Mode (`DS:0x54f4 + (actor_tile >> 2)`)**: Dispatches passability rules by transport/movement mode.
- **Foot-Impassable Bitmask (`DATA.OVL+0x54d4`, 32 bytes = 256 bits)**:
  - Bit `(0x80 >> (tile_id & 7))` in byte `tile_id >> 3`: `1` = blocked on foot, `0` = passable.
  - Tiles `0x90..0x93` (doors/barriers) are additionally blocked unless `(mode & 0xfe) == 0x1c` or `(mode & 0xf0) == 0x40`.
- **Water Passability (`0x0000:0x2c2e`)**: Returns `1` if `tile_id < 4` (water) or `(tile_id & 0xf0) == 0x60` (bridges/moongate/whirlpool).

## 9. Monster & Actor Stat Table (`DATA.OVL+0x13cc`–`0x154b`)

48 records x 8 bytes (`COMBAT.OVL+0x1480` indexes `0x13bc`/`0x13bf` in code, aligned to `DATA.OVL+0x13cc`):
- Indices `0..15`: 16 human/NPC classes (including Blackthorn/Lord British at `13..15` with `30, 30, 30, 30, 99 HP`).
- Indices `16..47`: 32 monster types (`Sea Horse`..`Shadow Lord`, names at `DATA.OVL+0x023e`).
- Per-record 8-byte layout: `[STR, DEX, INT, ARM, DMG, HP, MaxSpawn, Special]`.
- Combat actor state is stored in `DS:0xba16` (8 bytes per actor: `x` at `+0x04`, `y` at `+0x05`, type/index at `+0x02`–`+0x03`).

## 10. Equipment Stats & Combat Formulas (`COMBAT.OVL`, `COMSUBS.OVL`)

- **Equipment Tables (`DATA.OVL`)**:
  - `0x1614`–`0x1643` (48 B): Weapon/item Attack / Damage (e.g., `99` = Glass Sword, `30` = Mystic Sword / Magic Axe).
  - `0x1644`–`0x1673` (48 B): Armour / Shield / Helm Defense (`1` = Leather Helm, `2` = Spiked Helm, `3..5` = Shields, `1..10` = Cloth..Mystic Armour).
  - `0x16ac`–`0x16db` (48 B): Weapon Range (`8` = bows/slings, `2..3` = halberd/axe, `1` = melee).
- **Effective DEX (`COMBAT.OVL+0x139a`)**: Returns `1` if Time Stop (`DS:[0x587a] == 'T'`) is active on an enemy (`flags & 0x40`) or if actor is asleep/paralyzed (`flags & 8`); otherwise returns `actor.dex`.
- **Hit / Miss Formula (`COMBAT.OVL+0x14d6`)**:
  1. `threshold = (attacker_stat - defender_stat + 30) // 2`
  2. `roll = roll_1d30()` (`0x0000:0x3abe` -> `rand(60) >> 1`, clamped `>= 1`, range `1..29`).
  3. Returns `0` (**HIT**) if `roll < threshold`, or `1` (**MISS**) if `roll >= threshold`.
- **Apply Damage (`COMBAT.OVL+0x1574`)**:
  - For party members (`flags & 0x80`): subtracts `dmg` from `char.hp` (`DS:0x55b8`). If `hp < 1` or `dmg == 99`, sets `hp = 0`, `flags |= 0x20` (dead), `status = 'D'` (`0x44`), places corpse tile `0x1e`, and clears active turn if `DS:[0x587b] == char_idx`.
- **Distance (`COMSUBS.OVL+0x048a` / `0x04d4`)**: Integer Euclidean distance `isqrt(dx^2 + dy^2)` via odd-number subtraction.

## 11. NPC Schedules (`NPC.OVL+0x00d6`)

- `NPC.OVL+0x00d6(hour)` iterates NPCs `1..31` (skipping entries where `DS:[0x659e + npc_idx] == 0`):
  1. Resolves active schedule slot (`0..2`) for `hour` via `0xb570(hour, npc_idx)`.
  2. Copies `(x, y, z)` from `DS:0x5d5e` (`*.NPC` schedule record) into runtime NPC state `DS:0x5f5e` (`target_x` at `+0x04`, `target_y` at `+0x06`, `sprite` at `+0x08`, `sched_idx` at `+0x0e`).

## 12. Time, Calendar & Active Spell Effects (`0x0000:0x4f7c`)

`advance_time(minutes)`:
1. If `DS:[0x587a] == 'Q'` (Quicken): halves `minutes` (clamped `>= 1`).
2. If `DS:[0x587a] != 'T'` (Time Stop freezes time):
   - Adds `minutes` to `DS:[0x5881]` (minute) and decrements `DS:[0x58a6]` (spell duration) and `DS:[0x58a7]` (torch duration).
3. **Rollover**:
   - `minute > 59`: subtracts `60`, decrements `DS:[0x588c]`, increments `hour` (`DS:[0x587f]`).
   - `hour > 23`: resets `hour = 0`, increments `day` (`DS:[0x587e]`).
   - `day > 28` (`0x1c`): resets `day = 1`, clears monthly flags (`DS:0x5858..0x585a`, `0x57b2`, `0x5959`), increments `char[+0x17]` (months in party, capped at `25`) for all 16 characters, and increments `month` (`DS:[0x587d]`).
   - `month > 13` (`0x0d`): resets `month = 1` and increments `year` (`DS:[0x5874]`).

## 13. Moon Phases & Sky Position (`0x0000:0x4ae0`)

- **Phase Lookup Table (`DATA.OVL+0x1ee8`, 29 x 2 bytes)**:
  - `DS:[0x5885]` = Trammel phase (`'0'..'7'` / `0x30..0x37`, 14-day cycle repeating on days 15–28).
  - `DS:[0x5886]` = Felucca phase (`'0'..'7'` / `0x30..0x37`, 9-day cycle).
- **Sky Visibility (`0x0000:0x4aee`–`0x4b48`)**:
  - Trammel position: `(8 - hour)` (wrapped `+24` if `< -12`), visible when `0 <= pos < 12`.
  - Felucca position: `(2 - hour)` (wrapped `+24` if `< -12`), visible when `0 <= pos < 12`.

## 14. Karma Rules (`DS:[0x5888]`)

Karma starts at `75` (`INIT.GAM+0x02e2`, `0..99` range) and is adjusted by player actions:
- **Lockpicking / Opening owned doors or chests in settlements (`SJOG.OVL+0x11f0`)**: `-2` Karma (clamped `>= 0`) when `location_id <= 0x20`.
- **Stealing / Getting owned items (`SJOG.OVL+0x1a50`)**: `-1` Karma and alerts guards (`DS:[0xa9fa] = 1`).
- **Attacking friendly NPCs (`TOWN.OVL+0x0ae8`)**: `-5` Karma (via `0x0000:0x3f36`, saturating at `0`) and turns town hostile (`0x8b28`).
- Additional Karma modifiers exist in `BLCKTHRN.OVL`, `CAST2.OVL`, `CMDS.OVL`, `SHOPPES2.OVL`, and `TALK.OVL` (dialogue choices, shrine meditation, donations).

## 15. Lighting, Darkness & Viewport (`0x0000:0x475a`, `0x5910`)

- **Day / Night Darkness (`DS:[0x5887]`)**:
  - Nighttime (`hour >= 20` or `hour < 5`): increments `DS:[0x5887]` up to `16` (`0x10`).
  - Daytime (`5 <= hour < 20`): decrements `DS:[0x5887]` down to `0` (full visibility radius `5`, `11 x 11` viewport).
- **Light Sources (`DS:0x5830`, `DS:0x5838`, `DS:[0x58a5]`)**: Up to 8 map light sources plus party torch/spell radius `DS:[0x58a5]` are evaluated before rendering the `11 x 11` viewport (`0x0000:0x70a6`); occluded/unlit tiles in the viewport buffer are marked `0xFF`.

## 16. Spell Casting Rules (`CAST.OVL+0x0dba`)

1. Prompts for caster and spell (`0..47`), computing `circle = (spell_id // 6) + 1` and storing `circle` in `DS:[0x588f]`.
2. Checks castability flags at `DATA.OVL+0x1ca0` (`DS:0x1c90` in code): bit `0x08` = Overworld (`location_id == 0`), bit `0x01` = Combat (`location_id >= 0x80`), and town/dungeon bits.
3. Requires `prepared_count[spell_id] > 0` (`DS:0x57f0`), `caster.mp >= circle`, and `caster.level >= circle` (`char[+0x16]`), then consumes 1 prepared spell and `circle` MP (or plays fizzle SFX via `0x0000:0x43ae(0x320, 0x7d0, 1, 0x32)` on failure).
4. Dispatches via the 48-entry jump table at `CAST.OVL+0x1146` into `CAST.OVL` / `CAST2.OVL` handlers (e.g., `In Lor`/`Vas Lor` -> `CAST2.OVL+0x08ea`, `Rel Hur` -> `CAST2.OVL+0x0306`, `An Grav` -> `CAST2.OVL+0x07bc`, `In Sanct` -> `CAST2.OVL+0x08f8`, `In Ex Por` -> `CAST2.OVL+0x0768`).

## 17. 3D Dungeon Rendering (`DUNGEON.OVL`, `DNG1`–`DNG3.16`)

- **Facing & Level**: `DS:[0x6603]` stores party facing (`0..3` = North/East/South/West); `DS:[0x5895] + 1` (`1..8`) is the dungeon depth.
- **3D Perspective Slices**: `DNG1.16`, `DNG2.16`, and `DNG3.16` (and `.4` CGA equivalents) each decompress to `54,666` bytes containing **28 perspective wall/door/corridor sprites** (`uint32` offset table, widths `8`/`16`/`24`/`32` x height `164`).
- **Ceiling & Floor (`DUNGEON.OVL+0x0332`)**: Fills the 3D viewport ceiling and floor (`0x0000:0x0aa6`) using style colors `DS:[0x13b2]` / `DS:[0x13b0]` selected by `location_id - 0x20`.

## 18. Shoppes & Services (`SHOPPES.OVL`–`SHOPPES3.OVL`, `SHOPPE.DAT`)

- Triggered from `TALK.OVL+0x03d3` when an NPC's dialogue ID is `0xFE` (`254`, merchant/service NPC).
- Shoppe names (Taverns, Stables, Shipwrights, Herbalists/Alchemists, Guilds, Healers, etc.) live in `DATA.OVL+0x0cb1+`, and shopkeeper dialogue is loaded from `SHOPPE.DAT` (word-compressed with `DATA.OVL+0x24F8` + `0x80`).







