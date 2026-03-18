"""Integra story flags documentados no sprint3.md em story_flags.json.

Expande os 13 flags atuais com endings, mending runes, milestones e world events.
"""

import json
from pathlib import Path

from log import get_logger

logger = get_logger("integrate_story")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCES_DIR = PROJECT_ROOT / "data" / "references"

STORY_FLAGS_COMPLETE = [
    {"flag_id": 20, "name": "Playthrough Complete: Age of Fracture", "type": "ending"},
    {"flag_id": 21, "name": "Playthrough Complete: Age of Stars", "type": "ending"},
    {"flag_id": 22, "name": "Playthrough Complete: Lord of the Frenzied Flame", "type": "ending"},
    {"flag_id": 23, "name": "Playthrough Complete: Unused Ending A", "type": "ending"},
    {"flag_id": 24, "name": "Playthrough Complete: Unused Ending B", "type": "ending"},

    {"flag_id": 100, "name": "Story: Start", "type": "milestone"},
    {"flag_id": 102, "name": "Story: Reached Limgrave", "type": "milestone"},
    {"flag_id": 104, "name": "Story: Reached Roundtable Hold", "type": "milestone"},
    {"flag_id": 108, "name": "Story: Received the Frenzied Flame", "type": "milestone"},
    {"flag_id": 110, "name": "Story: Reached Forge of the Giants", "type": "milestone"},
    {"flag_id": 111, "name": "Story: Forge of the Giants - Melina Variant A", "type": "milestone"},
    {"flag_id": 112, "name": "Story: Forge of the Giants - Melina Variant B", "type": "milestone"},
    {"flag_id": 114, "name": "Story: Ranni Questline Complete", "type": "milestone"},
    {"flag_id": 116, "name": "Story: Frenzied Flame Nullified (Miquella's Needle)", "type": "milestone"},
    {"flag_id": 118, "name": "Story: Erdtree on Fire", "type": "milestone"},
    {"flag_id": 120, "name": "Story: Game Completed", "type": "milestone"},
    {"flag_id": 128, "name": "Story: Entered Shadow of the Erdtree", "type": "milestone"},
    {"flag_id": 130, "name": "Story: Entered Stormveil Castle", "type": "milestone"},
    {"flag_id": 131, "name": "Story: Entered Raya Lucaria Academy", "type": "milestone"},
    {"flag_id": 132, "name": "Story: Entered Leyndell Royal Capital", "type": "milestone"},
    {"flag_id": 133, "name": "Story: Entered Volcano Manor", "type": "milestone"},
    {"flag_id": 134, "name": "Story: Entered Crumbling Farum Azula", "type": "milestone"},
    {"flag_id": 135, "name": "Story: Entered Miquella's Haligtree", "type": "milestone"},
    {"flag_id": 140, "name": "Story: Entered Mohgwyn Palace", "type": "milestone"},

    {"flag_id": 300, "name": "World Event: Erdtree Burnt (Leyndell Transformation)", "type": "world_event"},
    {"flag_id": 301, "name": "World Event: Flaming Sparks", "type": "world_event"},
    {"flag_id": 302, "name": "World Event: Small Flames", "type": "world_event"},
    {"flag_id": 310, "name": "World Event: Green Meteorite (Nokron Access)", "type": "world_event"},
    {"flag_id": 320, "name": "World Event: Carian Study Hall Reversal", "type": "world_event"},
    {"flag_id": 330, "name": "World Event: Romina Defeated (DLC Progression)", "type": "world_event"},

    {"flag_id": 9500, "name": "Obtained Mending Rune of Perfect Order", "type": "mending_rune"},
    {"flag_id": 9502, "name": "Obtained Mending Rune of the Death-Prince", "type": "mending_rune"},
    {"flag_id": 9504, "name": "Obtained Mending Rune of the Fell Curse", "type": "mending_rune"},
]


def main() -> None:
    path = REFERENCES_DIR / "story_flags.json"
    try:
        with open(path, encoding="utf-8") as f:
            current = json.load(f)
    except (OSError, json.JSONDecodeError):
        current = []

    current_ids = {entry["flag_id"] for entry in current}
    logger.info("story_flags.json atual: %d entradas", len(current))

    updated = list(STORY_FLAGS_COMPLETE)
    existing_ids = {entry["flag_id"] for entry in updated}

    for entry in current:
        if entry["flag_id"] not in existing_ids:
            updated.append(entry)

    updated.sort(key=lambda x: x["flag_id"])

    with open(path, "w", encoding="utf-8") as f:
        json.dump(updated, f, indent=2, ensure_ascii=False)
        f.write("\n")

    new_count = len(updated) - len(current)
    logger.info(
        "story_flags.json salvo: %d entradas (+%d novas)", len(updated), new_count,
    )

    by_type: dict[str, int] = {}
    for entry in updated:
        t = entry.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    for t, count in sorted(by_type.items()):
        logger.info("  %s: %d", t, count)


if __name__ == "__main__":
    main()


# "O progresso nao e feito por pessoas satisfeitas." -- Frank Tyger
