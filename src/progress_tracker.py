import json
import re
from pathlib import Path
from typing import Any

from database import (
    get_boss_kills,
    get_collected_items,
    get_grace_discoveries,
    get_manual_progress,
)
from log import get_logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCES_DIR = PROJECT_ROOT / "data" / "references"

logger = get_logger("progress")

CATEGORY_FILES = {
    "boss": "bosses.json",
    "grace": "graces.json",
    "dungeon": "dungeon_bosses.json",
    "waygate": "waygates.json",
    "weapon": "items.json",
    "armor": "items.json",
    "shield": "items.json",
    "talisman": "items.json",
    "ash_of_war": "items.json",
    "spirit_ash": "items.json",
    "spell": "items.json",
    "consumable": "items.json",
    "material": "items.json",
    "upgrade_material": "items.json",
    "flask_upgrade": "items.json",
    "key_item": "items.json",
    "map_fragment": "items.json",
    "npc": "npcs.json",
    "npc_invader": "npcs.json",
}


_ref_cache: dict[str, list[dict]] = {}


def _load_reference(category: str) -> list[dict]:
    filename = CATEGORY_FILES.get(category)
    if not filename:
        return []
    path = REFERENCES_DIR / filename
    if not path.exists():
        logger.warning("Referencia ausente: %s", path)
        return []

    if filename not in _ref_cache:
        try:
            with open(str(path), encoding="utf-8") as f:
                _ref_cache[filename] = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Falha ao carregar %s: %s", path, exc)
            return []

    data = _ref_cache[filename]
    if filename == "items.json":
        data = [e for e in data if e.get("category") == category]
    if filename == "npcs.json":
        data = [e for e in data if e.get("category") == category]
    return data


AUTO_TRACKED = {
    "flask_upgrade", "ash_of_war", "map_fragment", "key_item",
    "weapon", "armor", "shield", "talisman", "spell",
    "consumable", "material", "upgrade_material",
    "spirit_ash", "npc",
}

ITEM_CATEGORIES_WITH_NORMALIZATION = {
    "weapon", "armor", "shield", "talisman", "spell",
    "consumable", "material", "upgrade_material", "spirit_ash",
}

_RE_QTY_SUFFIX = re.compile(r"\s+x\d+$")
_RE_QTY_PREFIX = re.compile(r"^(?:\d+x|x\d+)\s+")
_RE_PAREN_NUM = re.compile(r"\((\d+)\)")
_RE_VARIANT_LETTER = re.compile(r"\s+[A-Za-z]$")
_RE_LOCATION_LETTER = re.compile(r"\s*\([A-Z]\)$")
_RE_LOCATION_SUFFIX = re.compile(r"\s+-\s+.+$")
_RE_SET_NO_PIECE = re.compile(r"\s*\(No \w+\)$")
_RE_PAREN_DESCRIPTOR = re.compile(r"\s*\([A-Z][a-z][\w\s',.-]+\)$")
_RE_UPGRADE_LEVEL = re.compile(r"\s*\+\d+$")
_RE_TRAILING_LOCATION = re.compile(r"(\]\s*)\w[\w\s]+$")


def _normalize_item_name(full_name: str) -> str:
    """Normaliza nome de items.json para matching contra item_ids.json.

    Transformacoes:
      'Arrow x10 - Limgrave'                          -> 'Arrow'
      'Ghost Glovewort (3) B'                          -> 'Ghost Glovewort [3]'
      '3x Golden Rune (1) F'                           -> 'Golden Rune [1]'
      'Smithing Stone [1] A'                           -> 'Smithing Stone [1]'
      'Crystal Dart (A)'                               -> 'Crystal Dart'
      'Dragon Heart (Borealis the Freezing Fog)'       -> 'Dragon Heart'
      'Zamor Ice Storm (Spell)'                        -> 'Zamor Ice Storm'
      'Banished Knight's Halberd +8'                   -> 'Banished Knight's Halberd'
      'Somber Smithing Stone [8] Consecrated Snowfield' -> 'Somber Smithing Stone [8]'
    """
    name = _RE_LOCATION_SUFFIX.sub("", full_name).strip()
    name = _RE_QTY_SUFFIX.sub("", name)
    name = _RE_QTY_PREFIX.sub("", name)
    name = _RE_UPGRADE_LEVEL.sub("", name)
    name = _RE_PAREN_DESCRIPTOR.sub("", name)
    name = _RE_PAREN_NUM.sub(r"[\1]", name)
    name = _RE_LOCATION_LETTER.sub("", name)
    name = _RE_TRAILING_LOCATION.sub(r"\1", name)
    name = _RE_VARIANT_LETTER.sub("", name)
    name = re.sub(r"(\])[a-z]$", r"\1", name)
    name = re.sub(r"\s*-x\d+$", "", name)
    return name.strip()


_ITEM_NAME_CORRECTIONS: dict[str, str] = {
    "St Trina's Torch": "St. Trina's Torch",
    "Flame, Grant me Strength": "Flame, Grant Me Strength",
    "Mottled Necklance": "Mottled Necklace",
    "Barbed Staff": "Barbed Staff-Spear",
    "Fire's Deadly": "Fire's Deadly Sin",
    "Glintstab Firefly": "Glintstone Firefly",
    "Ghosflame Bloom": "Ghostflame Bloom",
    "Giantslab Firefly": "Glintstone Firefly",
    "Beast blood": "Beast Blood",
    "Thin Best Bones": "Thin Beast Bones",
    "Velvet Sword of St Trina": "Velvet Sword of St. Trina",
    "Prince of Death Cyst": "Prince of Death's Cyst",
    "Stone-Sheathed Sword Altar": "Stone-Sheathed Sword",
    "Imp Head": "Imp Head (Cat)",
}

