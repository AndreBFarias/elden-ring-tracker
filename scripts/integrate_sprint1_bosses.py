"""Integra boss flags documentados no sprint1.md em boss_flags.json e bosses.json.

Parseia as tabelas markdown do sprint1.md, extrai todos os 204 boss flag IDs
documentados, compara com os dados atuais e gera versoes atualizadas.
"""

import json
import re
from pathlib import Path

from log import get_logger

logger = get_logger("integrate_sprint1")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCES_DIR = PROJECT_ROOT / "data" / "references"
SPRINT1_PATH = PROJECT_ROOT / "sprint1.md"


def parse_sprint1_tables(content: str) -> list[dict]:
    """Extrai entradas de boss flags das tabelas markdown do sprint1.md."""
    entries: list[dict] = []
    lines = content.splitlines()
    in_table = False
    headers: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            in_table = False
            headers = []
            continue

        cells = [c.strip() for c in stripped.split("|")[1:-1]]

        if not in_table:
            normalized = [c.lower().replace(" ", "_") for c in cells]
            if "flag_id" in normalized and "boss_name" in normalized:
                headers = normalized
                in_table = True
            continue

        if all(set(c) <= {"-", " ", ":"} for c in cells):
            continue

        if len(cells) < len(headers):
            continue

        row = dict(zip(headers, cells))
        flag_str = row.get("flag_id", "").strip().strip("*")
        if not flag_str or not flag_str.isdigit():
            continue

        flag_id = int(flag_str)
        boss_name = row.get("boss_name", "").strip()
        if not boss_name:
            continue

        location = row.get("location", "").strip()
        region = row.get("region", "").strip()
        game = row.get("game", "").strip().lower()

        global_flag_str = row.get("global_flag", "").strip().strip("*")
        global_flag = int(global_flag_str) if global_flag_str.isdigit() else None

        entries.append({
            "flag_id": flag_id,
            "name": boss_name,
            "location": location,
            "region": region,
            "game": game,
            "global_flag": global_flag,
        })

    return entries


def parse_global_flags_table(content: str) -> dict[int, int]:
    """Extrai o mapeamento global_flag -> map_flag da tabela de global flags."""
    mapping: dict[int, int] = {}
    lines = content.splitlines()
    in_global_table = False
    headers: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            in_global_table = False
            headers = []
            continue

        cells = [c.strip() for c in stripped.split("|")[1:-1]]

        if not in_global_table:
            normalized = [c.lower().replace(" ", "_") for c in cells]
            if "global_flag" in normalized and "map_flag" in normalized:
                headers = normalized
                in_global_table = True
            continue

        if all(set(c) <= {"-", " ", ":"} for c in cells):
            continue

        if len(cells) < len(headers):
            continue

        row = dict(zip(headers, cells))
        gf_str = row.get("global_flag", "").strip()
        mf_str = row.get("map_flag", "").strip()

        if gf_str.isdigit() and mf_str.isdigit():
            mapping[int(gf_str)] = int(mf_str)

    return mapping


def region_from_sprint1(region_str: str) -> str:
    """Normaliza nomes de regiao do sprint1 para o formato do tracker."""
    mapping = {
        "stormhill": "stormhill",
        "limgrave": "limgrave",
        "weeping peninsula": "weeping_peninsula",
        "liurnia": "liurnia",
        "altus plateau": "altus",
        "mt. gelmir": "altus",
        "caelid": "caelid",
        "dragonbarrow": "dragonbarrow",
        "mountaintops": "mountaintops",
        "snowfield": "mountaintops",
        "haligtree": "haligtree",
        "leyndell": "leyndell",
        "capital outskirts": "capital_outskirts",
        "farum azula": "farum_azula",
        "ainsel river": "underground",
        "lake of rot": "underground",
        "nokron": "underground",
        "siofra river": "underground",
        "deeproot depths": "underground",
        "mohgwyn palace": "underground",
        "underground": "underground",
        "volcano manor": "volcano_manor",
        "raya lucaria": "raya_lucaria",
        "gravesite plain": "dlc",
        "shadow keep": "dlc",
        "cerulean coast": "dlc",
        "scadu altus": "dlc",
        "scaduview": "dlc",
        "ancient ruins of rauh": "dlc",
        "abyssal woods": "dlc",
        "enir-ilim": "dlc",
        "jagged peak": "dlc",
        "hinterland": "dlc",
    }
    return mapping.get(region_str.lower(), region_str.lower().replace(" ", "_"))


