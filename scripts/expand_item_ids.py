"""Expande item_ids.json com IDs de fontes externas.

Fonte: Hapfel1/er-save-manager src/er_save_manager/data/items/*.txt
Formato dos .txt: "base_id nome_do_item" por linha.

Categorias expandidas:
  - talisman: Talismans.txt + DLCTalismans.txt
  - consumable: Consumables.txt + DLCConsumables.txt + Tools.txt
  - material: CraftingMaterials.txt + DLCCraftingMaterials.txt
  - upgrade_material: UpgradeMaterials.txt + DLCUpgradeMaterials.txt
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fetch_utils import (
    REFERENCES_DIR,
    backup_file,
    fetch_raw_github,
    save_json,
)
from log import get_logger

logger = get_logger("expand_item_ids")

ERSM_ITEMS_PATH = "src/er_save_manager/data/items"

SOURCE_MAP: dict[str, list[str]] = {
    "talisman": [
        "Talismans.txt",
        "DLC/DLCTalismans.txt",
    ],
    "consumable": [
        "Goods/Consumables.txt",
        "DLC/DLCGoods/DLCConsumables.txt",
        "Goods/Tools.txt",
        "DLC/DLCGoods/DLCTools.txt",
    ],
    "material": [
        "Goods/CraftingMaterials.txt",
        "DLC/DLCGoods/DLCCraftingMaterials.txt",
    ],
    "upgrade_material": [
        "Goods/UpgradeMaterials.txt",
        "DLC/DLCGoods/DLCUpgradeMaterials.txt",
    ],
    "weapon": [
        "Weapons/MeleeWeapons.txt",
        "Weapons/RangedWeapons.txt",
        "Weapons/SpellTools.txt",
        "DLC/DLCWeapons/DLCMeleeWeapons.txt",
        "DLC/DLCWeapons/DLCRangedWeapons.txt",
        "DLC/DLCWeapons/DLCSpellTools.txt",
    ],
    "armor": [
        "Armor.txt",
        "DLC/DLCArmor.txt",
    ],
    "shield": [
        "Weapons/Shields.txt",
        "DLC/DLCWeapons/DLCShields.txt",
    ],
    "spell": [
        "Magic.txt",
        "DLC/DLCMagic.txt",
    ],
}


def parse_item_txt(content: str) -> dict[int, str]:
    """Parse arquivo .txt do er-save-manager: 'base_id item_name' por linha."""
    items: dict[int, str] = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"(\d+)\s+(.+)", line)
        if match:
            base_id = int(match.group(1))
            name = match.group(2).strip()
            items[base_id] = name
    return items


def fetch_category_items(category: str, filenames: list[str]) -> dict[int, str]:
    """Busca e parseia todos os .txt de uma categoria."""
    merged: dict[int, str] = {}
    for filename in filenames:
        path = f"{ERSM_ITEMS_PATH}/{filename}"
        try:
            content = fetch_raw_github("Hapfel1", "er-save-manager", "main", path)
            items = parse_item_txt(content)
            merged.update(items)
            logger.info("  %s: %d itens", filename, len(items))
        except Exception as exc:
            logger.warning("  Falha ao buscar %s: %s", filename, exc)
            print(f"  AVISO: {filename}: {exc}")
    return merged


def main() -> None:
    logger.info("Iniciando expansao de item_ids.json")

    item_ids_path = REFERENCES_DIR / "item_ids.json"
    backup_file(item_ids_path)

    with open(item_ids_path, encoding="utf-8") as f:
        item_ids: dict[str, dict[str, str]] = json.load(f)

    total_added = 0
    results: list[tuple[str, int, int, int]] = []

    for category, filenames in SOURCE_MAP.items():
        print(f"\n[{category}]")
        logger.info("Processando categoria: %s", category)

        external = fetch_category_items(category, filenames)
        if not external:
            print(f"  Nenhum item obtido de fontes externas")
            continue

        if category not in item_ids:
            item_ids[category] = {}

        current = item_ids[category]
        before = len(current)
        added = 0

        for base_id, name in sorted(external.items()):
            key = str(base_id)
            if key not in current:
                current[key] = name
                added += 1

        total_added += added
        after = len(current)
        results.append((category, before, after, added))

        print(f"  Fonte externa: {len(external)} IDs")
        print(f"  Antes: {before}, Adicionados: {added}, Total: {after}")
        logger.info(
            "  %s: %d -> %d (+%d)", category, before, after, added,
        )

    sorted_ids: dict[str, dict[str, str]] = {}
    for cat in item_ids:
        entries = item_ids[cat]
        sorted_entries = dict(sorted(entries.items(), key=lambda x: int(x[0])))
        sorted_ids[cat] = sorted_entries

    save_json(item_ids_path, sorted_ids)

    print(f"\n{'='*50}")
    print(f"Resumo da expansao de item_ids.json:")
    print(f"{'='*50}")
    for category, before, after, added in results:
        print(f"  {category}: {before} -> {after} (+{added})")
    print(f"  Total adicionado: {total_added}")

    all_total = sum(len(v) for v in sorted_ids.values())
    print(f"  Total geral item_ids.json: {all_total}")

    logger.info("Expansao concluida: +%d IDs (total: %d)", total_added, all_total)


if __name__ == "__main__":
    main()


# "O conhecimento e a unica riqueza que aumenta quando compartilhada." -- Socrates
