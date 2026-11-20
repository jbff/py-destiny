"""Dialogue script parser and keyword conversation engine (TALK.OVL)."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class NpcDialogue:
    npc_id: int
    name: str
    description: str
    greeting: str
    job: str
    bye: str
    topics: dict[str, str]


def _clean_text(s: str) -> str:
    # Strip <0x..> control markers for clean display while preserving <AVATAR> / <PAUSE>
    s = re.sub(r"<0x[0-9a-fA-F]+>", "", s)
    s = s.replace("<PAUSE>", " ").replace("<END>", "")
    return " ".join(s.split()).strip()


def parse_tlk_script(npc_id: int, raw_script: str) -> NpcDialogue:
    """Parse a decoded .TLK script into structured dialogue fields."""
    fields = [f.strip() for f in raw_script.split("\n| ")]
    name = _clean_text(fields[0]) if len(fields) > 0 else f"NPC #{npc_id}"
    desc = _clean_text(fields[1]) if len(fields) > 1 else ""
    greeting = _clean_text(fields[2]) if len(fields) > 2 else "Hello!"
    job = _clean_text(fields[3]) if len(fields) > 3 else "I have no job."
    bye = _clean_text(fields[4]) if len(fields) > 4 else "Farewell!"

    topics: dict[str, str] = {}
    i = 5
    while i + 1 < len(fields):
        kw_raw = _clean_text(fields[i]).lower()
        resp = _clean_text(fields[i + 1])
        if kw_raw and not kw_raw.startswith("@"):
            for kw in kw_raw.split("/"):
                k = kw.strip()[:4]
                if k:
                    topics[k] = resp
        i += 2

    return NpcDialogue(
        npc_id=npc_id,
        name=name,
        description=desc,
        greeting=greeting,
        job=job,
        bye=bye,
        topics=topics,
    )


class TalkSession:
    """Active conversation with a settlement NPC."""

    def __init__(self, dialogue: NpcDialogue, avatar_name: str = "Avatar") -> None:
        self.dialogue = dialogue
        self.avatar_name = avatar_name or "Avatar"
        self.finished = False

    def _sub(self, text: str) -> str:
        return text.replace("<AVATAR>", self.avatar_name)

    def opening(self) -> str:
        return self._sub(f"You meet {self.dialogue.description}. {self.dialogue.greeting}")

    def ask(self, query: str) -> str:
        q = query.strip().lower()[:4]
        if not q:
            return ""
        if q == "name":
            return self._sub(f"My name is {self.dialogue.name}.")
        if q == "job":
            return self._sub(self.dialogue.job)
        if q == "bye":
            self.finished = True
            return self._sub(self.dialogue.bye)
        if q in self.dialogue.topics:
            return self._sub(self.dialogue.topics[q])
        return "That I cannot help thee with."