def boss_type_from_flag(flag_id: int, game: str) -> str:
    """Determina o tipo de boss baseado no padrao do flag ID."""
    if game == "dlc":
        if flag_id < 100000:
            return "dlc"
        return "field" if flag_id >= 2000000000 else "dungeon"

    if flag_id >= 1000000000:
        return "field"
    if flag_id >= 30000000:
        return "dungeon"
    return "legacy"


def integrate_boss_flags(
    sprint1_entries: list[dict],
    global_to_map: dict[int, int],
    current_boss_flags: dict[int, dict],
) -> dict[int, dict]:
    """Integra entradas do sprint1 no boss_flags.json."""
    updated = dict(current_boss_flags)
    added = 0

    for entry in sprint1_entries:
        flag_id = entry["flag_id"]
        if flag_id in updated:
            continue

        region = region_from_sprint1(entry["region"])
        is_main = entry.get("global_flag") is not None
        boss_type = boss_type_from_flag(flag_id, entry.get("game", "base"))
        if entry.get("game") == "dlc" and flag_id < 100000:
            boss_type = "dlc"

        updated[flag_id] = {
            "name": entry["name"],
            "region": region,
            "is_main": is_main,
            "type": boss_type,
        }
        added += 1

    logger.info("boss_flags.json: %d entradas adicionadas (total: %d)", added, len(updated))
    return updated


