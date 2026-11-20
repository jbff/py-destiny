"""320x200 EGA renderer using pygame-ce, assets/tiles.png, and data/font_ibm.json."""

from __future__ import annotations

import json
from pathlib import Path

import pygame

from pydestiny.assets.graphics import EGA_PALETTE
from pydestiny.assets.open_data import DEFAULT_DATA_DIR
from pydestiny.engine.fov import UNSEEN_TILE
from pydestiny.engine.overworld_session import AVATAR_TILE_ID, OverworldSession

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
        elif session.combat is not None:
            self._render_combat(session)
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
