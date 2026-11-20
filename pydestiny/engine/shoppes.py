"""Shoppes & merchant services (SHOPPES.OVL - SHOPPES3.OVL, SHOPPE.DAT)."""

from __future__ import annotations

from dataclasses import dataclass

from pydestiny.state.savegame import SaveGame


@dataclass(frozen=True)
class ShopItem:
    label: str
    cost: int
    action: str  # 'food', 'reagent', 'heal', 'cure', 'resurrect', 'inn', 'equip'
    param: int = 0


DEFAULT_SHOP_MENU: tuple[ShopItem, ...] = (
    ShopItem("Food x20", 25, "food", 20),
    ShopItem("Heal Party", 50, "heal", 0),
    ShopItem("Cure Poison", 40, "cure", 0),
    ShopItem("Resurrect", 200, "resurrect", 0),
    ShopItem("Rest at Inn", 30, "inn", 0),
    ShopItem("Ash x5", 20, "reagent", 0),
    ShopItem("Ginseng x5", 20, "reagent", 1),
    ShopItem("Garlic x5", 20, "reagent", 2),
    ShopItem("Silk x5", 25, "reagent", 3),
)


def buy_shop_item(save: SaveGame, item: ShopItem, target_char: int = 0) -> tuple[bool, str]:
    """Execute a shoppe purchase if party has enough gold."""
    if save.gold < item.cost:
        return False, "Not enough gold!"

    if item.action == "food":
        save.gold -= item.cost
        save.food = min(9999, save.food + item.param)
        return True, f"Bought {item.label}"

    if item.action == "reagent":
        save.gold -= item.cost
        idx = item.param
        save.reagents[idx] = min(99, save.reagents[idx] + 5)
        return True, f"Bought {item.label}"

    if item.action == "heal":
        save.gold -= item.cost
        for ch in save.characters:
            if ch.party_slot != 0xFF and ch.status != "D":
                ch.hp = ch.max_hp
        return True, "Party healed!"

    if item.action == "cure":
        ch = save.characters[target_char]
        if ch.status != "P":
            return False, "Not poisoned!"
        save.gold -= item.cost
        ch.status = "G"
        return True, "Cured!"

    if item.action == "resurrect":
        dead = [ch for ch in save.characters if ch.party_slot != 0xFF and ch.status == "D"]
        if not dead:
            return False, "No one is dead!"
        save.gold -= item.cost
        dead[0].status = "G"
        dead[0].hp = dead[0].max_hp
        return True, f"{dead[0].name or 'Avatar'} raised!"

    if item.action == "inn":
        save.gold -= item.cost
        for ch in save.characters:
            if ch.party_slot != 0xFF and ch.status != "D":
                ch.hp = ch.max_hp
                ch.mp = min(99, ch.intelligence)
        return True, "Rested well!"

    return False, "Unavailable"