def normalize_boss_name(name: str) -> str:
    """Normaliza nome de boss para comparacao fuzzy."""
    name = name.lower().strip()
    name = re.sub(r"\s*\(.*?\)\s*", " ", name)
    name = re.sub(r"\s*-\s*.*$", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    name = name.replace(",", "").replace("'", "").replace("'", "")
    return name


def build_name_to_flag_map(
    sprint1_entries: list[dict],
    global_to_map: dict[int, int],
) -> dict[str, int]:
    """Constroi mapa de nome normalizado -> flag_id preferido."""
    name_map: dict[str, int] = {}
    for entry in sprint1_entries:
        norm = normalize_boss_name(entry["name"])
        flag = entry["flag_id"]
        if norm not in name_map or flag > 10000:
            name_map[norm] = flag

    return name_map


def update_bosses_json(
    bosses: list[dict],
    sprint1_entries: list[dict],
    global_to_map: dict[int, int],
    boss_flags_db: dict[int, dict],
) -> tuple[list[dict], int]:
    """Atualiza bosses.json preenchendo flag:null com dados do sprint1."""
    name_to_flag = build_name_to_flag_map(sprint1_entries, global_to_map)

    manual_overrides = {
        "morgott, the omen king": 9104,
        "beast clergyman / maliketh, the black blade": 9116,
        "godfrey, first elden lord": 9105,
        "sir gideon ofnir, the all-knowing": 9106,
        "radagon of the golden order": 9123,
        "godskin apostle & godskin noble": 9114,
        "godskin noble(volcano manor)": 9121,
        "godskin noble (divine tower of liurnia)": 34120800,
        "godskin apostle": 9173,
        "promised consort radahn - enir-ilim": 9143,
        "radahn, consort of miquella - enir-ilim": 9143,
        "divine beast dancing lion - belurat tower settlement": 9140,
        "putrescent knight - stone coffin fissure": 9148,
        "crucible knight / misbegotten warrior": 1051360800,
        "crucible knight": 12020390,
        "margit, the fell omen (leyndell)": 11000800,
        "tree sentinel (limgrave)": 1042360800,
        "tree sentinel (leyndell, royal capital)": 1045520800,
        "bell bearing hunter": 1042380850,
        "tibia mariner (limgrave)": 1045390800,
        "tibia mariner (liurnia of the lakes)": 1039440800,
        "tibia mariner (wyndham ruins)": 1038520800,
        "night's cavalry (weeping peninsula)": 1044320850,
        "night's cavalry (liurnia)": 1036480800,
        "night's cavalry (liurnia of the lakes north)": 1039430800,
        "night's cavalry (altus plateau)": 1048510800,
        "night's cavalry (caelid)": 1049370800,
        "night's cavalry (dragonbarrow east)": 1052410850,
        "night's cavalry (forbidden lands)": 1048510800,
        "night's cavalry - 2x (consecrated snowfield)": 1248550800,
        "death rite bird (raya lucaria academy east)": 1036450800,
        "death rite bird (caelid swamp)": 1049370850,
        "death rite bird (west mountaintops of the giants)": 1050570800,
        "death rite bird (central mountaintops of the giants)": 1048570800,
        "deathbird (stormhill)": 1042380800,
        "deathbird (weeping peninsula)": 1044320800,
        "deathbird (liurnia of the lakes south)": 1037420800,
        "deathbird (leyndell capital outskirts)": 1040520800,
        "black knife assassin (altus plateau)": 1040520800,
        "black knife assassin (liurnia of the lakes east)": 1036450800,
        "onyx lord": 1036500800,
        "perfumer tricia": 30120800,
        "grave warden duelist (auriza side tomb)": 30130800,
        "demi-human queen gilika": 1038510800,
        "demi-human queen": 1038510800,
        "erdtree avatar (leyndell)": 1041530800,
        "wormface": 1041530800,
        "crucible knight siluria": 12020390,
        "devonia, crucible knight": 12020390,
        "magma wyrm (volcano manor)": 9126,
        "count ymir, mother of fingers": 2051450800,
        "bayle the dread": 2054390800,
        "black blade kindred": 1049520800,
        "black blade kindred b": 1051430800,
        "bell bearing hunter (isolated merchant dragonbarrow)": 1048410800,
        "valiant gargoyle (twinblade)": 12020800,
        "magma wyrm - dragon's pit": 43010800,
        "hippopotamus": 9144,
        "lesser ulcerated tree spirit": 9128,
        "misbegotten crusader - stone coffin fissure": 31120800,
        "miranda the blighted bloom / omenkiller": 31180800,
        "kood, captain of the fire knights": 2050470800,
        "ulcerated tree spirit - belurat tower settlement": 20000800,
    }

    flag_from_bf = {}
    for fid, info in boss_flags_db.items():
        norm = normalize_boss_name(info["name"])
        flag_from_bf[norm] = fid

    updated_count = 0
    updated = []
    for boss in bosses:
        if boss.get("flag") is not None:
            updated.append(boss)
            continue

        name_lower = boss["name"].lower().strip()
        norm = normalize_boss_name(boss["name"])

        resolved_flag = None

        if name_lower in manual_overrides:
            resolved_flag = manual_overrides[name_lower]
        elif norm in name_to_flag:
            resolved_flag = name_to_flag[norm]
        elif norm in flag_from_bf:
            resolved_flag = flag_from_bf[norm]

        if resolved_flag is not None:
            boss = dict(boss)
            boss["flag"] = resolved_flag
            updated_count += 1
            logger.info("  %s -> flag %d", boss["name"], resolved_flag)

        updated.append(boss)

    logger.info("bosses.json: %d flags preenchidos", updated_count)
    return updated, updated_count


def main() -> None:
    content = SPRINT1_PATH.read_text(encoding="utf-8")

    sprint1_entries = parse_sprint1_tables(content)
    logger.info("Sprint1: %d entradas extraidas das tabelas", len(sprint1_entries))

    global_to_map = parse_global_flags_table(content)
    logger.info("Sprint1: %d mapeamentos global->map", len(global_to_map))

    with open(REFERENCES_DIR / "boss_flags.json", encoding="utf-8") as f:
        current_boss_flags = {int(k): v for k, v in json.load(f).items()}
    logger.info("boss_flags.json atual: %d entradas", len(current_boss_flags))

    updated_boss_flags = integrate_boss_flags(
        sprint1_entries, global_to_map, current_boss_flags,
    )

    sorted_flags = dict(sorted(updated_boss_flags.items()))
    bf_path = REFERENCES_DIR / "boss_flags.json"
    with open(bf_path, "w", encoding="utf-8") as f:
        json.dump(
            {str(k): v for k, v in sorted_flags.items()},
            f, indent=2, ensure_ascii=False,
        )
        f.write("\n")
    logger.info("boss_flags.json salvo: %d entradas", len(sorted_flags))

    with open(REFERENCES_DIR / "bosses.json", encoding="utf-8") as f:
        bosses = json.load(f)
    logger.info("bosses.json atual: %d entradas", len(bosses))

    updated_bosses, fill_count = update_bosses_json(
        bosses, sprint1_entries, global_to_map, updated_boss_flags,
    )

    with open(REFERENCES_DIR / "bosses.json", "w", encoding="utf-8") as f:
        json.dump(updated_bosses, f, indent=2, ensure_ascii=False)
        f.write("\n")
    logger.info("bosses.json salvo: %d entradas (%d flags preenchidos)", len(updated_bosses), fill_count)

    still_null = [b["name"] for b in updated_bosses if b.get("flag") is None]
    if still_null:
        logger.warning("Bosses ainda sem flag (%d):", len(still_null))
        for name in sorted(still_null):
            logger.warning("  - %s", name)


if __name__ == "__main__":
    main()


# "A perfeicao nao e alcancavel, mas se a perseguirmos, podemos alcancar a excelencia." -- Vince Lombardi
