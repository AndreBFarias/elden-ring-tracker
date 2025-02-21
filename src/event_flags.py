import json
from pathlib import Path

from log import get_logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REFERENCES_DIR = DATA_DIR / "references"

logger = get_logger("event_flags")

EVENT_FLAGS_SIZE = 0x1BF99F
BLOCK_SIZE = 125
FLAG_DIVISOR = 1000

VALIDATION_FLAG = 100

FLAG_CATEGORY_FILES: dict[str, str] = {
    "boss": "boss_flags.json",
    "grace": "grace_flags.json",
    "flask_upgrade": "crystal_tear_flags.json",
    "ash_of_war": "ash_of_war_flags.json",
    "map_fragment": "map_fragment_flags.json",
    "key_item": "key_item_flags.json",
    "npc": "npc_dead_flags.json",
}

_bst_map: dict[int, int] | None = None
_boss_flags_db: dict[int, dict] | None = None
_grace_flags_db: dict[int, str] | None = None
_flag_db_cache: dict[str, dict[int, str]] = {}


def _load_bst_map() -> dict[int, int]:
    global _bst_map
    if _bst_map is not None:
        return _bst_map

    bst_path = DATA_DIR / "eventflag_bst.txt"
    result: dict[int, int] = {}
    try:
        with open(str(bst_path), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(",")
                if len(parts) != 2:
                    continue
                block_id = int(parts[0])
                offset_index = int(parts[1])
                result[block_id] = offset_index
    except (OSError, ValueError) as exc:
        logger.error("Falha ao carregar BST map: %s", exc)
        return {}

    logger.info("BST map carregado: %d blocos", len(result))
    _bst_map = result
    return _bst_map


def _load_boss_flags() -> dict[int, dict]:
    global _boss_flags_db
    if _boss_flags_db is not None:
        return _boss_flags_db

    path = REFERENCES_DIR / "boss_flags.json"
    try:
        with open(str(path), encoding="utf-8") as f:
            raw = json.load(f)
        _boss_flags_db = {int(k): v for k, v in raw.items()}
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        logger.error("Falha ao carregar boss_flags.json: %s", exc)
        _boss_flags_db = {}

    return _boss_flags_db


def _load_grace_flags() -> dict[int, str]:
    global _grace_flags_db
    if _grace_flags_db is not None:
        return _grace_flags_db

    path = REFERENCES_DIR / "grace_flags.json"
    try:
        with open(str(path), encoding="utf-8") as f:
            raw = json.load(f)
        _grace_flags_db = {int(k): v for k, v in raw.items()}
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        logger.error("Falha ao carregar grace_flags.json: %s", exc)
        _grace_flags_db = {}

    return _grace_flags_db


def read_flag(event_flags: bytes, flag_id: int, bst_map: dict[int, int]) -> bool:
    block = flag_id // FLAG_DIVISOR
    index = flag_id % FLAG_DIVISOR

    if block not in bst_map:
        logger.warning("Flag %d: bloco %d ausente no BST map", flag_id, block)
        return False

    offset = bst_map[block] * BLOCK_SIZE
    byte_index = index // 8
    bit_index = 7 - (index % 8)
    pos = offset + byte_index

    if pos >= len(event_flags):
        logger.warning("Flag %d: posição 0x%x fora dos limites (tamanho=0x%x)", flag_id, pos, len(event_flags))
        return False

    return bool(event_flags[pos] & (1 << bit_index))


def read_flags_batch(
    event_flags: bytes,
    flag_ids: list[int],
    bst_map: dict[int, int],
) -> dict[int, bool]:
    return {fid: read_flag(event_flags, fid, bst_map) for fid in flag_ids}


def read_boss_flags(event_flags: bytes) -> list[int]:
    bst_map = _load_bst_map()
    if not bst_map:
        return []

    boss_db = _load_boss_flags()
    if not boss_db:
        return []

    active: list[int] = []
    for flag_id in boss_db:
        if read_flag(event_flags, flag_id, bst_map):
            active.append(flag_id)

    logger.debug("Boss flags ativos: %d/%d", len(active), len(boss_db))
    return active


def read_grace_flags(event_flags: bytes) -> list[int]:
    bst_map = _load_bst_map()
    if not bst_map:
        return []

    grace_db = _load_grace_flags()
    if not grace_db:
        return []

    active: list[int] = []
    for flag_id in grace_db:
        if read_flag(event_flags, flag_id, bst_map):
            active.append(flag_id)

    logger.debug("Grace flags ativos: %d/%d", len(active), len(grace_db))
    return active


def _load_flag_db(filename: str) -> dict[int, str]:
    if filename in _flag_db_cache:
        return _flag_db_cache[filename]

    path = REFERENCES_DIR / filename
    try:
        with open(str(path), encoding="utf-8") as f:
            raw = json.load(f)
        result = {int(k): v for k, v in raw.items()}
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        logger.error("Falha ao carregar %s: %s", filename, exc)
        result = {}

    _flag_db_cache[filename] = result
    logger.info("Flag DB carregado: %s (%d entradas)", filename, len(result))
    return result


def read_category_flags(event_flags: bytes, category: str) -> list[int]:
    filename = FLAG_CATEGORY_FILES.get(category)
    if not filename:
        return []

    bst_map = _load_bst_map()
    if not bst_map:
        return []

    flag_db = _load_flag_db(filename)
    if not flag_db:
        return []

    active: list[int] = []
    for flag_id in flag_db:
        if read_flag(event_flags, flag_id, bst_map):
            active.append(flag_id)

    logger.debug(
        "%s flags ativos: %d/%d", category, len(active), len(flag_db),
    )
    return active


def validate_event_flags(event_flags: bytes) -> bool:
    bst_map = _load_bst_map()
    if not bst_map:
        return False
    return read_flag(event_flags, VALIDATION_FLAG, bst_map)


# "A verdade é como um leão; não precisas defendê-la. Solta-a." -- Santo Agostinho
