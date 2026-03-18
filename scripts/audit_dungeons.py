"""Auditoria de dungeons: classifica com dungeon_type semantico e linka grace flags.

Classifica as 306 entradas de dungeons.json com base no nome.
Cross-reference com grace_flags.json para adicionar grace_flag linkage.
Re-executa logica de link_dungeon_boss_flags.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fetch_utils import (
    REFERENCES_DIR,
    backup_file,
    load_json,
    normalize_name,
    save_json,
)
from log import get_logger

logger = get_logger("audit_dungeons")

DUNGEON_TYPE_PATTERNS: dict[str, list[str] | None] = {
    "catacomb": ["Catacombs", "Hero's Grave"],
    "cave": ["Cave", "Grotto", "Hideaway"],
    "tunnel": ["Tunnel"],
    "gaol": ["Gaol"],
    "evergaol": ["Evergaol"],
    "divine_tower": ["Divine Tower"],
    "legacy_dungeon": [
        "Stormveil Castle", "Raya Lucaria Academy", "Volcano Manor",
        "Leyndell", "Elphael", "Haligtree", "Crumbling Farum Azula",
        "Miquella's Haligtree", "Castle Morne", "Caria Manor",
        "The Shaded Castle", "Redmane Castle", "Castle Sol",
        "Belurat", "Shadow Keep", "Enir-Ilim",
        "Mohgwyn", "Subterranean Shunning-Grounds",
    ],
    "ruins": ["Ruins"],
    "church": ["Church", "Chapel", "Cathedral"],
    "rise": ["Rise"],
    "fort": ["Fort ", "Fort,"],
    "shack": ["Shack"],
    "minor_erdtree": ["Minor Erdtree"],
    "forge": ["Forge"],
    "waygate": ["Waygate", "Sending Gate"],
}


def classify_dungeon(name: str) -> str:
    """Classifica dungeon por pattern matching no nome."""
    for dtype, patterns in DUNGEON_TYPE_PATTERNS.items():
        if patterns is None:
            continue
        for pattern in patterns:
            if pattern.lower() in name.lower():
                return dtype
    return "surface_poi"


def build_grace_lookup(grace_flags: dict[str, str]) -> dict[str, int]:
    """Constroi lookup de nome normalizado de grace -> flag_id."""
    lookup: dict[str, int] = {}
    for flag_id_str, name in grace_flags.items():
        norm = normalize_name(name)
        lookup[norm] = int(flag_id_str)
    return lookup


def find_grace_flag(dungeon_name: str, grace_lookup: dict[str, int]) -> int | None:
    """Busca grace_flag associada a uma dungeon."""
    norm = normalize_name(dungeon_name)
    if norm in grace_lookup:
        return grace_lookup[norm]

    for grace_norm, flag_id in grace_lookup.items():
        if norm in grace_norm or grace_norm in norm:
            return flag_id

    return None


def main() -> None:
    logger.info("Iniciando auditoria de dungeons")

    dungeons: list[dict] = load_json("dungeons.json")
    grace_flags: dict[str, str] = load_json("grace_flags.json")
    boss_flags: dict = load_json("boss_flags.json")

    backup_file(REFERENCES_DIR / "dungeons.json")

    grace_lookup = build_grace_lookup(grace_flags)

    type_counts: dict[str, int] = {}
    grace_linked = 0

    for dungeon in dungeons:
        dtype = classify_dungeon(dungeon["name"])
        dungeon["dungeon_type"] = dtype
        type_counts[dtype] = type_counts.get(dtype, 0) + 1

        gf = find_grace_flag(dungeon["name"], grace_lookup)
        if gf is not None:
            dungeon["grace_flag"] = gf
            grace_linked += 1

    dungeon_lookup: dict[str, int] = {}
    for i, d in enumerate(dungeons):
        norm = re.sub(r"[^a-z0-9]", "", d["name"].lower())
        dungeon_lookup[norm] = i

    manual_boss_to_dungeon: dict[int, str] = {
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

    pending: dict[str, list[int]] = {}
    for flag_id_str, entry in boss_flags.items():
        if entry.get("type") != "dungeon":
            continue
        flag_id = int(flag_id_str)
        boss_name = entry["name"]

        dungeon_name: str | None = None
        if flag_id in manual_boss_to_dungeon:
            dungeon_name = manual_boss_to_dungeon[flag_id]
        else:
            m = re.search(r"\(([^)]+)\)", boss_name)
            if m:
                candidate = m.group(1)
                norm = re.sub(r"[^a-z0-9]", "", candidate.lower())
                if norm in dungeon_lookup:
                    dungeon_name = dungeons[dungeon_lookup[norm]]["name"]

        if dungeon_name:
            if dungeon_name not in pending:
                pending[dungeon_name] = []
            pending[dungeon_name].append(flag_id)

    boss_linked = 0
    for dungeon in dungeons:
        name = dungeon["name"]
        flags = pending.get(name, [])
        if flags:
            dungeon["boss_flags"] = sorted(flags)
            boss_linked += 1
        elif "boss_flags" in dungeon:
            del dungeon["boss_flags"]

    save_json(REFERENCES_DIR / "dungeons.json", dungeons)

    print(f"\nResultado da auditoria de dungeons:")
    print(f"  Total: {len(dungeons)} dungeons classificados")
    print(f"\n  Distribuicao por tipo:")
    for dtype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"    {dtype}: {count}")

    print(f"\n  Grace flags linkados: {grace_linked}")
    print(f"  Boss flags linkados: {boss_linked} dungeons")

    logger.info(
        "Auditoria concluida: %d dungeons, %d tipos, %d grace links, %d boss links",
        len(dungeons), len(type_counts), grace_linked, boss_linked,
    )


if __name__ == "__main__":
    main()


# "A medida de um homem e o que ele faz com o poder." -- Platao
