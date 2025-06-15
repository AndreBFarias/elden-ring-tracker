import json
import math
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCES_DIR = PROJECT_ROOT / "data" / "references"

PROXIMITY_THRESHOLD = 15.0


def _dist(a: dict, b: dict) -> float:
    return math.sqrt((a["lat"] - b["lat"]) ** 2 + (a["lng"] - b["lng"]) ** 2)


def main() -> None:
    npcs_path = REFERENCES_DIR / "npcs.json"
    graces_path = REFERENCES_DIR / "graces.json"

    with open(str(npcs_path), encoding="utf-8") as f:
        npcs: list[dict] = json.load(f)

    with open(str(graces_path), encoding="utf-8") as f:
        graces: list[dict] = json.load(f)

    non_dlc_flagged = [g for g in graces if g.get("flag") is not None and g.get("region") != "dlc"]

    matched = 0
    unmatched = 0

    for entry in npcs:
        if entry.get("category") != "npc":
            continue

        if entry.get("region") == "dlc":
            entry["nearby_grace_flag"] = None
            unmatched += 1
            continue

        eligible = non_dlc_flagged
        if not eligible:
            entry["nearby_grace_flag"] = None
            unmatched += 1
            continue

        nearest = min(eligible, key=lambda g: _dist(entry, g))
        d = _dist(entry, nearest)

        if d <= PROXIMITY_THRESHOLD:
            entry["nearby_grace_flag"] = nearest["flag"]
            matched += 1
        else:
            entry["nearby_grace_flag"] = None
            unmatched += 1

    with open(str(npcs_path), "w", encoding="utf-8") as f:
        json.dump(npcs, f, indent=2, ensure_ascii=False)

    total_npc = matched + unmatched
    print(f"NPCs processados: {total_npc}")
    print(f"  Com grace linkada: {matched}")
    print(f"  Sem match (raio > {PROXIMITY_THRESHOLD} ou DLC): {unmatched}")
    print(f"Arquivo salvo: {npcs_path}")


if __name__ == "__main__":
    main()


# "Conhecimento e virtude sao inseparaveis." -- Socrates
