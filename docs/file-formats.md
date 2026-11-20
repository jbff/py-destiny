# Ultima V (DOS) — Resource & Data File Formats

Living specification of the data and asset files in `orig/extracted/`.

## File Inventory

| Category | Files | Sizes (bytes) | Notes |
|---|---|---|---|
| **Overworld Maps** | `UNDER.DAT` | 65,536 | `256 x 256` tile grid (1 byte/tile; `0x0c` = rock) |
| | `BRIT.DAT` | 52,480 | 205 non-empty `16 x 16` chunks (256 B each); empty ocean chunks omitted (chunk map in `DATA.OVL`) |
| **Settlement Maps** | `CASTLE.DAT`, `TOWNE.DAT`, `KEEP.DAT`, `DWELLING.DAT` | 16,384 each | 16 maps x `32 x 32` tiles (1,024 B/map) |
| **Settlement NPCs** | `CASTLE.NPC`, `TOWNE.NPC`, `KEEP.NPC`, `DWELLING.NPC` | 4,608 each | NPC schedules & initial placements |
| **Dialogue** | `CASTLE.TLK`, `TOWNE.TLK`, `KEEP.TLK`, `DWELLING.TLK` | 7,979 – 26,835 | Indexed by `(npc_id, offset)` pairs; compressed/encoded text |
| **Dungeons** | `DUNGEON.DAT` | 4,096 | 8 dungeons x 8 levels x `8 x 8` cells |
| **Combat Maps** | `BRIT.CBT` | 5,632 | 16 maps x 352 B |
| | `DUNGEON.CBT` | 39,424 | 112 rooms x 352 B |
| **Pathfinding** | `BRITISH.PTH` | 2,783 | Lord British / castle path data |
| **Tiles & Sprites (16-color)** | `TILES.16`, `ITEMS.16`, `ULTIMA.16`, `CREATE.16`, `TEXT.16`, `STARTSC.16`, `ENDSC.16`, `END1.16`, `END2.16`, `DNG1.16`–`DNG3.16`, `MON0.16`–`MON7.16`, `STORY1.16`–`STORY6.16` | varies | 4-byte little-endian uncompressed size header + compressed payload (e.g. `TILES.16` = `0x00010000` = 65,536 B = 512 `16x16` 4bpp tiles) |
| **Tiles & Sprites (4-color)** | `*.4` (matching `.16` pairs) | varies | 4-byte little-endian uncompressed size header + compressed payload (e.g. `TILES.4` = `0x00008000` = 32,768 B = 512 `16x16` 2bpp tiles) |
| **Bitmaps** | `TITLE.BIT`, `WD.BIT`, `BRITISH.BIT` | 784 – 3,323 | 4-byte little-endian uncompressed size header + compressed payload |
| **Fonts** | `IBM.CH`, `RUNES.CH` | 1,024 each | 128 glyphs x 8 bytes (1bpp `8x8`) |
| | `IBM.HCS`, `RUNES.HCS` | 3,072 each | 128 glyphs x 24 bytes (Hercules) |
| | `PROPORT.PCS` | 802 | Proportional font data |
| **Misc Text & Data** | `QUESTION.DAT`, `SIGNS.DAT`, `SHOPPE.DAT`, `MISCMSG.DAT`, `ENDMSG.DAT`, `LOOK2.DAT`, `KARMA.DAT`, `STORY.DAT`, `END.DAT`, `MISCMAPS.DAT` | 761 – 11,679 | Game text, signs, shops, karma, story |
| **Save / World State** | `INIT.GAM`, `SAVED.GAM` (`__support/save/`) | 4,192 each | Party, roster, inventory, flags |
| | `INIT.OOL`, `BRIT.OOL`, `UNDER.OOL` | 256 each | Overworld object/overlay state |
| | `SAVED.OOL` | 512 | Combined Britannia + Underworld object state |

---

## Verified Format Details

### 1. LZW Graphics & Bitmaps (`*.16`, `*.4`, `*.BIT`)

Verified via [tools/lzw.py](../tools/lzw.py) across all 54 compressed `.16`, `.4`, and `.BIT` files (all except `WD.BIT`, which is uncompressed):

- **Header**: `uint32` little-endian uncompressed size.
- **Payload**: LSB-first variable-width LZW stream starting at 9-bit codes, scaling up to 12-bit (`next_code == 2^code_len`):
  - `0x100`: Reset dictionary (`code_len = 9`, `next_code = 0x102`)
  - `0x101`: End of stream
  - `0x000..0x0FF`: Literal byte
  - `0x102..0xFFF`: Dictionary entries
- **Decompressed Container Layouts**:
  - `TILES.16` (65,536 B): 512 tiles x 128 B (`16x16` packed 4bpp, 8 bytes/row, high nibble = left pixel, low nibble = right pixel; standard 16-color EGA palette).
  - `TILES.4` (32,768 B): 512 tiles x 64 B (`16x16` packed 2bpp, 4 bytes/row).
  - Large `.16`/`.4` containers (`CREATE.16`, `STARTSC.16`, `STORY1.16`–`STORY6.16`, etc.): `uint16 count`, followed by `count` x `uint32` offsets.
  - Sprite/item `.16`/`.4` containers (`ITEMS.16`, `MON0.16`–`MON7.16`, etc.): `uint16 count`, followed by `count` pairs of `(uint16 image_off, uint16 mask_off)` (`2 + count * 4` bytes).
  - `TITLE.BIT`, `BRITISH.BIT`: `uint16 count`, followed by `count` x `uint16` offsets.
  - Every sub-image inside `.16`/`.4`/`.BIT` begins with `(uint16 width, uint16 height)` followed by packed pixel data.
  - `WD.BIT` (uncompressed): `uint16 count` (`1`), `uint16 offset` (`4`), `uint16 width` (`288`), `uint16 height` (`49`), followed by 1bpp pixel data (`36 * 49 = 1764` bytes).

