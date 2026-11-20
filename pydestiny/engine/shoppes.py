"""Shoppes & merchant services (SHOPPES.OVL - SHOPPES3.OVL, SHOPPE.DAT)."""

from __future__ import annotations

from dataclasses import dataclass

from pydestiny.state.savegame import SaveGame


@dataclass(frozen=True)
class ShopItem:
    label: str
    cost: int
    action: str  # 'food', 'reagent', 'heal', 'cure', 'resurrect', 'inn', 'torch', 'gem', 'key'
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

SHOP_MENUS_BY_TALK_ID: dict[int, tuple[str, tuple[ShopItem, ...]]] = {
    0x81: (
        "ARMOURY",
        (
            ShopItem("Food x10", 15, "food", 10),
            ShopItem("Torch x5", 25, "torch", 5),
            ShopItem("Key x2", 40, "key", 2),
        ),
    ),
    0x82: (
        "APOTHECARY",
        (
            ShopItem("Ash x5", 20, "reagent", 0),
            ShopItem("Ginseng x5", 20, "reagent", 1),
            ShopItem("Garlic x5", 20, "reagent", 2),
            ShopItem("Silk x5", 25, "reagent", 3),
            ShopItem("Moss x5", 25, "reagent", 4),
            ShopItem("Pearl x5", 35, "reagent", 5),
            ShopItem("Shade x5", 45, "reagent", 6),
            ShopItem("Mandrake x5", 50, "reagent", 7),
        ),
    ),
    0x83: (
        "TAVERN",
        (
            ShopItem("Ale & Stew", 10, "food", 10),
            ShopItem("Rations x20", 25, "food", 20),
            ShopItem("Feast x50", 55, "food", 50),
        ),
    ),
    0x84: (
        "HEALER",
        (
            ShopItem("Heal Party", 50, "heal", 0),
            ShopItem("Cure Poison", 40, "cure", 0),
            ShopItem("Resurrect", 200, "resurrect", 0),
        ),
    ),
    0x85: (
        "PROVISIONS",
        (
            ShopItem("Food x20", 25, "food", 20),
            ShopItem("Torch x5", 25, "torch", 5),
            ShopItem("Gem x3", 60, "gem", 3),
            ShopItem("Key x2", 40, "key", 2),
        ),
    ),
    0x86: (
        "GUILD SHOPPE",
        (
            ShopItem("Torch x5", 20, "torch", 5),
            ShopItem("Gem x5", 90, "gem", 5),
            ShopItem("Key x3", 50, "key", 3),
        ),
    ),
    0x87: (
        "INNKEEPER",
        (
            ShopItem("Rest at Inn", 30, "inn", 0),
            ShopItem("Rations x20", 25, "food", 20),
        ),
    ),
    0x88: (
        "MAGIC SHOPPE",
        (
            ShopItem("Ash x5", 20, "reagent", 0),
            ShopItem("Ginseng x5", 20, "reagent", 1),
            ShopItem("Garlic x5", 20, "reagent", 2),
            ShopItem("Silk x5", 25, "reagent", 3),
            ShopItem("Gem x3", 60, "gem", 3),
        ),
    ),
}


def get_shop_menu(talk_id: int) -> tuple[str, tuple[ShopItem, ...]]:
    """Return (shop_title, items) for a merchant talk_id."""
    return SHOP_MENUS_BY_TALK_ID.get(talk_id, ("SHOPPE MENU", DEFAULT_SHOP_MENU))


def buy_shop_item(save: SaveGame, item: ShopItem, target_char: int = 0) -> tuple[bool, str]:
    """Execute a shoppe purchase if party has enough gold."""
    if save.gold < item.cost:
        return False, "Not enough gold!"

    if item.action == "food":
        save.gold -= item.cost
        save.food = min(9999, save.food + item.param)
        return True, f"Bought {item.label}"

    if item.action == "torch":
        save.gold -= item.cost
        save.torches = min(99, save.torches + item.param)
        return True, f"Bought {item.label}"

    if item.action == "gem":
        save.gold -= item.cost
        save.gems = min(99, save.gems + item.param)
        return True, f"Bought {item.label}"

    if item.action == "key":
        save.gold -= item.cost
        save.keys = min(99, save.keys + item.param)
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
