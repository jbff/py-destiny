"""320x200 EGA renderer using pygame-ce, assets/tiles.png, and data/font_ibm.json."""

from __future__ import annotations

import json
from pathlib import Path

import pygame

from pydestiny.assets.graphics import EGA_PALETTE
from pydestiny.assets.open_data import DEFAULT_DATA_DIR
from pydestiny.engine.dungeon_session import FACING_NAMES, is_door_cell, is_wall_cell
from pydestiny.engine.fov import UNSEEN_TILE
from pydestiny.engine.overworld_session import AVATAR_TILE_ID, OverworldSession
from pydestiny.engine.shoppes import DEFAULT_SHOP_MENU

DEFAULT_ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"

SCREEN_W = 320
SCREEN_H = 200
SCALE = 3


class EgaRenderer:
    """Renders the Ultima V 320x200 EGA screen onto a pygame Surface."""

    def __init__(
        self,
        assets_dir: Path = DEFAULT_ASSETS_DIR,
        data_dir: Path = DEFAULT_DATA_DIR,
    ) -> None:
        self.assets_dir = assets_dir
        self._dng_cache: dict[int, dict[int, pygame.Surface]] = {}
        self.canvas = pygame.Surface((SCREEN_W, SCREEN_H))
        sheet = pygame.image.load(str(assets_dir / "tiles.png")).convert()
        self.tiles: list[pygame.Surface] = []
        for tid in range(512):
            tx = (tid % 32) * 16
            ty = (tid // 32) * 16
            surf = pygame.Surface((16, 16))
            surf.blit(sheet, (0, 0), (tx, ty, 16, 16))
            self.tiles.append(surf)

        self.font_glyphs: list[list[int]] = json.loads(
            (data_dir / "font_ibm.json").read_text(encoding="utf-8")
        )
        self._glyph_cache: dict[tuple[int, tuple[int, int, int]], pygame.Surface] = {}

    def _get_glyph(self, code: int, color: tuple[int, int, int]) -> pygame.Surface:
        key = (code, color)
        if key not in self._glyph_cache:
            surf = pygame.Surface((8, 8))
            surf.fill((0, 0, 0))
            rows = self.font_glyphs[code & 0x7F]
            for y, row_bits in enumerate(rows):
                for x in range(8):
                    if row_bits & (0x80 >> x):
                        surf.set_at((x, y), color)
            self._glyph_cache[key] = surf
        return self._glyph_cache[key]

    def draw_text(
        self,
        x: int,
        y: int,
        text: str,
        color: tuple[int, int, int] = EGA_PALETTE[15],
    ) -> None:
        for i, ch in enumerate(text):
            self.canvas.blit(self._get_glyph(ord(ch), color), (x + i * 8, y))

    def _draw_borders(self) -> None:
        blue = EGA_PALETTE[9]
        gray = EGA_PALETTE[7]
        # Viewport border (8..183, 12..187 -> 11x11 tiles = 176x176)
        pygame.draw.rect(self.canvas, blue, (6, 10, 180, 180), 1)
        pygame.draw.rect(self.canvas, gray, (7, 11, 178, 178), 1)
        # Right-side divider lines
        pygame.draw.line(self.canvas, blue, (190, 68), (317, 68), 1)
        pygame.draw.line(self.canvas, blue, (190, 98), (317, 98), 1)

    def render_overworld(self, session: OverworldSession) -> pygame.Surface:
        self.canvas.fill((0, 0, 0))
        self._draw_borders()

        if session.ztats_open:
            self._render_ztats(session)
        elif session.shop_open:
            self._render_shop(session)
        elif session.combat is not None:
            self._render_combat(session)
        elif session.dungeon is not None:
            self._render_dungeon(session)
        else:
            fov = session.get_viewport_fov()
            for vy in range(11):
                for vx in range(11):
                    tid = fov[vy][vx]
                    px = 8 + vx * 16
                    py = 12 + vy * 16
                    if tid != UNSEEN_TILE and 0 <= tid < len(self.tiles):
                        self.canvas.blit(self.tiles[tid], (px, py))
            # Draw settlement NPCs within visible 11x11 FOV
            if session.settlement is not None:
                ox = session.save.x - 5
                oy = session.save.y - 5
                for npc in session.settlement.npcs:
                    if npc.z == session.save.z:
                        vx, vy = npc.x - ox, npc.y - oy
                        if 0 <= vx < 11 and 0 <= vy < 11 and fov[vy][vx] != UNSEEN_TILE:
                            ntid = 256 + npc.sprite
                            if 0 <= ntid < len(self.tiles):
                                self.canvas.blit(self.tiles[ntid], (8 + vx * 16, 12 + vy * 16))
            # Draw Avatar at center (5, 5)
            self.canvas.blit(self.tiles[AVATAR_TILE_ID], (8 + 5 * 16, 12 + 5 * 16))

        # Top-right: Party Roster (slots with party_slot != 0xFF)
        y_cursor = 8
        slot_num = 1
        for ch in session.save.characters:
            if ch.party_slot != 0xFF and slot_num <= 6:
                name = ch.name or "Avatar"
                line = f"{slot_num}-{name[:7]:<7s} {ch.hp:3d}{ch.status}"
                self.draw_text(192, y_cursor, line, EGA_PALETTE[15])
                y_cursor += 9
                slot_num += 1

        # Mid-right: Date, Time, Moons, Food/Gold
        sg = session.save
        t_ph, f_ph = session.moon_phases()
        self.draw_text(192, 72, f"{sg.month:2d}-{sg.day:2d}-{sg.year}", EGA_PALETTE[14])
        self.draw_text(276, 72, f"{sg.hour:02d}:{sg.minute:02d}", EGA_PALETTE[11])
        self.draw_text(192, 81, f"T:{t_ph} F:{f_ph} K:{sg.karma:2d}", EGA_PALETTE[7])
        self.draw_text(192, 90, f"F:{sg.food:<4d} G:{sg.gold:<5d}", EGA_PALETTE[14])

        # Bottom-right: Scrolling message log (last 10 lines, or 9 + talk prompt)
        if session.talk_session is not None:
            log_lines = session.messages[-9:]
            for i, line in enumerate(log_lines):
                self.draw_text(192, 102 + i * 9, line[:16], EGA_PALETTE[7])
            self.draw_text(192, 102 + 9 * 9, f">{session.talk_input[-14:]}_", EGA_PALETTE[14])
        else:
            log_lines = session.messages[-10:]
            for i, line in enumerate(log_lines):
                self.draw_text(192, 102 + i * 9, line[:16], EGA_PALETTE[7])

        # Coordinates footer
        world = f"LOC{sg.location_id:02d}" if session.settlement else ("UNDER" if sg.z >= 0x80 else "BRIT ")
        self.draw_text(8, 1, f"{world} ({sg.x:3d},{sg.y:3d})", EGA_PALETTE[11])
        self.draw_text(192, 1, "E L T Z Q", EGA_PALETTE[8])

        return self.canvas

    def _render_ztats(self, session: OverworldSession) -> None:
        sg = session.save
        self.draw_text(12, 16, "== PARTY ZTATS ==", EGA_PALETTE[14])
        y = 28
        for i, ch in enumerate(sg.characters):
            if ch.party_slot != 0xFF:
                name = (ch.name or "Avatar")[:8]
                self.draw_text(
                    12,
                    y,
                    f"{name:<8s} L{ch.level} HP{ch.hp:3d}/{ch.max_hp:3d}",
                    EGA_PALETTE[15],
                )
                self.draw_text(
                    12,
                    y + 9,
                    f" S{ch.strength:2d} D{ch.dexterity:2d} I{ch.intelligence:2d} MP{ch.mp:2d}",
                    EGA_PALETTE[7],
                )
                y += 20
                if y > 140:
                    break
        self.draw_text(
            12,
            156,
            f"Keys:{sg.keys} Gems:{sg.gems} Tor:{sg.torches}",
            EGA_PALETTE[11],
        )
        self.draw_text(12, 170, "Press Z to close", EGA_PALETTE[14])

    def _render_combat(self, session: OverworldSession) -> None:
        cbt = session.combat
        if cbt is None:
            return
        for y in range(11):
            for x in range(11):
                tid = cbt.tiles[y][x]
                if 0 <= tid < len(self.tiles):
                    self.canvas.blit(self.tiles[tid], (8 + x * 16, 12 + y * 16))
        for actor in cbt.actors:
            if actor.alive and 0 <= actor.tile_id < len(self.tiles):
                px, py = 8 + actor.x * 16, 12 + actor.y * 16
                self.canvas.blit(self.tiles[actor.tile_id], (px, py))
                if cbt.active_actor is actor:
                    pygame.draw.rect(self.canvas, EGA_PALETTE[14], (px, py, 16, 16), 1)

    def _render_shop(self, session: OverworldSession) -> None:
        self.draw_text(12, 16, "=== SHOPPE MENU ===", EGA_PALETTE[14])
        y = 30
        for i, item in enumerate(DEFAULT_SHOP_MENU):
            self.draw_text(
                12,
                y,
                f"{i+1}) {item.label:<12s} {item.cost:3d}g",
                EGA_PALETTE[15],
            )
            y += 12
        self.draw_text(12, 168, "1-9 Buy  Esc Exit", EGA_PALETTE[11])

    def _get_dng_slices(self, style: int) -> dict[int, pygame.Surface]:
        if style not in self._dng_cache:
            dng_dir = self.assets_dir / "dng"
            loaded: dict[int, pygame.Surface] = {}
            for idx in range(28):
                p = dng_dir / f"dng{style}_{idx:02d}.png"
                if p.exists():
                    loaded[idx] = pygame.image.load(str(p)).convert_alpha()
            self._dng_cache[style] = loaded
        return self._dng_cache[style]

    def _render_dungeon(self, session: OverworldSession) -> None:
        dng = session.dungeon
        if dng is None:
            return
        slices = self._get_dng_slices(dng.style)
        vx, vy = 16, 18  # 160x164 centered inside 176x176 viewport
        pygame.draw.rect(self.canvas, (0, 0, 0), (8, 12, 176, 176))

        left_x = (0, 24, 56, 72)
        right_x = (136, 104, 88, 80)
        front_x = (0, 24, 56, 72)
        front_wall_idx = (12, 9, 10, 11)
        front_door_idx = (12, 25, 26, 27)

        view = dng.view_slices(max_depth=3)
        # Draw back-to-front (d=3..0)
        for d in range(3, -1, -1):
            _, left_c, center_c, right_c = view[d]
            if is_wall_cell(left_c) or is_door_cell(left_c):
                idx = (16 + d) if is_door_cell(left_c) else d
                if idx in slices:
                    self.canvas.blit(slices[idx], (vx + left_x[d], vy))
            if is_wall_cell(right_c) or is_door_cell(right_c):
                idx = (20 + d) if is_door_cell(right_c) else (4 + d)
                if idx in slices:
                    self.canvas.blit(slices[idx], (vx + right_x[d], vy))
            if d >= 1 and (is_wall_cell(center_c) or is_door_cell(center_c)):
                idx = front_door_idx[d] if is_door_cell(center_c) else front_wall_idx[d]
                if idx in slices:
                    img = slices[idx]
                    self.canvas.blit(img, (vx + front_x[d], vy))
                    self.canvas.blit(
                        pygame.transform.flip(img, True, False),
                        (vx + 80, vy),
                    )
            # Draw simple perspective markers for ladders/chests/pits in open cells
            hi = center_c & 0xF0
            if hi in (0x10, 0x20, 0x30, 0x40, 0x50, 0x60) and d <= 2:
                half_w = (18, 10, 5)[d]
                cx = vx + 80
                if hi in (0x10, 0x30):  # Ladder up
                    top_y = vy + (14, 38, 58)[d]
                    bot_y = vy + (82, 82, 82)[d]
                    pygame.draw.line(self.canvas, EGA_PALETTE[6], (cx - half_w // 2, top_y), (cx - half_w // 2, bot_y), 1)
                    pygame.draw.line(self.canvas, EGA_PALETTE[6], (cx + half_w // 2, top_y), (cx + half_w // 2, bot_y), 1)
                    for ry in range(top_y + 4, bot_y, 6):
                        pygame.draw.line(self.canvas, EGA_PALETTE[14], (cx - half_w // 2, ry), (cx + half_w // 2, ry), 1)
                if hi in (0x20, 0x30):  # Ladder down
                    top_y = vy + 82
                    bot_y = vy + (150, 126, 106)[d]
                    pygame.draw.line(self.canvas, EGA_PALETTE[6], (cx - half_w // 2, top_y), (cx - half_w // 2, bot_y), 1)
                    pygame.draw.line(self.canvas, EGA_PALETTE[6], (cx + half_w // 2, top_y), (cx + half_w // 2, bot_y), 1)
                    for ry in range(top_y + 4, bot_y, 6):
                        pygame.draw.line(self.canvas, EGA_PALETTE[14], (cx - half_w // 2, ry), (cx + half_w // 2, ry), 1)
                if hi == 0x40:  # Chest
                    fy = vy + (138, 118, 100)[d]
                    pygame.draw.rect(self.canvas, EGA_PALETTE[6], (cx - half_w, fy - half_w // 2, half_w * 2, half_w))
                    pygame.draw.rect(self.canvas, EGA_PALETTE[14], (cx - half_w, fy - half_w // 2, half_w * 2, half_w), 1)
                elif hi == 0x60:  # Pit
                    fy = vy + (142, 120, 100)[d]
                    pygame.draw.ellipse(self.canvas, EGA_PALETTE[8], (cx - half_w, fy - 3, half_w * 2, 6), 1)

        self.draw_text(
            12,
            18,
            f"{dng.name} L{dng.z + 1} {FACING_NAMES[dng.facing]}",
            EGA_PALETTE[14],
        )
