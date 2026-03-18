"""Integra grace flags DLC a partir de repositorios externos do GitHub.

Fontes:
  1. groobybugs/ER-Save-Editor: src/db/graces.rs (Rust enum, ~89 DLC graces)
  2. Hapfel1/er-save-manager: src/er_save_manager/data/event_flags_db.py (Python dict)

Merge com prioridade para er-save-manager (nomes mais completos).
Cross-reference com graces.json por nome normalizado em 3 niveis.
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

logger = get_logger("integrate_dlc_graces")

DLC_GRACE_RANGES = [
    (72000, 72999),
    (74000, 75999),
    (76800, 77999),
]

GRACE_SUFFIXES_TO_STRIP = [
    " site of grace",
    " | unlocked",
    " (unlocked)",
]

AREA_PREFIXES_TO_STRIP = [
    r"^\[.*?\]\s*",
    r"^gravesite plain\s*[-:]\s*",
    r"^scadu altus\s*[-:]\s*",
    r"^shadow keep\s*[-:]\s*",
    r"^cerulean coast\s*[-:]\s*",
    r"^abyssal woods\s*[-:]\s*",
    r"^ancient ruins of rauh\s*[-:]\s*",
    r"^jagged peak\s*[-:]\s*",
    r"^enir-ilim\s*[-:]\s*",
    r"^hinterland\s*[-:]\s*",
]

NAME_OVERRIDES: dict[str, str] = {
    "cerulean  coast cross": "cerulean coast cross",
    "greatbrdige, north": "greatbridge, north",
    "scadu atlus, west": "scadu altus, west",
    "divine gatefront staircase": "divine gatefront staircase",
    "moorth highway, south site of grace": "moorth highway, south",
    "moorth ruins site of grace": "moorth ruins",
    "bonny gaol site of grace": "bonny gaol",
    "bonny village site of grace": "bonny village",
    "darklight catacombs site of grace": "darklight catacombs",
    "fort of reprimand site of grace": "fort of reprimand",
    "scaduview cross site of grace": "scaduview cross",
}

MANUAL_GRACE_MAP: dict[str, int] = {
    "divine gatefront staircase": 72016,
    "enir-ilim: outer wall": 72012,
}


def _in_dlc_range(flag_id: int) -> bool:
    return any(lo <= flag_id <= hi for lo, hi in DLC_GRACE_RANGES)


def _clean_grace_name(name: str) -> str:
    """Remove sufixos e prefixos de area para normalizacao."""
    cleaned = name.strip()
    for suffix in GRACE_SUFFIXES_TO_STRIP:
        if cleaned.lower().endswith(suffix):
            cleaned = cleaned[: -len(suffix)].strip()
    for prefix_pattern in AREA_PREFIXES_TO_STRIP:
        cleaned = re.sub(prefix_pattern, "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned


def parse_groobybugs_graces(content: str) -> dict[int, str]:
    """Parse Rust enum de groobybugs/ER-Save-Editor."""
    pattern = r'Grace::\w+,\s*\(MapName::\w+,\s*(\d+),\s*"([^"]+)"\)'
    results: dict[int, str] = {}
    for match in re.finditer(pattern, content):
        flag_id = int(match.group(1))
        name = match.group(2).strip()
        if _in_dlc_range(flag_id):
            results[flag_id] = name
    return results


def parse_ersavemanager_flags(content: str) -> dict[int, str]:
    """Parse Python dict de Hapfel1/er-save-manager event_flags_db.py."""
    pattern = r'(\d+):\s*\{[^}]*"name":\s*"([^"]+)"'
    results: dict[int, str] = {}
    for match in re.finditer(pattern, content):
        flag_id = int(match.group(1))
        name = match.group(2).strip()
        if _in_dlc_range(flag_id) and ("grace" in name.lower() or "unlocked" in name.lower() or flag_id >= 76800):
            cleaned = _clean_grace_name(name)
            results[flag_id] = cleaned
    return results


def merge_sources(
    grooby: dict[int, str],
    ersm: dict[int, str],
) -> dict[int, str]:
    """Merge de ambas as fontes com prioridade para er-save-manager."""
    merged = dict(grooby)
    for flag_id, name in ersm.items():
        merged[flag_id] = name
    return merged


def build_match_index(graces: list[dict]) -> dict[str, int]:
    """Constroi indice de graces DLC sem flag para matching."""
    index: dict[str, int] = {}
    for i, g in enumerate(graces):
        if g.get("region") == "dlc" and g.get("flag") is None:
            index[g["name"].lower().strip()] = i
    return index


def match_grace(
    source_name: str,
    graces: list[dict],
    exact_index: dict[str, int],
    norm_index: dict[str, int],
) -> int | None:
    """Tenta match em 3 niveis. Retorna indice em graces ou None."""
    cleaned = _clean_grace_name(source_name)

    lower = cleaned.lower().strip()
    if lower in exact_index:
        return exact_index[lower]

    override = NAME_OVERRIDES.get(lower)
    if override:
        lower_o = override.lower().strip()
        if lower_o in exact_index:
            return exact_index[lower_o]

    norm = normalize_name(cleaned)
    if norm in norm_index:
        return norm_index[norm]

    return None


def main() -> None:
    logger.info("Iniciando integracao de grace flags DLC")

    grace_flags: dict[str, str] = load_json("grace_flags.json")
    graces: list[dict] = load_json("graces.json")

    backup_file(REFERENCES_DIR / "grace_flags.json")
    backup_file(REFERENCES_DIR / "graces.json")

    grooby_graces: dict[int, str] = {}
    try:
        content = fetch_raw_github(
            "groobybugs", "ER-Save-Editor", "main", "src/db/graces.rs",
        )
        grooby_graces = parse_groobybugs_graces(content)
        logger.info("groobybugs: %d graces DLC extraidos", len(grooby_graces))
    except Exception as exc:
        logger.warning("Falha ao buscar groobybugs: %s", exc)
        print(f"AVISO: Falha ao buscar groobybugs/ER-Save-Editor: {exc}")

    ersm_graces: dict[int, str] = {}
    try:
        content = fetch_raw_github(
            "Hapfel1", "er-save-manager", "main",
            "src/er_save_manager/data/event_flags_db.py",
        )
        ersm_graces = parse_ersavemanager_flags(content)
        logger.info("er-save-manager: %d graces DLC extraidos", len(ersm_graces))
    except Exception as exc:
        logger.warning("Falha ao buscar er-save-manager: %s", exc)
        print(f"AVISO: Falha ao buscar Hapfel1/er-save-manager: {exc}")

    if not grooby_graces and not ersm_graces:
        logger.error("Nenhuma fonte externa disponivel")
        print("ERRO: Nenhuma fonte externa disponivel. Abortando.")
        sys.exit(1)

    merged = merge_sources(grooby_graces, ersm_graces)
    logger.info("Merge: %d grace flags DLC unicos", len(merged))

    added_to_gf = 0
    for flag_id, name in sorted(merged.items()):
        key = str(flag_id)
        if key not in grace_flags:
            grace_flags[key] = name
            added_to_gf += 1

    logger.info("grace_flags.json: %d novas entradas adicionadas", added_to_gf)

    exact_index = build_match_index(graces)
    norm_index: dict[str, int] = {}
    for i, g in enumerate(graces):
        if g.get("region") == "dlc" and g.get("flag") is None:
            norm_key = normalize_name(g["name"])
            if norm_key not in norm_index:
                norm_index[norm_key] = i

    also_check_overrides: dict[str, int] = {}
    for original, corrected in NAME_OVERRIDES.items():
        for i, g in enumerate(graces):
            if g.get("region") == "dlc" and g.get("flag") is None:
                if g["name"].lower().strip() == original:
                    also_check_overrides[corrected.lower().strip()] = i
                    break

    for corrected_lower, idx in also_check_overrides.items():
        if corrected_lower not in exact_index:
            exact_index[corrected_lower] = idx
        norm_key = normalize_name(corrected_lower)
        if norm_key not in norm_index:
            norm_index[norm_key] = idx

    matched = 0
    unmatched: list[tuple[int, str]] = []

    for flag_id, source_name in sorted(merged.items()):
        idx = match_grace(source_name, graces, exact_index, norm_index)
        if idx is not None:
            grace = graces[idx]
            if grace.get("flag") is None:
                grace["flag"] = flag_id
                matched += 1
                logger.info("  Match: %s -> flag %d", grace["name"], flag_id)
                name_lower = grace["name"].lower().strip()
                if name_lower in exact_index:
                    del exact_index[name_lower]
                norm_key = normalize_name(grace["name"])
                if norm_key in norm_index:
                    del norm_index[norm_key]
        else:
            unmatched.append((flag_id, source_name))

    for grace_name_lower, manual_flag in MANUAL_GRACE_MAP.items():
        for g in graces:
            if g.get("region") == "dlc" and g.get("flag") is None:
                if g["name"].lower().strip() == grace_name_lower:
                    g["flag"] = manual_flag
                    matched += 1
                    logger.info("  Manual: %s -> flag %d", g["name"], manual_flag)
                    break

    sorted_gf = dict(sorted(grace_flags.items(), key=lambda x: int(x[0])))
    save_json(REFERENCES_DIR / "grace_flags.json", sorted_gf)
    save_json(REFERENCES_DIR / "graces.json", graces)

    still_null = [g["name"] for g in graces if g.get("region") == "dlc" and g.get("flag") is None]

    print(f"\nResultado da integracao de graces DLC:")
    print(f"  Fontes: groobybugs={len(grooby_graces)}, er-save-manager={len(ersm_graces)}")
    print(f"  Merge total: {len(merged)} flags unicos")
    print(f"  grace_flags.json: +{added_to_gf} entradas (total: {len(sorted_gf)})")
    print(f"  graces.json: {matched} DLC graces preenchidos")
    print(f"  Ainda sem flag: {len(still_null)} graces DLC")

    if unmatched:
        print(f"\n  Flags sem match em graces.json ({len(unmatched)}):")
        for fid, name in unmatched[:20]:
            print(f"    - {fid}: {name}")
        if len(unmatched) > 20:
            print(f"    ... e mais {len(unmatched) - 20}")

    if still_null:
        print(f"\n  Graces DLC ainda sem flag ({len(still_null)}):")
        for name in sorted(still_null):
            print(f"    - {name}")

    logger.info(
        "Integracao concluida: %d matched, %d sem match, %d DLC ainda sem flag",
        matched, len(unmatched), len(still_null),
    )


if __name__ == "__main__":
    main()


# "O mapa nao e o territorio." -- Alfred Korzybski
