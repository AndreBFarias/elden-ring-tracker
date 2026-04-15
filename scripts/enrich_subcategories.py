"""Enriquece items.json com subcategory, is_dlc, is_altered e adiciona Spirit Ashes.

Utiliza mapeamentos de weapon_types.json, armor_slots.json, spell_types.json
e ash_of_war_types.json para classificar cada item na subcategoria correta.
"""
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCES_DIR = PROJECT_ROOT / "data" / "references"

ITEMS_PATH = REFERENCES_DIR / "items.json"
ITEM_IDS_PATH = REFERENCES_DIR / "item_ids.json"
WEAPON_TYPES_PATH = REFERENCES_DIR / "weapon_types.json"
ARMOR_SLOTS_PATH = REFERENCES_DIR / "armor_slots.json"
SPELL_TYPES_PATH = REFERENCES_DIR / "spell_types.json"
AOW_TYPES_PATH = REFERENCES_DIR / "ash_of_war_types.json"


def _load_json(path: Path) -> dict | list:
    with open(str(path), encoding="utf-8") as f:
        return json.load(f)


def _strip_location_suffix(name: str) -> str:
    """Remove sufixo de localização do nome: 'Item - Local Name' -> 'Item'."""
    parts = re.split(r" [-\u2013] ", name, maxsplit=1)
    base = parts[0].strip()
    if len(parts) > 1 and len(base) > 3:
        return base
    return name.strip()


def _build_name_to_id_index(item_ids: dict, category: str) -> dict[str, int]:
    entries = item_ids.get(category, {})
    index: dict[str, int] = {}
    for id_str, name in entries.items():
        normalized = name.strip().lower()
        index[normalized] = int(id_str)
    return index


def _lookup_item_id(name: str, name_index: dict[str, int]) -> int | None:
    normalized = name.strip().lower()
    item_id = name_index.get(normalized)
    if item_id is not None:
        return item_id
    stripped = _strip_location_suffix(name).lower()
    return name_index.get(stripped)


def _classify_weapon(name: str, name_index: dict[str, int], weapon_types: dict) -> str:
    item_id = _lookup_item_id(name, name_index)
    if item_id is None:
        return ""
    prefix = str(item_id // 1000000)
    return weapon_types.get(prefix, "")


def _classify_armor_slot(name: str, name_index: dict[str, int], armor_slots: dict) -> str:
    item_id = _lookup_item_id(name, name_index)
    if item_id is None:
        return ""
    suffix = item_id % 10000
    slot_code = str(suffix % 1000)
    return armor_slots.get(slot_code, "")


def _classify_spell(name: str, name_index: dict[str, int], spell_types: dict) -> str:
    item_id = _lookup_item_id(name, name_index)
    if item_id is None:
        return ""
    range_key = item_id // 1000
    if range_key in spell_types["sorcery_ranges"]:
        return "Sorcery"
    if range_key in spell_types["incantation_ranges"]:
        return "Incantation"
    return ""


def _classify_ash_of_war(name: str, aow_types: dict) -> str:
    clean = name.strip()
    if clean in aow_types:
        return aow_types[clean]
    clean_base = re.split(r" [-\u2013] ", clean)[0].strip()
    if clean_base in aow_types:
        return aow_types[clean_base]
    for ref_name, affinity in aow_types.items():
        if ref_name.lower() == clean.lower() or ref_name.lower() == clean_base.lower():
            return affinity
    return ""


def _is_altered(name: str) -> bool:
    return "(Altered)" in name


def _generate_spirit_ash_items(item_ids: dict) -> list[dict]:
    spirit_ashes = item_ids.get("spirit_ash", {})
    items = []
    for id_str, name in spirit_ashes.items():
        item_id = int(id_str)
        is_dlc = item_id >= 2000000
        items.append({
            "name": name,
            "lat": 0.0,
            "lng": 0.0,
            "region": "dlc" if is_dlc else "surface",
            "category": "spirit_ash",
        })
    return items


def main() -> None:
    print("Carregando dados de referência...")
    items = _load_json(ITEMS_PATH)
    item_ids = _load_json(ITEM_IDS_PATH)
    weapon_types = _load_json(WEAPON_TYPES_PATH)
    armor_slots = _load_json(ARMOR_SLOTS_PATH)
    spell_types = _load_json(SPELL_TYPES_PATH)
    aow_types = _load_json(AOW_TYPES_PATH)

    weapon_index = _build_name_to_id_index(item_ids, "weapon")
    shield_index = _build_name_to_id_index(item_ids, "shield")
    armor_index = _build_name_to_id_index(item_ids, "armor")
    spell_index = _build_name_to_id_index(item_ids, "spell")

    weapon_index.update(shield_index)

    stats = {"total": 0, "subcategory_set": 0, "is_dlc_set": 0, "is_altered_set": 0}

    for item in items:
        stats["total"] += 1
        category = item.get("category", "")
        name = item.get("name", "")
        region = item.get("region", "")

        item["is_dlc"] = region == "dlc"
        if item["is_dlc"]:
            stats["is_dlc_set"] += 1

        item["is_altered"] = _is_altered(name)
        if item["is_altered"]:
            stats["is_altered_set"] += 1

        subcategory = ""
        if category == "weapon":
            subcategory = _classify_weapon(name, weapon_index, weapon_types)
        elif category == "shield":
            subcategory = _classify_weapon(name, weapon_index, weapon_types)
        elif category == "armor":
            subcategory = _classify_armor_slot(name, armor_index, armor_slots)
        elif category == "spell":
            subcategory = _classify_spell(name, spell_index, spell_types)
        elif category == "ash_of_war":
            subcategory = _classify_ash_of_war(name, aow_types)

        if subcategory:
            item["subcategory"] = subcategory
            stats["subcategory_set"] += 1
        elif category in ("weapon", "armor", "spell", "shield"):
            item["subcategory"] = ""

    existing_spirit_names = {i["name"] for i in items if i.get("category") == "spirit_ash"}
    spirit_items = _generate_spirit_ash_items(item_ids)
    new_spirits = [s for s in spirit_items if s["name"] not in existing_spirit_names]
    for spirit in new_spirits:
        spirit["is_dlc"] = spirit.get("region") == "dlc"
        spirit["is_altered"] = False
    items.extend(new_spirits)

    with open(str(ITEMS_PATH), "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"\nResultados:")
    print(f"  Total de itens processados: {stats['total']}")
    print(f"  Subcategorias atribuídas: {stats['subcategory_set']}")
    print(f"  Marcados como DLC: {stats['is_dlc_set']}")
    print(f"  Marcados como altered: {stats['is_altered_set']}")
    print(f"  Spirit Ashes adicionados: {len(new_spirits)}")
    print(f"  Total final em items.json: {len(items)}")

    categories = {}
    for item in items:
        cat = item.get("category", "?")
        categories[cat] = categories.get(cat, 0) + 1
    print(f"\nDistribuição por categoria:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    subcats = {}
    for item in items:
        sub = item.get("subcategory")
        if sub:
            subcats[sub] = subcats.get(sub, 0) + 1
    if subcats:
        print(f"\nDistribuição por subcategoria:")
        for sub, count in sorted(subcats.items(), key=lambda x: -x[1]):
            print(f"  {sub}: {count}")


if __name__ == "__main__":
    main()


# "O conhecimento é a única coisa que ninguém pode tirar de você." -- B.B. King
