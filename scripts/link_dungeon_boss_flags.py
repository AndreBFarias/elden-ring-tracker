import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCES_DIR = PROJECT_ROOT / "data" / "references"

MANUAL_BOSS_TO_DUNGEON: dict[int, str] = {
    9108: "Lake of Rot",
    9109: "Nokstella, Eternal City",
    9110: "Nokron, Eternal City",
    9111: "Deeproot Depths",
    9112: "Mohgwyn Dynasty Mausoleum",
    9115: "Crumbling Farum Azula",
    9120: "Elphael, Brace of the Haligtree",
    9125: "Subterranean Shunning-Grounds",
    9126: "Ruin-Strewn Precipice",
    9129: "Volcano Manor",
    9132: "Siofra River",
    9133: "Nokron, Eternal City",
    9134: "Nokron, Eternal City",
    9135: "Deeproot Depths",
    9174: "Mohgwyn Dynasty Mausoleum",
    9180: "Castle Morne",
    9181: "Caria Manor",
    9182: "The Shaded Castle",
    9183: "Redmane Castle",
    9184: "Castle Sol",
    30030800: "Spiritcaller Cave",
    30100800: "Auriza Hero's Grave",
    35000850: "Leyndell Catacombs",
    41000800: "Ruined Forge of Starfall Past",
    12010850: "Lake of Rot",
    30200810: "Hidden Path to the Haligtree",
}


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _extract_dungeon_candidate(boss_name: str) -> str | None:
    m = re.search(r"\(([^)]+)\)", boss_name)
    return m.group(1) if m else None


def main() -> None:
    dungeons_path = REFERENCES_DIR / "dungeons.json"
    boss_flags_path = REFERENCES_DIR / "boss_flags.json"

    with open(str(dungeons_path), encoding="utf-8") as f:
        dungeons: list[dict] = json.load(f)

    with open(str(boss_flags_path), encoding="utf-8") as f:
        boss_flags: dict = json.load(f)

    dungeon_lookup: dict[str, int] = {
        _normalize(d["name"]): i for i, d in enumerate(dungeons)
    }

    pending: dict[str, list[int]] = {}

    for flag_id_str, entry in boss_flags.items():
        if entry.get("type") != "dungeon":
            continue
        flag_id = int(flag_id_str)
        boss_name = entry["name"]

        dungeon_name: str | None = None

        if flag_id in MANUAL_BOSS_TO_DUNGEON:
            dungeon_name = MANUAL_BOSS_TO_DUNGEON[flag_id]
        else:
            candidate = _extract_dungeon_candidate(boss_name)
            if candidate:
                idx = dungeon_lookup.get(_normalize(candidate))
                if idx is not None:
                    dungeon_name = dungeons[idx]["name"]

        if dungeon_name:
            if dungeon_name not in pending:
                pending[dungeon_name] = []
            pending[dungeon_name].append(flag_id)
        else:
            print(f"  Sem match: [{flag_id}] {boss_name!r}")

    linked = 0
    for dungeon in dungeons:
        name = dungeon["name"]
        flags = pending.get(name, [])
        if flags:
            dungeon["boss_flags"] = sorted(flags)
            linked += 1
        elif "boss_flags" in dungeon:
            del dungeon["boss_flags"]

    with open(str(dungeons_path), "w", encoding="utf-8") as f:
        json.dump(dungeons, f, indent=2, ensure_ascii=False)

    print(f"\nDungeons linkadas a boss_flags: {linked}/{len(dungeons)}")

    multi = [(d["name"], d["boss_flags"]) for d in dungeons if len(d.get("boss_flags", [])) > 1]
    if multi:
        print(f"Multi-boss dungeons: {len(multi)}")
        for name, flags in multi:
            print(f"  {name}: {flags}")


if __name__ == "__main__":
    main()


# "A ignorância é a noite da mente, uma noite sem lua e sem estrelas." -- Confúcio