### 2. Dialogue Files (`*.TLK`)

Decoded and verified via [tools/dump_tlk.py](../tools/dump_tlk.py) (`CASTLE.TLK`, `TOWNE.TLK`):
- **Header**: `uint16 count` (e.g. 40 in `CASTLE.TLK`, 48 in `TOWNE.TLK`), followed by `count` pairs of `(uint16 npc_id, uint16 offset)`.
- **Text encoding**:
  - `0x00`: Field/record terminator (Name `|`, Description `|`, Greeting `|`, Job `|`, Bye `|`, Keyword `|`, Response `|`, ...).
  - `0x80..0xFF`: High-bit ASCII (`byte & 0x7F`); `0x81` = Avatar name (`DS:[0x55a8]`), `0x82` = end/return, `0x83` = pause/keypress, `0x87` = keyword OR-separator, `0x8D` = newline, `0x90..0x9F` = script labels/prompts, `0xFF` = end of label block.
  - `0x01..0x7F`: Compressed word-table index into `DATA.OVL` (`0x24F8 + idx * 2`, with `+0x10` applied to each string pointer into the word pool at `DATA.OVL+0x104C+`).

### 3. Overworld Maps (`BRIT.DAT`, `UNDER.DAT`)

- **`UNDER.DAT`** (65,536 B): Raw `256 x 256` tile grid (row-major, 1 byte per tile; `0x0C` = solid rock).
- **`BRIT.DAT`** (52,480 B): 205 chunks of `16 x 16` tiles (256 B each). The `16 x 16` chunk index map is stored in `DATA.OVL` at `0x3886` (`256` bytes):
  - `0x00..0xCC` (`0..204`): Chunk index into `BRIT.DAT` (`chunk_idx * 256`).
  - `0xFF`: Empty ocean chunk (all tile `0x01`).

### 4. Save & Initial Game State (`INIT.GAM`, `SAVED.GAM`)

Total size: 4,192 bytes (`0x1060`).
- **`0x0002..0x0202`**: 16 character records x 32 bytes each (Avatar at index 0, followed by 15 companions: Shamino, Iolo, Mariah, Geoffrey, Jaana, Julia, Dupre, Katrina, Sentri, Gwenno, Johne, Gorn, Maxwell, Toshi, Saduj):
  - `+0x00..0x08`: `name[9]` (8-char null-terminated)
  - `+0x09`: `gender` (`0x0B` = Male, `0x0C` = Female)
  - `+0x0A`: `class` (`'A'` Avatar, `'F'` Fighter, `'B'` Bard, `'M'` Mage)
  - `+0x0B`: `status` (`'G'` Good, etc.)
  - `+0x0C..0x0F`: `str`, `dex`, `int`, `mp` (`uint8` each)
  - `+0x10..0x15`: `hp`, `max_hp`, `exp` (`uint16` each)
  - `+0x16`: `level` (`uint8`)
  - `+0x19`: party slot / membership (`0xFF` = not in party)
  - `+0x1A..0x1F`: equipped item slots (helm, armour, weapon, shield, ring, amulet)

### 5. Settlement NPCs (`*.NPC`)

`CASTLE.NPC`, `TOWNE.NPC`, `KEEP.NPC`, and `DWELLING.NPC` are 4,608 bytes each: **8 settlements x 576 bytes**:
- **`+0x000..+0x1FF`** (512 B): 32 NPC schedule records x 16 bytes each (loaded into `DS:0x5d5e`):
  - `+0x00..0x02`: `ai_type[3]` (3 daily schedule phases)
  - `+0x03..0x05`: `x[3]` (`0..31`)
  - `+0x06..0x08`: `y[3]` (`0..31`)
  - `+0x09..0x0B`: `z[3]` (floor index)
  - `+0x0C..0x0F`: `time[4]` (schedule transition hours)
- **`+0x200..+0x21F`** (32 B): 32 x `uint8` NPC sprite/tile type (e.g. `0x70` = guard).
- **`+0x220..+0x23F`** (32 B): 32 x `uint8` dialogue ID (`0x01..0x7F` = `.TLK` NPC ID, `0x80..0xFE` = shopkeeper/special, `0xFF` = generic guard/no dialogue).

### 6. Combat Maps (`BRIT.CBT`, `DUNGEON.CBT`)

Each combat map is **352 bytes (`11 rows x 32 bytes`)**:
- `BRIT.CBT` (5,632 B): 16 overworld/terrain combat maps.
- `DUNGEON.CBT` (39,424 B): 112 dungeon room maps.
- Per-row layout (32 bytes):
  - `row[0..10]` (11 B): Tile IDs for the `11 x 11` tactical grid.
  - `row[11..31]` (21 B): Packed metadata — row 4 holds party spawn X coordinates (`party_start_x[6]`), row 5 holds up to 16 monster types, row 6 holds 16 monster X coordinates, and row 7 holds 16 monster Y coordinates.




