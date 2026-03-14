import functools
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from progress_tracker import get_progress

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCES_DIR = PROJECT_ROOT / "data" / "references"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("elden_tracker.achievements")
if not logger.handlers:
    logger.setLevel(logging.DEBUG)
    _handler = RotatingFileHandler(
        LOG_DIR / "tracker.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    _handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(_handler)


@functools.lru_cache(maxsize=1)
def _load_achievements() -> tuple[dict, ...]:
    path = REFERENCES_DIR / "achievements.json"
    if not path.exists():
        logger.warning("Arquivo de conquistas ausente: %s", path)
        return ()
    try:
        with open(str(path), encoding="utf-8") as f:
            return tuple(json.load(f))
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Falha ao carregar conquistas: %s", exc)
        return ()


def _get_completed_bosses(slot_index: int) -> set[str]:
    progress = get_progress(slot_index, "boss")
    return {
        item["name"] for item in progress["items"]
        if item["completed"]
    }


def _get_completed_items_manual(slot_index: int) -> set[str]:
    from database import get_collected_items, get_manual_progress

    completed: set[str] = set()
    for entity_type in ("item", "weapon", "armor", "shield", "talisman", "spell",
                         "ash_of_war", "consumable", "material", "key_item"):
        rows = get_manual_progress(slot_index, entity_type)
        completed.update(row["entity_name"] for row in rows if row["completed"])

    for row in get_collected_items(slot_index):
        completed.add(row["item_name"])

    return completed


def resolve_achievement(
    slot_index: int,
    achievement: dict,
    completed_bosses: set[str],
    completed_items: set[str],
) -> dict[str, Any]:
    achievement_id = achievement["achievement_id"]

    required_bosses = achievement.get("required_bosses", [])
    required_items = achievement.get("required_items", [])

    total_required = len(required_bosses) + len(required_items)
    if total_required == 0:
        return {
            "achievement_id": achievement_id,
            "name_pt": achievement["name_pt"],
            "description": achievement["description"],
            "type": achievement["type"],
            "status": "pendente",
            "progress_pct": 0.0,
            "missing_items": [],
        }

    missing_bosses = [b for b in required_bosses if b not in completed_bosses]
    missing_items = [i for i in required_items if i not in completed_items]
    completed_count = total_required - len(missing_bosses) - len(missing_items)
    progress_pct = (completed_count / total_required * 100) if total_required > 0 else 0.0

    if not missing_bosses and not missing_items:
        status = "concluido"
    elif completed_count > 0:
        status = "em_progresso"
    else:
        status = "pendente"

    return {
        "achievement_id": achievement_id,
        "name_pt": achievement["name_pt"],
        "description": achievement["description"],
        "type": achievement["type"],
        "status": status,
        "progress_pct": progress_pct,
        "missing_items": missing_bosses + missing_items,
    }


def get_all_achievements(slot_index: int) -> list[dict[str, Any]]:
    achievements = list(_load_achievements())
    completed_bosses = _get_completed_bosses(slot_index)
    completed_items = _get_completed_items_manual(slot_index)

    results = []
    for ach in achievements:
        if ach["achievement_id"] == "elden_ring_platinum":
            continue
        resolved = resolve_achievement(
            slot_index, ach, completed_bosses, completed_items
        )
        results.append(resolved)

    platinum = next(
        (a for a in achievements if a["achievement_id"] == "elden_ring_platinum"),
        None,
    )
    if platinum:
        all_done = all(r["status"] == "concluido" for r in results)
        total = len(results)
        done = sum(1 for r in results if r["status"] == "concluido")
        results.append({
            "achievement_id": "elden_ring_platinum",
            "name_pt": platinum["name_pt"],
            "description": platinum["description"],
            "type": "misc",
            "status": "concluido" if all_done else "pendente",
            "progress_pct": (done / total * 100) if total > 0 else 0.0,
            "missing_items": [],
        })

    return results


def get_achievement_summary(slot_index: int) -> dict[str, Any]:
    achievements = get_all_achievements(slot_index)
    total = len(achievements)
    done = sum(1 for a in achievements if a["status"] == "concluido")
    in_progress = sum(1 for a in achievements if a["status"] == "em_progresso")

    return {
        "total": total,
        "concluido": done,
        "em_progresso": in_progress,
        "pendente": total - done - in_progress,
        "percentage": (done / total * 100) if total > 0 else 0.0,
    }


# "A vitória pertence ao mais perseverante." -- Napoleão Bonaparte
