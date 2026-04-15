"""Resolução de subcategorias para itens de equipamento.

Agrupa itens por subcategoria (tipo de arma, slot de armadura, tipo de
feitiço, afinidade de ash of war) a partir do campo 'subcategory' já
presente nos dicts de progresso.
"""
from collections import OrderedDict
from typing import Any

SUBCATEGORY_CATEGORIES = {
    "weapon", "armor", "shield", "spell", "ash_of_war",
}

WEAPON_TYPE_ORDER = [
    "Dagger", "Straight Sword", "Greatsword", "Colossal Sword",
    "Thrusting Sword", "Heavy Thrusting Sword",
    "Curved Sword", "Curved Greatsword",
    "Katana", "Great Katana", "Twinblade",
    "Hammer", "Great Hammer", "Flail",
    "Axe", "Greataxe",
    "Spear", "Great Spear", "Halberd", "Reaper",
    "Whip", "Fist", "Claw", "Colossal Weapon",
    "Light Greatsword", "Backhand Blade", "Throwing Blade",
    "Hand-to-Hand", "Perfume Bottle", "Beast Claw",
    "Torch", "Glintstone Staff", "Sacred Seal",
    "Light Bow", "Bow", "Greatbow", "Crossbow", "Ballista",
]

ARMOR_SLOT_ORDER = ["Head", "Body", "Arms", "Legs"]

SPELL_TYPE_ORDER = ["Sorcery", "Incantation"]

AFFINITY_ORDER = [
    "Standard", "Heavy", "Keen", "Quality",
    "Magic", "Fire", "Flame Art", "Lightning",
    "Sacred", "Poison", "Blood", "Cold", "Occult",
]

SHIELD_TYPE_ORDER = ["Small Shield", "Medium Shield", "Greatshield"]

_ORDER_MAP = {
    "weapon": WEAPON_TYPE_ORDER,
    "shield": SHIELD_TYPE_ORDER,
    "armor": ARMOR_SLOT_ORDER,
    "spell": SPELL_TYPE_ORDER,
    "ash_of_war": AFFINITY_ORDER,
}


def has_subcategories(category: str) -> bool:
    return category in SUBCATEGORY_CATEGORIES


def group_by_subcategory(
    items: list[dict[str, Any]], category: str,
) -> OrderedDict[str, list[dict[str, Any]]]:
    """Agrupa itens por subcategoria, na ordem canônica da categoria.

    Itens sem subcategoria vão para o grupo "Outros".
    """
    order = _ORDER_MAP.get(category, [])
    order_index = {name: i for i, name in enumerate(order)}

    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        sub = item.get("subcategory") or "Outros"
        if sub not in groups:
            groups[sub] = []
        groups[sub].append(item)

    sorted_keys = sorted(
        groups.keys(),
        key=lambda k: (order_index.get(k, 9999), k),
    )

    return OrderedDict((k, groups[k]) for k in sorted_keys)


def get_subcategory_stats(
    items: list[dict[str, Any]], category: str,
) -> OrderedDict[str, dict[str, int]]:
    """Retorna contadores completed/total por subcategoria."""
    grouped = group_by_subcategory(items, category)
    stats: OrderedDict[str, dict[str, int]] = OrderedDict()

    for sub_name, sub_items in grouped.items():
        total = len(sub_items)
        completed = sum(1 for i in sub_items if i.get("completed"))
        stats[sub_name] = {
            "total": total,
            "completed": completed,
            "remaining": total - completed,
        }

    return stats


# "A ordem é a primeira lei do céu." -- Alexander Pope
