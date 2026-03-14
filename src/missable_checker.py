import functools
import json
from pathlib import Path
from typing import Any

from database import get_boss_kills
from log import get_logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCES_DIR = PROJECT_ROOT / "data" / "references"

logger = get_logger("missable")

STATUS_DISPONIVEL = "disponivel"
STATUS_PERDIDO = "perdido"

SEVERITY_ORDER = {"critical": 0, "moderate": 1, "minor": 2}


@functools.lru_cache(maxsize=1)
def _load_missable_events() -> tuple[dict, ...]:
    path = REFERENCES_DIR / "missable_events.json"
    if not path.exists():
        logger.warning("Arquivo de eventos perdíveis ausente: %s", path)
        return ()
    try:
        with open(str(path), encoding="utf-8") as f:
            return tuple(json.load(f))
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Falha ao carregar eventos perdíveis: %s", exc)
        return ()


def _get_killed_flags(slot_index: int) -> set[int]:
    kills = get_boss_kills(slot_index)
    return {row["boss_flag"] for row in kills}


def evaluate_event(slot_index: int, event: dict, killed_flags: set[int]) -> str:
    loss_flags = event.get("loss_boss_flags", [])
    if loss_flags and any(f in killed_flags for f in loss_flags):
        return STATUS_PERDIDO

    return STATUS_DISPONIVEL


def get_missable_status(slot_index: int) -> list[dict[str, Any]]:
    events = _load_missable_events()
    killed_flags = _get_killed_flags(slot_index)
    result = []

    for event in events:
        status = evaluate_event(slot_index, event, killed_flags)
        result.append({
            "event_id": event["event_id"],
            "name": event["name"],
            "description": event["description"],
            "loss_condition": event["loss_condition"],
            "related_npc": event.get("related_npc", ""),
            "severity": event.get("severity", "moderate"),
            "region": event.get("region", "surface"),
            "status": status,
        })

    result.sort(key=lambda e: SEVERITY_ORDER.get(e["severity"], 99))
    return result


def get_missable_summary(slot_index: int) -> dict[str, int]:
    events = get_missable_status(slot_index)
    summary = {
        STATUS_DISPONIVEL: 0,
        STATUS_PERDIDO: 0,
        "total": len(events),
    }
    for event in events:
        status = event["status"]
        if status in summary:
            summary[status] += 1
    return summary


# "A prudência é a mãe de todas as virtudes." -- Epicuro
