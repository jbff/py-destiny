"""Tactical 11x11 combat engine (COMBAT.OVL, COMSUBS.OVL)."""

from __future__ import annotations

import random
from dataclasses import dataclass

from pydestiny.assets.open_data import OpenTables
from pydestiny.engine.combat_math import (
    apply_party_damage,
    award_exp,
    check_hit,
    effective_dex,
    euclidean_dist,
    roll_1d30,
)
from pydestiny.engine.movement import is_foot_passable
from pydestiny.state.savegame import SaveGame


@dataclass
class CombatActor:
    is_party: bool
    index: int          # character index (0..15) if party, else monster def index (16..47)
    name: str
    x: int
    y: int
    hp: int
    max_hp: int
    dex: int
    attack: int
    defense: int
    attack_range: int
    tile_id: int
    flags: int = 0
    fled: bool = False

    @property
    def alive(self) -> bool:
        return self.hp > 0 and not self.fled


class CombatSession:
    """Manages an 11x11 tactical combat encounter."""

    def __init__(
        self,
        save: SaveGame,
        tables: OpenTables,
        tiles: list[list[int]],
        actors: list[CombatActor],
        rng: random.Random | None = None,
    ) -> None:
        self.save = save
        self.tables = tables
        self.tiles = tiles
        self.actors = actors
        self.rng = rng or random.Random()
        self.turn_queue: list[CombatActor] = []
        self.active_actor: CombatActor | None = None
        self.messages: list[str] = ["Combat!"]
        self.finished = False
        self.victory = False
        self.gold_looted = 0
        self._rebuild_turn_queue()
        self._advance_to_next_party_or_end()

    @classmethod
    def from_cbt_dict(
        cls,
        save: SaveGame,
        tables: OpenTables,
        cbt_data: dict[str, list],
        default_monster_idx: int = 32,  # Orc
        rng: random.Random | None = None,
    ) -> CombatSession:
        tiles = [list(r) for r in cbt_data["tiles"]]
        actors: list[CombatActor] = []

        # Spawn active party members
        class_tiles = {"M": 320, "B": 324, "F": 328, "A": 332}
        p_slot = 0
        for ci, ch in enumerate(save.characters):
            if ch.party_slot != 0xFF and ch.status != "D" and ch.hp > 0 and p_slot < 6:
                sx = int(cbt_data["party_start_x"][p_slot]) % 11
                sy = 9 if p_slot < 3 else 10
                # Compute equipment attack & defense
                atk = ch.strength
                dfn = 0
                rng_dist = 1
                for eq in ch.equipped:
                    if eq != 0xFF and eq < len(tables.item_attack):
                        atk = max(atk, tables.item_attack[eq])
                        dfn += tables.item_defense[eq]
                        rng_dist = max(rng_dist, tables.item_range[eq])
                actors.append(
                    CombatActor(
                        is_party=True,
                        index=ci,
                        name=ch.name or "Avatar",
                        x=sx,
                        y=sy,
                        hp=ch.hp,
                        max_hp=ch.max_hp,
                        dex=ch.dexterity,
                        attack=atk,
                        defense=dfn,
                        attack_range=rng_dist,
                        tile_id=class_tiles.get(ch.char_class, 332),
                        flags=0x80,
                    )
                )
                p_slot += 1

        # Spawn enemies from monster_types / monster_x / monster_y
        m_types = cbt_data["monster_types"]
        m_xs = cbt_data["monster_x"]
        m_ys = cbt_data["monster_y"]
        spawned = 0
        for i in range(16):
            mt = int(m_types[i])
            if mt == 0:
                continue
            if mt in (0x70, 0xA0):
                m_idx = default_monster_idx
            elif 0x80 <= mt <= 0xFC:
                m_idx = 16 + (mt - 0x80) // 4
            else:
                m_idx = max(16, min(47, mt))
            mdef = tables.monsters[m_idx]
            mx, my = int(m_xs[i]) % 11, int(m_ys[i]) % 11
            actors.append(
                CombatActor(
                    is_party=False,
                    index=m_idx,
                    name=mdef.name,
                    x=mx,
                    y=my,
                    hp=mdef.hp,
                    max_hp=mdef.hp,
                    dex=mdef.dexterity,
                    attack=mdef.damage,
                    defense=mdef.armour,
                    attack_range=1,
                    tile_id=384 + (m_idx - 16) * 4,
                    flags=0x40,
                )
            )
            spawned += 1
            if spawned >= 4:
                break

        return cls(save, tables, tiles, actors, rng=rng)

    def _rebuild_turn_queue(self) -> None:
        alive = [a for a in self.actors if a.alive]
        alive.sort(
            key=lambda a: effective_dex(a.dex, a.flags, self.save.active_spell),
            reverse=True,
        )
        self.turn_queue = alive

    def actor_at(self, x: int, y: int) -> CombatActor | None:
        for a in self.actors:
            if a.alive and a.x == x and a.y == y:
                return a
        return None

    def _check_end(self) -> bool:
        party_alive = any(a.is_party and a.alive for a in self.actors)
        enemies_alive = any((not a.is_party) and a.alive for a in self.actors)
        if not enemies_alive:
            self.finished = True
            self.victory = True
            self.messages.append("Victory!")
            return True
        if not party_alive:
            self.finished = True
            self.victory = False
            self.messages.append("Fled/Defeat!")
            return True
        return False

    def _advance_to_next_party_or_end(self) -> None:
        while not self._check_end():
            if not self.turn_queue:
                self._rebuild_turn_queue()
                if not self.turn_queue:
                    break
            actor = self.turn_queue.pop(0)
            if not actor.alive:
                continue
            if actor.is_party:
                self.active_actor = actor
                return
            self._run_monster_turn(actor)
        self.active_actor = None

    def _run_monster_turn(self, monster: CombatActor) -> None:
        targets = [a for a in self.actors if a.is_party and a.alive]
        if not targets:
            return
        target = min(targets, key=lambda p: euclidean_dist(monster.x, monster.y, p.x, p.y))
        dist = euclidean_dist(monster.x, monster.y, target.x, target.y)
        if dist <= monster.attack_range:
            self._resolve_attack(monster, target)
            return

        dx = 1 if target.x > monster.x else (-1 if target.x < monster.x else 0)
        dy = 1 if target.y > monster.y else (-1 if target.y < monster.y else 0)
        for mx, my in ((dx, dy), (dx, 0), (0, dy)):
            if mx == 0 and my == 0:
                continue
            nx, ny = monster.x + mx, monster.y + my
            if 0 <= nx < 11 and 0 <= ny < 11:
                if (
                    is_foot_passable(self.tiles[ny][nx], self.tables.foot_impassable_tiles)
                    and self.actor_at(nx, ny) is None
                ):
                    monster.x, monster.y = nx, ny
                    break

    def _resolve_attack(self, attacker: CombatActor, defender: CombatActor) -> None:
        roll = roll_1d30(self.rng)
        if not check_hit(attacker.dex, defender.dex, roll):
            self.messages.append(f"{attacker.name[:6]} missed!")
            return
        raw_dmg = self.rng.randint(1, max(1, attacker.attack))
        dmg = max(1, raw_dmg - defender.defense // 2)
        if defender.is_party:
            ch = self.save.characters[defender.index]
            killed = apply_party_damage(ch, dmg)
            defender.hp = ch.hp
            self.messages.append(f"{defender.name[:6]} -{dmg}HP")
            if killed:
                self.messages.append(f"{defender.name[:6]} slain!")
        else:
            defender.hp = max(0, defender.hp - dmg)
            self.messages.append(f"{defender.name[:6]} -{dmg}HP")
            if defender.hp == 0:
                self.messages.append(f"{defender.name[:6]} killed!")
                if attacker.is_party:
                    award_exp(self.save.characters[attacker.index], max(5, defender.max_hp))
                loot = self.rng.randint(2, 12)
                self.gold_looted += loot
                self.save.gold += loot

    def move_active(self, dx: int, dy: int) -> bool:
        if self.finished or self.active_actor is None:
            return False
        actor = self.active_actor
        nx, ny = actor.x + dx, actor.y + dy
        if not (0 <= nx < 11 and 0 <= ny < 11):
            actor.fled = True
            self.messages.append(f"{actor.name[:6]} fled!")
            self._advance_to_next_party_or_end()
            return True
        if not is_foot_passable(self.tiles[ny][nx], self.tables.foot_impassable_tiles):
            self.messages.append("Blocked!")
            return False
        if self.actor_at(nx, ny) is not None:
            self.messages.append("Blocked!")
            return False
        actor.x, actor.y = nx, ny
        self._advance_to_next_party_or_end()
        return True

    def attack_dir(self, dx: int, dy: int) -> bool:
        if self.finished or self.active_actor is None:
            return False
        attacker = self.active_actor
        for step in range(1, attacker.attack_range + 1):
            tx = attacker.x + dx * step
            ty = attacker.y + dy * step
            if not (0 <= tx < 11 and 0 <= ty < 11):
                break
            target = self.actor_at(tx, ty)
            if target is not None and not target.is_party:
                self._resolve_attack(attacker, target)
                self._advance_to_next_party_or_end()
                return True
        self.messages.append("Missed!")
        self._advance_to_next_party_or_end()
        return True

    def pass_active(self) -> None:
        if self.finished or self.active_actor is None:
            return
        self.messages.append("Pass")
        self._advance_to_next_party_or_end()
