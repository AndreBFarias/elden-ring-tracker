import json
import struct
from pathlib import Path

from log import get_logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCES_DIR = PROJECT_ROOT / "data" / "references"

logger = get_logger("inventory")

ENTRY_SIZE = 12
TYPE_WEAPON = 0x0
TYPE_ARMOR = 0x1
TYPE_TALISMAN = 0x2
TYPE_GOODS = 0x4
TYPE_ASH = 0x8

TYPE_NAMES = {
    TYPE_WEAPON: "weapon",
    TYPE_ARMOR: "armor",
    TYPE_TALISMAN: "talisman",
    TYPE_GOODS: "goods",
    TYPE_ASH: "ash_of_war",
}

TRACKED_CATEGORIES = {"weapon", "armor", "shield", "talisman", "spell", "consumable", "material"}

WEAPON_REINFORCE_STEP = 10000
SHIELD_RANGE_MIN = 30000000
SHIELD_RANGE_MAX = 33000000

MIN_CLUSTER_ENTRIES = 5
MAX_SKIP_ENTRIES = 8
SCAN_ALIGNMENT = 4
INVENTORY_SCAN_RANGE = 0x20000

_item_ids: dict[str, dict[int, str]] | None = None


def _load_item_ids() -> dict[str, dict[int, str]]:
    global _item_ids
    if _item_ids is not None:
        return _item_ids

    path = REFERENCES_DIR / "item_ids.json"
    try:
        with open(str(path), encoding="utf-8") as f:
            raw = json.load(f)
        _item_ids = {}
        for category, entries in raw.items():
            _item_ids[category] = {int(k): v for k, v in entries.items()}
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        logger.error("Falha ao carregar item_ids.json: %s", exc)
        _item_ids = {}

    return _item_ids


def _normalize_weapon_id(item_id: int) -> int:
    return (item_id // WEAPON_REINFORCE_STEP) * WEAPON_REINFORCE_STEP


def _classify_handle(ga_item_handle: int) -> tuple[str, int]:
    type_nibble = (ga_item_handle >> 28) & 0xF
    item_id = ga_item_handle & 0x0FFFFFFF

    type_name = TYPE_NAMES.get(type_nibble, "")
    if not type_name:
        return "", item_id

    if type_name == "weapon":
        if SHIELD_RANGE_MIN <= item_id < SHIELD_RANGE_MAX:
            type_name = "shield"

    return type_name, item_id


def _resolve_name(
    type_name: str, item_id: int, db: dict[str, dict[int, str]],
) -> str:
    lookup = type_name
    if type_name == "goods":
        if 4000 <= item_id < 8000:
            lookup = "spell"
        elif item_id < 4000:
            lookup = "consumable"
        else:
            lookup = "material"

    id_map = db.get(lookup, {})
    if not id_map:
        return ""

    name = id_map.get(item_id)
    if name:
        return name

    if lookup in ("weapon", "shield"):
        base_id = _normalize_weapon_id(item_id)
        return id_map.get(base_id, "")

    return ""


def _is_valid_entry(slot_data: bytes, pos: int) -> bool:
    if pos + ENTRY_SIZE > len(slot_data):
        return False
    handle = struct.unpack_from("<I", slot_data, pos)[0]
    if handle == 0:
        return False
    type_nibble = (handle >> 28) & 0xF
    if type_nibble not in TYPE_NAMES:
        return False
    qty = struct.unpack_from("<I", slot_data, pos + 4)[0]
    return 1 <= qty <= 999


def _find_inventory_regions(
    slot_data: bytes, pgd_offset: int, db: dict[str, dict[int, str]],
) -> list[tuple[int, int]]:
    search_start = pgd_offset + 0x200
    search_end = min(
        len(slot_data) - ENTRY_SIZE,
        pgd_offset + INVENTORY_SCAN_RANGE,
    )

    if search_end <= search_start:
        return []

    regions: list[tuple[int, int]] = []
    pos = search_start

    while pos < search_end:
        if not _is_valid_entry(slot_data, pos):
            pos += SCAN_ALIGNMENT
            continue

        region_start = pos
        valid_count = 0
        resolved_count = 0
        skip_count = 0
        scan_pos = pos

        while scan_pos < search_end:
            if _is_valid_entry(slot_data, scan_pos):
                valid_count += 1
                skip_count = 0
                handle = struct.unpack_from("<I", slot_data, scan_pos)[0]
                type_name, item_id = _classify_handle(handle)
                if type_name and _resolve_name(type_name, item_id, db):
                    resolved_count += 1
                scan_pos += ENTRY_SIZE
            else:
                skip_count += 1
                if skip_count > MAX_SKIP_ENTRIES:
                    break
                scan_pos += ENTRY_SIZE

        if valid_count >= MIN_CLUSTER_ENTRIES and resolved_count >= 3:
            regions.append((region_start, scan_pos))
            logger.debug(
                "Região de inventário: 0x%x-0x%x (%d entries, %d resolved)",
                region_start, scan_pos, valid_count, resolved_count,
            )

        pos = scan_pos + SCAN_ALIGNMENT

    return regions


def parse_inventory(
    slot_data: bytes, pgd_offset: int,
) -> dict[str, list[str]]:
    db = _load_item_ids()
    if not db:
        return {}

    regions = _find_inventory_regions(slot_data, pgd_offset, db)
    if not regions:
        logger.warning("Nenhuma região de inventário encontrada")
        return {}

    result: dict[str, set[str]] = {cat: set() for cat in TRACKED_CATEGORIES}

    for region_start, region_end in regions:
        pos = region_start
        while pos < region_end:
            if pos + ENTRY_SIZE > len(slot_data):
                break

            handle = struct.unpack_from("<I", slot_data, pos)[0]
            qty = struct.unpack_from("<I", slot_data, pos + 4)[0]
            pos += ENTRY_SIZE

            if handle == 0:
                continue
            if qty < 1 or qty > 999:
                continue

            type_name, item_id = _classify_handle(handle)
            if not type_name or type_name not in result:
                continue

            name = _resolve_name(type_name, item_id, db)
            if name:
                result[type_name].add(name)

    output: dict[str, list[str]] = {
        cat: sorted(names) for cat, names in result.items() if names
    }

    for cat, names in output.items():
        logger.info("Inventário %s: %d itens detectados", cat, len(names))

    return output


# "Quem controla o passado controla o futuro." -- George Orwell
