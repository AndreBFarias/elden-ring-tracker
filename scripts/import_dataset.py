import json
import logging
import sys
import urllib.request
from logging.handlers import RotatingFileHandler
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from map_config import REFERENCES_DIR

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("elden_tracker.import_dataset")
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

_console = logging.StreamHandler()
_console.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
logger.addHandler(_console)

DATASET_URL = (
    "https://raw.githubusercontent.com/learning/elden_map_data/main/data.json"
)

CATEGORY_MAP = {
    "site_of_grace": ("graces.json", "grace"),
    "bosses": ("bosses.json", "boss"),
    "locations": ("dungeons.json", "dungeon"),
    "weapons": ("items.json", "weapon"),
    "armor": ("items.json", "armor"),
    "shields": ("items.json", "shield"),
    "talismans": ("items.json", "talisman"),
    "ashes_of_war": ("items.json", "ash_of_war"),
    "spells": ("items.json", "spell"),
    "consumables": ("items.json", "consumable"),
    "materials": ("items.json", "material"),
    "upgrade_materials": ("items.json", "upgrade_material"),
    "flask_upgrades": ("items.json", "flask_upgrade"),
    "key": ("items.json", "key_item"),
    "npc": ("npcs.json", "npc"),
    "npc_invader": ("npcs.json", "npc_invader"),
    "waygates": ("waygates.json", "waygate"),
    "maps": ("items.json", "map_fragment"),
}

LEVEL_TO_REGION = {
    1: "surface",
    2: "underground",
    3: "dlc",
    4: "extra",
}


def _load_dataset(source: str) -> list[dict]:
    source_path = Path(source)
    if source_path.exists():
        logger.info("Carregando dataset local: %s", source_path)
        return json.loads(source_path.read_text(encoding="utf-8"))

    logger.info("Baixando dataset de: %s", source)
    try:
        req = urllib.request.Request(source, headers={"User-Agent": "EldenRingTracker/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        logger.error("Falha ao carregar dataset: %s", exc)
        raise


def _transform_entry(raw: dict) -> dict:
    dataset_cat = raw.get("category", "")
    mapping = CATEGORY_MAP.get(dataset_cat)
    if not mapping:
        return {}
    _, category = mapping
    level = raw.get("level", 1)
    region = LEVEL_TO_REGION.get(level, "surface")

    return {
        "name": raw["name"],
        "lat": raw["x"],
        "lng": raw["y"],
        "region": region,
        "category": category,
    }



def import_dataset(source: str) -> dict[str, int]:
    raw_data = _load_dataset(source)
    logger.info("Dataset carregado: %d entradas", len(raw_data))

    file_groups: dict[str, list[dict]] = {}

    for raw in raw_data:
        entry = _transform_entry(raw)
        if not entry:
            dataset_cat = raw.get("category", "unknown")
            logger.warning("Categoria desconhecida no dataset: %s", dataset_cat)
            continue

        dataset_cat = raw.get("category", "")
        mapping = CATEGORY_MAP.get(dataset_cat)
        if mapping:
            filename = mapping[0]
            file_groups.setdefault(filename, []).append(entry)

    REFERENCES_DIR.mkdir(parents=True, exist_ok=True)
    counts = {}

    for filename, entries in file_groups.items():
        output_path = REFERENCES_DIR / filename
        entries.sort(key=lambda e: (e["region"], e["category"], e["name"]))
        output_path.write_text(
            json.dumps(entries, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        counts[filename] = len(entries)
        logger.info("  %s: %d entradas", filename, len(entries))

    return counts


def main() -> None:
    source = sys.argv[1] if len(sys.argv) > 1 else DATASET_URL
    logger.info("=== Importando dataset ===")
    counts = import_dataset(source)
    total = sum(counts.values())
    logger.info("Importação concluída: %d entradas em %d arquivos", total, len(counts))


if __name__ == "__main__":
    main()


# "Conhecimento e poder." -- Francis Bacon
