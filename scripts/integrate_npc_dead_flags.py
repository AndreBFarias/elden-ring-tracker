"""Integra NPC dead flags a partir do repositorio er-save-manager.

Fonte: Hapfel1/er-save-manager src/er_save_manager/data/npc_data.py
Regra: dead_flag = base_flag_id + 3
Verificacao BST antes de adicionar.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fetch_utils import (
    REFERENCES_DIR,
    backup_file,
    fetch_raw_github,
    load_bst_blocks,
    load_json,
    normalize_name,
    save_json,
)
from log import get_logger

logger = get_logger("integrate_npc_dead_flags")

DEAD_FLAG_OFFSET = 3


def parse_npc_data(content: str) -> list[dict]:
    """Parse npc_data.py do er-save-manager.

    Formato esperado: "NPC Name": (base_flag_id, "Location")
    """
    pattern = r'"([^"]+)":\s*\((\d+),\s*"([^"]+)"\)'
    results: list[dict] = []
    for match in re.finditer(pattern, content):
        name = match.group(1).strip()
        base_flag = int(match.group(2))
        location = match.group(3).strip()
        results.append({
            "name": name,
            "base_flag": base_flag,
            "dead_flag": base_flag + DEAD_FLAG_OFFSET,
            "location": location,
        })
    return results


def verify_bst_coverage(flag_id: int, bst_blocks: set[int]) -> bool:
    """Verifica se o bloco BST para um flag_id existe."""
    block = flag_id // 1000
    return block in bst_blocks


def main() -> None:
    logger.info("Iniciando integracao de NPC dead flags")

    current_flags: dict[str, str] = load_json("npc_dead_flags.json")
    npcs: list[dict] = load_json("npcs.json")
    bst_blocks = load_bst_blocks()

    backup_file(REFERENCES_DIR / "npc_dead_flags.json")

    try:
        content = fetch_raw_github(
            "Hapfel1", "er-save-manager", "main",
            "src/er_save_manager/data/npc_data.py",
        )
    except Exception as exc:
        logger.error("Falha ao buscar er-save-manager npc_data.py: %s", exc)
        print(f"ERRO: Falha ao buscar fonte externa: {exc}")
        sys.exit(1)

    parsed = parse_npc_data(content)
    logger.info("er-save-manager: %d NPCs parseados", len(parsed))

    npc_names_norm: dict[str, str] = {}
    for npc in npcs:
        if npc.get("category") == "npc":
            npc_names_norm[normalize_name(npc["name"])] = npc["name"]

    added = 0
    skipped_bst = 0
    skipped_exists = 0
    by_range: dict[str, int] = {}

    for entry in parsed:
        dead_flag = entry["dead_flag"]
        key = str(dead_flag)

        if key in current_flags:
            skipped_exists += 1
            continue

        if not verify_bst_coverage(dead_flag, bst_blocks):
            skipped_bst += 1
            logger.info(
                "  BST ausente: %s (dead_flag=%d, bloco=%d)",
                entry["name"], dead_flag, dead_flag // 1000,
            )
            continue

        current_flags[key] = entry["name"]
        added += 1

        range_key = f"{dead_flag // 1000}xxx"
        by_range[range_key] = by_range.get(range_key, 0) + 1

        npc_norm = normalize_name(entry["name"])
        match_status = "match" if npc_norm in npc_names_norm else "sem match"
        logger.info(
            "  Adicionado: %s -> dead_flag %d (%s em npcs.json)",
            entry["name"], dead_flag, match_status,
        )

    sorted_flags = dict(sorted(current_flags.items(), key=lambda x: int(x[0])))
    save_json(REFERENCES_DIR / "npc_dead_flags.json", sorted_flags)

    print(f"\nResultado da integracao de NPC dead flags:")
    print(f"  Fonte: er-save-manager ({len(parsed)} NPCs parseados)")
    print(f"  Adicionados: {added}")
    print(f"  Ja existiam: {skipped_exists}")
    print(f"  Sem cobertura BST: {skipped_bst}")
    print(f"  Total npc_dead_flags.json: {len(sorted_flags)}")

    if by_range:
        print(f"\n  Distribuicao por range de flags:")
        for r, count in sorted(by_range.items()):
            print(f"    {r}: {count}")

    trackable = [n for n in npcs if n.get("category") == "npc"]
    coverage = len(sorted_flags) / max(len(trackable), 1) * 100
    print(f"\n  Cobertura: {len(sorted_flags)}/{len(trackable)} NPCs rastreaveis ({coverage:.1f}%)")

    logger.info(
        "Integracao concluida: +%d flags (total: %d, cobertura: %.1f%%)",
        added, len(sorted_flags), coverage,
    )


if __name__ == "__main__":
    main()


# "Nao ha fatos, apenas interpretacoes." -- Friedrich Nietzsche
