import csv
import io
import json
import re
import urllib.request
from pathlib import Path

CSV_URL = "https://raw.githubusercontent.com/kh0nsu/EldenRingTool/main/items.csv"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCES_DIR = PROJECT_ROOT / "data" / "references"

GOODS_CATEGORIES = {"consumable", "material", "upgrade_material"}
GOODS_TYPE_NIBBLE = 0x4


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _strip_suffixes(name: str) -> str:
    name = re.sub(r"^\d+x\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name)
    name = re.sub(r"\s*-\s*\S.*$", "", name)
    name = re.sub(r"\s+x\d+\s*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+[A-F]\s*$", "", name)
    return name.strip()


def _download_csv() -> list[dict]:
    with urllib.request.urlopen(CSV_URL, timeout=30) as resp:
        content = resp.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    return list(reader)


def _build_csv_map(rows: list[dict]) -> dict[str, tuple[int, str]]:
    csv_map: dict[str, tuple[int, str]] = {}
    for row in rows:
        hex_id = (row.get("ID") or row.get("Id") or row.get("id") or "").strip()
        name = (row.get("Name") or row.get("name") or row.get("ItemName") or "").strip()
        if not hex_id or not name:
            continue
        try:
            val = int(hex_id, 16)
        except ValueError:
            continue
        if (val >> 28) & 0xF != GOODS_TYPE_NIBBLE:
            continue
        item_id = val & 0x0FFFFFFF
        key = _normalize(name)
        if key not in csv_map:
            csv_map[key] = (item_id, name)
    return csv_map


def main() -> None:
    print("Baixando CSV de itens...")
    rows = _download_csv()
    print(f"Total de linhas no CSV: {len(rows)}")

    csv_map = _build_csv_map(rows)
    print(f"Goods no CSV: {len(csv_map)} nomes unicos")

    items_path = REFERENCES_DIR / "items.json"
    with open(str(items_path), encoding="utf-8") as f:
        all_items = json.load(f)

    goods_items = [e for e in all_items if e.get("category") in GOODS_CATEGORIES]
    print(f"Entradas em items.json (goods): {len(goods_items)}")

    item_ids_path = REFERENCES_DIR / "item_ids.json"
    with open(str(item_ids_path), encoding="utf-8") as f:
        item_ids = json.load(f)

    for cat in GOODS_CATEGORIES:
        if cat not in item_ids:
            item_ids[cat] = {}

    seen: dict[int, str] = {}
    matched = 0
    unmatched: list[tuple[str, str]] = []

    for entry in goods_items:
        raw_name = entry["name"]
        cat = entry["category"]

        base_name = _strip_suffixes(raw_name)
        norm_key = _normalize(base_name)

        result = csv_map.get(norm_key)
        if result is not None:
            item_id, canonical = result
            if item_id not in seen:
                item_ids[cat][str(item_id)] = canonical
                seen[item_id] = canonical
                matched += 1
        else:
            direct = csv_map.get(_normalize(raw_name))
            if direct is not None:
                item_id, canonical = direct
                if item_id not in seen:
                    item_ids[cat][str(item_id)] = canonical
                    seen[item_id] = canonical
                    matched += 1
            else:
                unmatched.append((cat, raw_name))

    print(f"\nIDs mapeados: {matched}")
    if unmatched:
        unique_unmatched = sorted(set(unmatched))
        print(f"Sem match ({len(unique_unmatched)} unicos):")
        for cat, name in unique_unmatched[:20]:
            print(f"  [{cat}] {name}")
        if len(unique_unmatched) > 20:
            print(f"  ... e mais {len(unique_unmatched) - 20}")

    with open(str(item_ids_path), "w", encoding="utf-8") as f:
        json.dump(item_ids, f, indent=2, ensure_ascii=False)

    print("\nitem_ids.json atualizado.")
    for cat in GOODS_CATEGORIES:
        print(f"  {cat}: {len(item_ids[cat])} IDs")


if __name__ == "__main__":
    main()


# "Conhecimento sem prática é vento sem vela." -- Benjamin Franklin