_case_index_cache: dict[int, dict[str, str]] = {}


def _build_case_index(auto_completed: set[str]) -> dict[str, str]:
    """Constroi indice lowercase -> original para matching case-insensitive."""
    key = id(auto_completed)
    if key in _case_index_cache:
        return _case_index_cache[key]
    index = {name.lower(): name for name in auto_completed}
    _case_index_cache[key] = index
    return index


def _match_item(
    entry_name: str,
    auto_completed: set[str],
    category: str,
) -> bool:
    """Verifica se uma entrada de items.json foi coletada.

    Para a maioria das categorias, normaliza o nome e compara.
    Para armor sets, verifica se qualquer peca do set esta no inventario.
    Usa matching case-insensitive como fallback.
    """
    if entry_name in auto_completed:
        return True

    norm = _normalize_item_name(entry_name)
    if norm in auto_completed:
        return True

    corrected = _ITEM_NAME_CORRECTIONS.get(norm)
    if corrected:
        norm = _normalize_item_name(corrected)
        if norm in auto_completed:
            return True

    case_index = _build_case_index(auto_completed)
    if norm.lower() in case_index:
        return True

    if category == "armor" and " Set" in norm:
        cleaned = _RE_SET_NO_PIECE.sub("", norm)
        prefix = re.sub(r"\s+Set$", "", cleaned).rstrip()
        if prefix:
            prefix_lower = prefix.lower()
            return any(prefix_lower in item.lower() for item in auto_completed)

    return False


def _get_auto_completed(slot_index: int, category: str) -> set[str]:
    if category == "boss":
        kills = get_boss_kills(slot_index)
        flag_set = {row["boss_flag"] for row in kills}
        ref = _load_reference("boss")
        return {
            entry["name"] for entry in ref
            if entry.get("flag") and entry["flag"] in flag_set
        }
    if category == "grace":
        discoveries = get_grace_discoveries(slot_index)
        flag_set = {row["grace_flag"] for row in discoveries}
        ref = _load_reference("grace")
        return {
            entry["name"] for entry in ref
            if entry.get("flag") and entry["flag"] in flag_set
        }
    if category == "dungeon":
        kills = get_boss_kills(slot_index)
        flag_set = {row["boss_flag"] for row in kills}
        ref = _load_reference("dungeon")
        return {
            entry["name"] for entry in ref
            if entry.get("flag") and entry["flag"] in flag_set
        }
    if category == "npc":
        discoveries = get_grace_discoveries(slot_index)
        discovered_flags = {row["grace_flag"] for row in discoveries}
        ref = _load_reference("npc")
        grace_met = {
            entry["name"] for entry in ref
            if entry.get("nearby_grace_flag") and entry["nearby_grace_flag"] in discovered_flags
        }
        item_met = {row["item_name"] for row in get_collected_items(slot_index, "npc")}
        return grace_met | item_met
    if category == "npc_invader":
        kills = get_boss_kills(slot_index)
        killed_flags = {row["boss_flag"] for row in kills}
        ref = _load_reference("npc_invader")
        boss_defeated = {
            entry["name"] for entry in ref
            if entry.get("boss_flag") and entry["boss_flag"] in killed_flags
        }
        item_col = {row["item_name"] for row in get_collected_items(slot_index, "npc_invader")}
        return boss_defeated | item_col
    if category in AUTO_TRACKED:
        rows = get_collected_items(slot_index, category)
        return {row["item_name"] for row in rows}
    return set()


def _get_manual_completed(slot_index: int, category: str) -> set[str]:
    rows = get_manual_progress(slot_index, category)
    return {row["entity_name"] for row in rows if row["completed"]}


def get_progress(
    slot_index: int, category: str, region: str = ""
) -> dict[str, Any]:
    ref = _load_reference(category)
    if region:
        ref = [e for e in ref if e.get("region") == region]

    all_names = [entry["name"] for entry in ref]
    total = len(all_names)

    auto_completed = _get_auto_completed(slot_index, category)
    manual_completed = _get_manual_completed(slot_index, category)

    use_norm = category in ITEM_CATEGORIES_WITH_NORMALIZATION

    items = []
    for entry in ref:
        name = entry["name"]
        if use_norm:
            is_auto = _match_item(name, auto_completed, category)
        else:
            is_auto = name in auto_completed
        is_manual = name in manual_completed
        is_done = is_auto or is_manual
        item_dict: dict[str, Any] = {
            "name": name,
            "region": entry.get("region", ""),
            "completed": is_done,
            "source": "auto" if is_auto else ("manual" if is_manual else "none"),
        }
        subcategory = entry.get("subcategory")
        if subcategory:
            item_dict["subcategory"] = subcategory
        items.append(item_dict)

    completed_count = sum(1 for i in items if i["completed"])
    remaining = total - completed_count

    return {
        "category": category,
        "region": region,
        "total": total,
        "completed": completed_count,
        "remaining": remaining,
        "percentage": (completed_count / total * 100) if total > 0 else 0.0,
        "items": items,
    }


def get_all_progress(slot_index: int) -> dict[str, dict[str, Any]]:
    result = {}
    for category in CATEGORY_FILES:
        result[category] = get_progress(slot_index, category)
    return result


def get_overall_stats(slot_index: int, region: str = "") -> dict[str, Any]:
    all_prog = {cat: get_progress(slot_index, cat, region=region) for cat in CATEGORY_FILES}
    total = sum(p["total"] for p in all_prog.values())
    completed = sum(p["completed"] for p in all_prog.values())
    return {
        "total": total,
        "completed": completed,
        "remaining": total - completed,
        "percentage": (completed / total * 100) if total > 0 else 0.0,
        "by_category": all_prog,
    }


# "Medir o progresso é o primeiro passo para o domínio." -- Peter Drucker
