"""Phase 7: Title/Intro (STORY.DAT), Character Creation (QUESTION.DAT), and Endgame (END.DAT)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from pydestiny.assets.open_data import DEFAULT_DATA_DIR
from pydestiny.state.savegame import SaveGame


def clean_story_text(text: str) -> str:
    """Strip soft-hyphen underscores and normalize whitespace from STORY/QUESTION/END.DAT."""
    return " ".join(text.replace("_", "").split()).strip()


@dataclass
class StorySequence:
    """Paginated text sequence for Title/Intro (STORY.DAT) or Endgame (END.DAT)."""

    pages: list[str]
    page_idx: int = 0
    finished: bool = False

    @classmethod
    def load_intro(cls, data_dir: Path = DEFAULT_DATA_DIR) -> StorySequence:
        raw: list[str] = json.loads((data_dir / "text" / "story.json").read_text(encoding="utf-8"))
        pages = [clean_story_text(p) for p in raw if clean_story_text(p)]
        return cls(pages=pages)

    @classmethod
    def load_endgame(cls, data_dir: Path = DEFAULT_DATA_DIR) -> StorySequence:
        raw: list[str] = json.loads((data_dir / "text" / "end.json").read_text(encoding="utf-8"))
        pages = [clean_story_text(p) for p in raw if clean_story_text(p)]
        return cls(pages=pages)

    @property
    def current_text(self) -> str:
        if not self.pages or self.page_idx >= len(self.pages):
            return ""
        return self.pages[self.page_idx]

    def advance(self) -> bool:
        if self.page_idx + 1 < len(self.pages):
            self.page_idx += 1
            return True
        self.finished = True
        return False

    def skip(self) -> None:
        self.finished = True


VIRTUE_QUESTIONS: tuple[tuple[str, str, str], ...] = (
    ("Honesty vs Compassion", "A) Speak the blunt truth", "B) Spare their feelings"),
    ("Valor vs Justice", "A) Charge the foe alone", "B) Uphold the law first"),
    ("Sacrifice vs Honor", "A) Give all you own", "B) Keep your sworn oath"),
    ("Spirituality vs Humility", "A) Meditate at the shrine", "B) Serve in silence"),
)


@dataclass
class CharacterCreationState:
    """Interactive Avatar creation & Gypsy virtue questionnaire."""

    intro_blocks: list[str]
    name: str = "Avatar"
    sex: str = "M"
    step: int = 0  # 0=name, 1=sex, 2..5=virtue questions, 6=done
    choices: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, data_dir: Path = DEFAULT_DATA_DIR) -> CharacterCreationState:
        raw: list[str] = json.loads(
            (data_dir / "text" / "question.json").read_text(encoding="utf-8")
        )
        return cls(intro_blocks=[clean_story_text(b) for b in raw if clean_story_text(b)])

    @property
    def done(self) -> bool:
        return self.step >= 2 + len(VIRTUE_QUESTIONS)

    def current_prompt(self) -> tuple[str, str, str]:
        if self.step == 0:
            return ("Enter Avatar's Name:", self.name, "Press Enter to confirm")
        if self.step == 1:
            return ("Select Sex (M/F):", self.sex, "Press M or F")
        q_idx = self.step - 2
        if 0 <= q_idx < len(VIRTUE_QUESTIONS):
            return VIRTUE_QUESTIONS[q_idx]
        return ("Creation Complete!", "", "")

    def answer_choice(self, choice: str) -> None:
        c = choice.strip().upper()
        if self.step == 1 and c in ("M", "F"):
            self.sex = c
            self.step += 1
        elif 2 <= self.step < 2 + len(VIRTUE_QUESTIONS) and c in ("A", "B"):
            self.choices.append(c)
            self.step += 1

    def apply_to_save(self, save: SaveGame) -> None:
        """Apply chosen name, sex, and virtue-derived class/stats to Avatar (slot 0)."""
        avatar = save.characters[0]
        avatar.name = (self.name or "Avatar")[:8]
        avatar.sex = self.sex if self.sex in ("M", "F") else "M"
        a_count = sum(1 for c in self.choices if c == "A")
        if a_count >= 3:
            avatar.char_class = "M"  # Mage
            avatar.intelligence = max(avatar.intelligence, 22)
            avatar.mp = avatar.intelligence
        elif a_count == 2:
            avatar.char_class = "B"  # Bard
            avatar.dexterity = max(avatar.dexterity, 22)
        else:
            avatar.char_class = "F"  # Fighter
            avatar.strength = max(avatar.strength, 22)
