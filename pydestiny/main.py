"""Entry point for PyDestiny (Ultima V Python reimplementation)."""

from __future__ import annotations

import argparse
from pathlib import Path

import pygame

from pydestiny.engine.overworld_session import OverworldSession
from pydestiny.ui.ega_renderer import SCALE, SCREEN_H, SCREEN_W, EgaRenderer

DIR_KEYS = {
    pygame.K_UP: (0, -1),
    pygame.K_w: (0, -1),
    pygame.K_DOWN: (0, 1),
    pygame.K_s: (0, 1),
    pygame.K_LEFT: (-1, 0),
    pygame.K_a: (-1, 0),
    pygame.K_RIGHT: (1, 0),
    pygame.K_d: (1, 0),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="PyDestiny — Ultima V Reimplementation")
    parser.add_argument("--save", type=Path, default=Path("save.json"), help="Save file path")
    args = parser.parse_args()

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W * SCALE, SCREEN_H * SCALE))
    pygame.display.set_caption("PyDestiny — Ultima V")
    clock = pygame.time.Clock()

    session = OverworldSession.from_data_dir(save_path=args.save)
    renderer = EgaRenderer()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if session.talk_session is not None:
                    if event.key == pygame.K_RETURN:
                        session.submit_talk(session.talk_input)
                    elif event.key == pygame.K_ESCAPE:
                        session.talk_session = None
                        session.talk_input = ""
                    elif event.key == pygame.K_BACKSPACE:
                        session.talk_input = session.talk_input[:-1]
                    elif event.unicode and event.unicode.isprintable():
                        session.talk_input += event.unicode
                    continue

                if session.awaiting_look_dir and event.key in DIR_KEYS:
                    dx, dy = DIR_KEYS[event.key]
                    session.look_at(dx, dy)
                    session.awaiting_look_dir = False
                elif session.awaiting_talk_dir and event.key in DIR_KEYS:
                    dx, dy = DIR_KEYS[event.key]
                    session.start_talk(dx, dy)
                    session.awaiting_talk_dir = False
                elif event.key in DIR_KEYS and not session.ztats_open:
                    dx, dy = DIR_KEYS[event.key]
                    session.step_move(dx, dy)
                elif event.key == pygame.K_SPACE and not session.ztats_open:
                    session.pass_turn()
                elif event.key == pygame.K_e and not session.ztats_open:
                    session.enter_location()
                elif event.key == pygame.K_t and not session.ztats_open:
                    session.awaiting_talk_dir = True
                    session.log("Talk-dir?")
                elif event.key == pygame.K_l and not session.ztats_open:
                    session.awaiting_look_dir = True
                    session.log("Look-dir?")
                elif event.key == pygame.K_z:
                    session.ztats_open = not session.ztats_open
                elif event.key == pygame.K_q:
                    session.save.save_json(args.save)
                    session.log("Saved!")
                    running = False

        canvas = renderer.render_overworld(session)
        pygame.transform.scale(canvas, screen.get_size(), screen)
        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    main()
