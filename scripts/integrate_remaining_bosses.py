"""Integra boss flags restantes a partir do repositorio er-save-manager.

Fonte: Hapfel1/er-save-manager src/er_save_manager/data/boss_data.py
Resolve os 13 bosses non-Golem que ainda nao tem flag.
Furnace Golems (8) sao confirmados como nao-rastreaveis.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fetch_utils import (
    REFERENCES_DIR,
    backup_file,
    fetch_raw_github,
    load_json,
    normalize_name,
    save_json,
)
from log import get_logger

logger = get_logger("integrate_remaining_bosses")

FURNACE_GOLEM_PREFIX = "furnace golem"

MANUAL_BOSS_FLAGS: dict[str, int] = {
    "night's cavalry (altus plateau)": 1039520850,
    "deathbird (leyndell capital outskirts)": 1040520800,
    "black knife assassin (altus plateau)": 1040520850,
    "black knife assassin (liurnia of the lakes east)": 1036450850,
    "wormface": 1041530800,
    "crucible knight siluria": 12020390,
    "devonia, crucible knight": 12020850,
    "elder dragon greyoll": 1050400800,
    "base serpent messmer": 9146,
    "dryleaf dane (boss)": 2050470850,
}

KNOWN_UNTRACKABLE = {
    "alabaster lord",
    "ghost troll",
    "giant golem",
}


def parse_boss_data(content: str) -> dict[str, list[dict]]:
    """Parse boss_data.py do er-save-manager.

    Retorna dict de nome normalizado -> lista de entradas.
    Formatos esperados:
      "Boss Name": flag_id
      "Boss Name": (flag_id, "Location")
    """
    results: dict[str, list[dict]] = {}

    pattern_tuple = r'"([^"]+)":\s*\((\d+),\s*"([^"]+)"\)'
    for match in re.finditer(pattern_tuple, content):
        name = match.group(1).strip()
        flag_id = int(match.group(2))
        location = match.group(3).strip()
        norm = normalize_name(name)
        if norm not in results:
            results[norm] = []
        results[norm].append({"name": name, "flag_id": flag_id, "location": location})

    pattern_simple = r'"([^"]+)":\s*(\d+)\s*[,}]'
    for match in re.finditer(pattern_simple, content):
        name = match.group(1).strip()
        flag_id = int(match.group(2))
        norm = normalize_name(name)
        if norm not in results:
            results[norm] = []
        if not any(e["flag_id"] == flag_id for e in results[norm]):
            results[norm].append({"name": name, "flag_id": flag_id, "location": ""})

    return results


def main() -> None:
    logger.info("Iniciando integracao de boss flags restantes")

    boss_flags: dict = load_json("boss_flags.json")
    bosses: list[dict] = load_json("bosses.json")

    backup_file(REFERENCES_DIR / "boss_flags.json")
    backup_file(REFERENCES_DIR / "bosses.json")

    external_bosses: dict[str, list[dict]] = {}
    try:
        content = fetch_raw_github(
            "Hapfel1", "er-save-manager", "main",
            "src/er_save_manager/data/boss_data.py",
        )
        external_bosses = parse_boss_data(content)
        logger.info("er-save-manager: %d boss names unicos", len(external_bosses))
    except Exception as exc:
        logger.warning("Falha ao buscar er-save-manager boss_data.py: %s", exc)
        print(f"AVISO: Fonte externa indisponivel: {exc}")

    null_bosses = [b for b in bosses if b.get("flag") is None]
    logger.info("Bosses sem flag: %d", len(null_bosses))

    resolved = 0
    skipped_golem = 0
    skipped_untrackable = 0
    unresolved: list[str] = []

    for boss in bosses:
        if boss.get("flag") is not None:
            continue

        name_lower = boss["name"].lower().strip()
        norm = normalize_name(boss["name"])

        if name_lower.startswith(FURNACE_GOLEM_PREFIX):
            skipped_golem += 1
            logger.info("  Furnace Golem (nao-rastreavel): %s", boss["name"])
            continue

        if norm in KNOWN_UNTRACKABLE:
            skipped_untrackable += 1
            logger.info("  Nao-rastreavel (inimigo generico): %s", boss["name"])
            continue

        flag_id = None

        if name_lower in MANUAL_BOSS_FLAGS:
            flag_id = MANUAL_BOSS_FLAGS[name_lower]
            logger.info("  Manual: %s -> %d", boss["name"], flag_id)
        elif external_bosses:
            entries = external_bosses.get(norm, [])
            if entries:
                flag_id = entries[0]["flag_id"]
                logger.info("  External: %s -> %d", boss["name"], flag_id)
            else:
                for ext_norm, ext_entries in external_bosses.items():
                    if norm in ext_norm or ext_norm in norm:
                        flag_id = ext_entries[0]["flag_id"]
                        logger.info(
                            "  Fuzzy: %s ~= %s -> %d",
                            boss["name"], ext_entries[0]["name"], flag_id,
                        )
                        break

        if flag_id is not None:
            boss["flag"] = flag_id
            resolved += 1

            key = str(flag_id)
            if key not in boss_flags:
                region = boss.get("region", "unknown")
                boss_flags[key] = {
                    "name": boss["name"],
                    "region": region,
                    "is_main": boss.get("is_main", False),
                    "type": boss.get("type", "field"),
                }
        else:
            unresolved.append(boss["name"])

    sorted_bf = dict(sorted(boss_flags.items(), key=lambda x: int(x[0])))
    save_json(REFERENCES_DIR / "boss_flags.json", sorted_bf)
    save_json(REFERENCES_DIR / "bosses.json", bosses)

    still_null = [b["name"] for b in bosses if b.get("flag") is None]

    print(f"\nResultado da integracao de boss flags restantes:")
    print(f"  Resolvidos: {resolved}")
    print(f"  Furnace Golems (nao-rastreaveis): {skipped_golem}")
    print(f"  Inimigos genericos: {skipped_untrackable}")
    print(f"  Sem resolucao: {len(unresolved)}")
    print(f"  boss_flags.json total: {len(sorted_bf)}")
    print(f"  Bosses sem flag restantes: {len(still_null)}")

    if unresolved:
        print(f"\n  Bosses nao resolvidos:")
        for name in sorted(unresolved):
            print(f"    - {name}")

    if still_null:
        print(f"\n  Todos os bosses sem flag:")
        for name in sorted(still_null):
            print(f"    - {name}")

    logger.info(
        "Integracao concluida: %d resolvidos, %d golems, %d genericos, %d sem resolucao",
        resolved, skipped_golem, skipped_untrackable, len(unresolved),
    )


if __name__ == "__main__":
    main()


# "Conhece-te a ti mesmo." -- Inscricao no Templo de Delfos
