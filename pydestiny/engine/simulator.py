"""Headless game simulation driver and trace/transcript instrumentation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Callable

from pydestiny.engine.overworld_session import OverworldSession


@dataclass(frozen=True)
class TraceStep:
    """Single instrumented step in a PyDestiny game simulation."""

    step: int
    action: str
    mode: str
    pos: tuple[int, int, int]
    location_id: int
    gold: int
    food: int
    hp0: int
    karma: int
    time_str: str
    ok: bool
    last_msg: str


def detect_mode(session: OverworldSession) -> str:
    if session.story_seq is not None:
        return "endgame" if session.endgame_won else "intro"
    if session.char_create is not None:
        return "char_create"
    if session.shop_open:
        return "shop"
    if session.talk_session is not None:
        return "talk"
    if session.combat is not None:
        return "combat"
    if session.dungeon is not None:
        return "dungeon"
    if session.settlement is not None:
        return "settlement"
    return "overworld"


class GameSimulator:
    """Drives OverworldSession actions headlessly and records a verified trace/transcript."""

    def __init__(self, session: OverworldSession) -> None:
        self.session = session
        self.trace: list[TraceStep] = []

    def _assert_invariants(self) -> None:
        sg = self.session.save
        assert 0 <= sg.hour < 24, f"Invalid hour: {sg.hour}"
        assert 0 <= sg.minute < 60, f"Invalid minute: {sg.minute}"
        assert sg.gold >= 0, f"Negative gold: {sg.gold}"
        assert sg.food >= 0, f"Negative food: {sg.food}"
        assert 0 <= sg.karma <= 99, f"Out-of-range karma: {sg.karma}"
        if self.session.settlement is not None:
            assert 0 <= sg.x < 32 and 0 <= sg.y < 32, f"Settlement OOB: {(sg.x, sg.y)}"
        elif self.session.dungeon is not None:
            d = self.session.dungeon
            assert 0 <= d.x < 8 and 0 <= d.y < 8 and 0 <= d.z < 8, f"Dungeon OOB: {(d.x, d.y, d.z)}"
        else:
            assert 0 <= sg.x < 256 and 0 <= sg.y < 256, f"World OOB: {(sg.x, sg.y)}"

    def act(self, action_name: str, fn: Callable[[], Any]) -> Any:
        res = fn()
        self._assert_invariants()
        sg = self.session.save
        ok = bool(res) if isinstance(res, bool) else True
        if isinstance(res, tuple) and len(res) >= 1 and isinstance(res[0], bool):
            ok = res[0]
        step = TraceStep(
            step=len(self.trace) + 1,
            action=action_name,
            mode=detect_mode(self.session),
            pos=(sg.x, sg.y, sg.z),
            location_id=sg.location_id,
            gold=sg.gold,
            food=sg.food,
            hp0=sg.characters[0].hp,
            karma=sg.karma,
            time_str=f"{sg.hour:02d}:{sg.minute:02d}",
            ok=ok,
            last_msg=self.session.messages[-1] if self.session.messages else "",
        )
        self.trace.append(step)
        return res

    def to_transcript(self) -> str:
        lines: list[str] = []
        for s in self.trace:
            lines.append(
                f"[{s.step:03d}] {s.mode:<11s} {s.action:<24s} "
                f"pos={s.pos} loc={s.location_id:2d} {s.time_str} "
                f"HP={s.hp0:3d} G={s.gold:4d} ok={str(s.ok):<5s} | {s.last_msg}"
            )
        return "\n".join(lines)

    def to_json(self) -> str:
        return json.dumps([asdict(s) for s in self.trace], indent=2)
