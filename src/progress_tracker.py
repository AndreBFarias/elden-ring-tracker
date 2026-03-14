import json
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
    "dungeon": "dungeons.json",
    "waygate": "waygates.json",
    "weapon": "items.json",
    "armor": "items.json",
    "shield": "items.json",
    "talisman": "items.json",
    "ash_of_war": "items.json",
    "spell": "items.json",
    "consumable": "items.json",
    "material": "items.json",
    "upgrade_material": "items.json",
    "flask_upgrade": "items.json",
    "key_item": "items.json",
    "map_fragment": "items.json",
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
    return data


AUTO_TRACKED = {
    "flask_upgrade", "ash_of_war", "map_fragment", "key_item",
    "weapon", "armor", "shield", "talisman", "spell",
    "consumable", "material",
}


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
        killed_flags = {row["boss_flag"] for row in kills}
        ref = _load_reference("dungeon")
        completed = set()
        for entry in ref:
            boss_flags = entry.get("boss_flags", [])
            if boss_flags and all(f in killed_flags for f in boss_flags):
                completed.add(entry["name"])
        return completed
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

    items = []
    for entry in ref:
        name = entry["name"]
        is_auto = name in auto_completed
        is_manual = name in manual_completed
        is_done = is_auto or is_manual
        items.append({
            "name": name,
            "region": entry.get("region", ""),
            "completed": is_done,
            "source": "auto" if is_auto else ("manual" if is_manual else "none"),
        })

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
