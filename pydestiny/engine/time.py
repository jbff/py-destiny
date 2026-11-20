"""Time, calendar, moon phases, and day/night darkness (0x0000:0x4f7c, 0x4ae0, 0x475a)."""

from __future__ import annotations

from pydestiny.state.savegame import SaveGame


def advance_time(
    save: SaveGame,
    minutes: int,
    moon_phases: tuple[tuple[int, int], ...] | None = None,
) -> tuple[int, int]:
    """Advance game clock by `minutes` and return updated (trammel_phase, felucca_phase).

    Matches 0x0000:0x4f7c:
    - Quicken ('Q' = 0x51): halves minutes (minimum 1).
    - Time Stop ('T' = 0x54): freezes time progression.
    - 60 min/hr, 24 hr/day, 28 days/month, 13 months/year.
    """
    if minutes <= 0:
        return get_moon_phases(save.day, moon_phases) if moon_phases else (0, 0)

    active = chr(save.active_spell) if save.active_spell else ""
    if active == "Q":
        minutes = max(1, minutes // 2)

    if active != "T":
        total_min = save.minute + minutes
        while total_min > 59:
            total_min -= 60
            save.hour += 1
            if save.hour > 23:
                save.hour = 0
                save.day += 1
                if save.day > 28:
                    save.day = 1
                    for ch in save.characters:
                        if ch.months_in_party < 25:
                            ch.months_in_party += 1
                    save.month += 1
                    if save.month > 13:
                        save.month = 1
                        save.year += 1
        save.minute = total_min

    return get_moon_phases(save.day, moon_phases) if moon_phases else (0, 0)


def get_moon_phases(
    day: int, moon_phases: tuple[tuple[int, int], ...]
) -> tuple[int, int]:
    """Return (trammel_phase, felucca_phase) in 0..7 for day 1..28."""
    idx = max(0, min(day, len(moon_phases) - 1))
    return moon_phases[idx]


def get_moon_sky_positions(hour: int) -> tuple[int | None, int | None]:
    """Return sky positions (0..11, or None if below horizon) for (Trammel, Felucca)."""
    def _pos(offset: int) -> int | None:
        p = offset - hour
        if p < -12:
            p += 24
        return p if 0 <= p < 12 else None

    return _pos(8), _pos(2)


def update_darkness(current_darkness: int, hour: int) -> int:
    """Update DS:[0x5887] day/night darkness level (0..16) per 0x0000:0x475a."""
    if hour >= 20 or hour < 5:
        return min(16, current_darkness + 1)
    return max(0, current_darkness - 1)
