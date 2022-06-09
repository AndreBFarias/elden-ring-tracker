import struct
from pathlib import Path
from typing import Optional

from log import get_logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent
logger = get_logger("save_parser")

BND4_MAGIC = b"BND4"
SLOT_COUNT = 10
CHECKSUM_SIZE = 0x10
SLOT_DATA_SIZE = 0x280000
SLOT_STRIDE = CHECKSUM_SIZE + SLOT_DATA_SIZE

SAVE_SEARCH_PATHS = [
    PROJECT_ROOT / "assets" / "save" / "ER0000.sl2",
    Path.home() / ".steam" / "debian-installation" / "steamapps" / "compatdata"
    / "1245620" / "pfx" / "drive_c" / "users" / "steamuser" / "AppData"
    / "Roaming" / "EldenRing",
    Path.home() / ".steam" / "steam" / "steamapps" / "compatdata"
    / "1245620" / "pfx" / "drive_c" / "users" / "steamuser" / "AppData"
    / "Roaming" / "EldenRing",
]

PGD_STAT_OFFSETS = {
    "vigor": 0x34,
    "mind": 0x38,
    "endurance": 0x3C,
    "strength": 0x40,
    "dexterity": 0x44,
    "intelligence": 0x48,
    "faith": 0x4C,
    "arcane": 0x50,
}

PGD_FIELD_OFFSETS = {
    "hp": 0x08,
    "fp": 0x14,
    "stamina": 0x24,
    "level": 0x60,
    "runes_held": 0x64,
}

PGD_NAME_OFFSET = 0x94
PGD_NAME_SIZE = 32

GENERAL_SECTION_NAME_BASE = 0x196E
GENERAL_SECTION_SLOT_SPACING = 588


def find_save_file() -> Optional[Path]:
    for search_path in SAVE_SEARCH_PATHS:
        if search_path.is_file() and search_path.name == "ER0000.sl2":
            logger.info("Save encontrado: %s", search_path)
            return search_path
        if search_path.is_dir():
            for sl2 in search_path.rglob("ER0000.sl2"):
                logger.info("Save encontrado: %s", sl2)
                return sl2
    logger.warning("Nenhum save encontrado nos caminhos conhecidos")
    return None


def _get_bnd4_header_size(data: bytes) -> int:
    if len(data) < 0x18 or data[:4] != BND4_MAGIC:
        return 0
    try:
        return struct.unpack_from("<Q", data, 0x10)[0]
    except struct.error:
        return 0


def _get_slot_data(data: bytes, slot_index: int) -> Optional[bytes]:
    header_size = _get_bnd4_header_size(data)
    if header_size == 0:
        return None

    try:
        entry_header_size = struct.unpack_from("<Q", data, 0x20)[0]
        entry_offset = header_size + (slot_index * entry_header_size)
        if entry_offset + entry_header_size > len(data):
            return None
        data_offset = struct.unpack_from("<I", data, entry_offset + 0x10)[0]
    except struct.error:
        logger.error("Falha ao ler header BND4 para slot %d", slot_index)
        return None

    slot_start = data_offset + CHECKSUM_SIZE
    slot_end = slot_start + SLOT_DATA_SIZE

    if slot_end > len(data):
        return None

    return data[slot_start:slot_end]


def _find_player_game_data(slot_data: bytes) -> Optional[int]:
    stat_keys = list(PGD_STAT_OFFSETS.keys())
    first_stat_offset = PGD_STAT_OFFSETS[stat_keys[0]]

    for offset in range(0, len(slot_data) - 0xA0):
        pgd_candidate = offset - first_stat_offset
        if pgd_candidate < 0:
            continue

        vals = []
        valid = True
        for key in stat_keys:
            pos = pgd_candidate + PGD_STAT_OFFSETS[key]
            if pos + 4 > len(slot_data):
                valid = False
                break
            v = struct.unpack_from("<I", slot_data, pos)[0]
            if v < 1 or v > 99:
                valid = False
                break
            vals.append(v)

        if not valid:
            continue

        level_pos = pgd_candidate + PGD_FIELD_OFFSETS["level"]
        if level_pos + 4 > len(slot_data):
            continue

        level = struct.unpack_from("<I", slot_data, level_pos)[0]
        if level < 1 or level > 713:
            continue

        if sum(vals) == level + 79:
            logger.debug(
                "PlayerGameData em 0x%x (nível=%d)", pgd_candidate, level,
            )
            return pgd_candidate

    return None


def _read_uint32(data: bytes, offset: int) -> int:
    if offset + 4 > len(data):
        return 0
    return struct.unpack_from("<I", data, offset)[0]


def _read_float32(data: bytes, offset: int) -> float:
    if offset + 4 > len(data):
        return 0.0
    return struct.unpack_from("<f", data, offset)[0]


SECTIONS_AFTER_EVENT_FLAGS = 5
PLAYER_COORDS_SIZE = 57


def _find_player_coordinates(
    slot_data: bytes, event_offset: int,
) -> Optional[tuple[float, float, float]]:
    from event_flags import EVENT_FLAGS_SIZE

    pos = event_offset + EVENT_FLAGS_SIZE + 1
    if pos >= len(slot_data):
        return None

    for _ in range(SECTIONS_AFTER_EVENT_FLAGS):
        if pos + 4 > len(slot_data):
            return None
        section_size = struct.unpack_from("<i", slot_data, pos)[0]
        if section_size < 0 or section_size > 0x100000:
            logger.warning("Secao com tamanho invalido: %d em 0x%x", section_size, pos)
            return None
        pos += 4 + section_size

    if pos + 12 > len(slot_data):
        return None

    x = _read_float32(slot_data, pos)
    y = _read_float32(slot_data, pos + 4)
    z = _read_float32(slot_data, pos + 8)

    if any(abs(v) > 10000.0 for v in (x, y, z)):
        logger.warning(
            "Coordenadas suspeitas: x=%.2f, y=%.2f, z=%.2f em 0x%x",
            x, y, z, pos,
        )
        return None

    logger.info(
        "PlayerCoordinates em 0x%x: x=%.2f, y=%.2f, z=%.2f",
        pos, x, y, z,
    )
    return (x, y, z)


VALIDATION_FLAG_ID = 100
MANDATORY_BOSS_SEQUENCE = [9101, 9118, 9104, 9116, 9107, 9123]
SCAN_RANGE = (0x3000, 0xC0000)
SCAN_STEP_COARSE = 0x1000
SCAN_STEP_FINE = 0x10


def _score_candidate(
    slot_data: bytes, offset: int, bst_map: dict[int, int],
) -> int:
    from event_flags import EVENT_FLAGS_SIZE, read_flag

    if offset + EVENT_FLAGS_SIZE > len(slot_data):
        return 0
    chunk = slot_data[offset : offset + EVENT_FLAGS_SIZE]
    if not read_flag(chunk, VALIDATION_FLAG_ID, bst_map):
        return 0

    boss_flags = [read_flag(chunk, fid, bst_map) for fid in MANDATORY_BOSS_SEQUENCE]
    boss_count = sum(boss_flags)

    consistent = True
    seen_false = False
    for is_set in boss_flags:
        if seen_false and is_set:
            consistent = False
            break
        if not is_set:
            seen_false = True

    score = 10 + (boss_count * 3)
    if consistent:
        score += 15

    return score


def _find_event_flags(slot_data: bytes) -> Optional[int]:
    from event_flags import EVENT_FLAGS_SIZE, _load_bst_map

    bst_map = _load_bst_map()
    if not bst_map:
        logger.warning("BST map indisponivel, impossivel localizar event flags")
        return None

    max_start = len(slot_data) - EVENT_FLAGS_SIZE
    if max_start < 0:
        return None

    scan_start, scan_end = SCAN_RANGE
    scan_end = min(scan_end, max_start)

    coarse_candidates: list[int] = []
    for offset in range(scan_start, scan_end, SCAN_STEP_COARSE):
        if _score_candidate(slot_data, offset, bst_map) >= 10:
            coarse_candidates.append(offset)

    best_offset = None
    best_score = 0

    for base in coarse_candidates:
        fine_start = max(scan_start, base - SCAN_STEP_COARSE)
        fine_end = min(scan_end, base + SCAN_STEP_COARSE)
        for offset in range(fine_start, fine_end, SCAN_STEP_FINE):
            s = _score_candidate(slot_data, offset, bst_map)
            if s > best_score:
                best_score = s
                best_offset = offset

    if best_offset is not None and best_score >= 10:
        logger.info(
            "Event flags localizados em 0x%x (score=%d)", best_offset, best_score,
        )
        return best_offset

    logger.warning("Event flags nao localizados no slot")
    return None


def parse_slot(slot_index: int, save_path: Optional[Path] = None) -> Optional[dict]:
    if save_path is None:
        save_path = find_save_file()
    if save_path is None:
        return None

    try:
        raw = save_path.read_bytes()
    except OSError as exc:
        logger.error("Falha ao ler save: %s", exc)
        return None

    if raw[:4] != BND4_MAGIC:
        logger.error("Arquivo não é BND4 válido")
        return None

    slot_data = _get_slot_data(raw, slot_index)
    if slot_data is None:
        logger.error("Slot %d: dados indisponíveis", slot_index)
        return None

    if slot_data[:16] == b"\x00" * 16:
        logger.info("Slot %d: vazio", slot_index)
        return None

    pgd = _find_player_game_data(slot_data)
    if pgd is None:
        logger.warning("Slot %d: PlayerGameData não encontrado", slot_index)
        return None

    result: dict = {"ng_plus": 0}

    for stat_name, offset in PGD_STAT_OFFSETS.items():
        result[stat_name] = _read_uint32(slot_data, pgd + offset)

    for field_name, offset in PGD_FIELD_OFFSETS.items():
        result[field_name] = _read_uint32(slot_data, pgd + offset)

    name_start = pgd + PGD_NAME_OFFSET
    name_end = name_start + PGD_NAME_SIZE
    if name_end > len(slot_data):
        name_bytes = slot_data[name_start:]
    else:
        name_bytes = slot_data[name_start:name_end]
    result["name"] = name_bytes.decode("utf-16-le", errors="ignore").split("\x00")[0]

    from event_flags import (
        EVENT_FLAGS_SIZE,
        FLAG_CATEGORY_FILES,
        _load_bst_map,
        read_boss_flags,
        read_category_flags,
        read_flag,
        read_grace_flags,
    )
    from inventory_parser import parse_inventory

    event_offset = _find_event_flags(slot_data)
    if event_offset is not None:
        event_data = slot_data[event_offset : event_offset + EVENT_FLAGS_SIZE]
        result["boss_flags"] = read_boss_flags(event_data)
        result["grace_flags"] = read_grace_flags(event_data)

        for cat_key in FLAG_CATEGORY_FILES:
            if cat_key in ("boss", "grace"):
                continue
            result[f"{cat_key}_flags"] = read_category_flags(event_data, cat_key)

        bst_map = _load_bst_map()
        ending_flags = [20, 21, 22, 23, 24]
        result["ending_flags"] = [
            fid for fid in ending_flags if read_flag(event_data, fid, bst_map)
        ]

        coords = _find_player_coordinates(slot_data, event_offset)
        if coords is not None:
            result["pos_x"] = coords[0]
            result["pos_y"] = coords[1]
            result["pos_z"] = coords[2]
        else:
            result["pos_x"] = 0.0
            result["pos_y"] = 0.0
            result["pos_z"] = 0.0
    else:
        result["boss_flags"] = []
        result["grace_flags"] = []
        result["ending_flags"] = []
        for cat_key in FLAG_CATEGORY_FILES:
            if cat_key in ("boss", "grace"):
                continue
            result[f"{cat_key}_flags"] = []
        result["pos_x"] = 0.0
        result["pos_y"] = 0.0
        result["pos_z"] = 0.0

    result["inventory"] = parse_inventory(slot_data, pgd)

    logger.info(
        "Slot %d parseado: nome='%s', nível=%d, runas=%d, hp=%d",
        slot_index, result.get("name", ""),
        result.get("level", 0), result.get("runes_held", 0),
        result.get("hp", 0),
    )

    return result


def sync_to_db(slot_index: int, save_path: Optional[Path] = None) -> bool:
    from database import get_connection
    from event_flags import FLAG_CATEGORY_FILES, _load_flag_db

    data = parse_slot(slot_index, save_path)
    if data is None:
        logger.warning("Nenhum dado para sincronizar (slot %d)", slot_index)
        return False

    stats = {
        k: data[k]
        for k in (
            "level", "runes_held", "vigor", "mind", "endurance",
            "strength", "dexterity", "intelligence", "faith", "arcane",
            "hp", "fp", "stamina", "pos_x", "pos_y", "pos_z", "ng_plus",
        )
    }

    conn = get_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO player_stats (
                    slot_index, level, runes_held,
                    vigor, mind, endurance, strength, dexterity,
                    intelligence, faith, arcane,
                    hp, fp, stamina, pos_x, pos_y, pos_z, ng_plus
                ) VALUES (
                    :slot_index, :level, :runes_held,
                    :vigor, :mind, :endurance, :strength, :dexterity,
                    :intelligence, :faith, :arcane,
                    :hp, :fp, :stamina, :pos_x, :pos_y, :pos_z, :ng_plus
                )
                """,
                {"slot_index": slot_index, **stats},
            )

            for flag in data.get("boss_flags", []):
                conn.execute(
                    "INSERT OR IGNORE INTO boss_kills (slot_index, boss_flag) VALUES (?, ?)",
                    (slot_index, flag),
                )

            for flag in data.get("grace_flags", []):
                conn.execute(
                    "INSERT OR IGNORE INTO grace_discoveries (slot_index, grace_flag) VALUES (?, ?)",
                    (slot_index, flag),
                )

            for cat_key, filename in FLAG_CATEGORY_FILES.items():
                if cat_key in ("boss", "grace"):
                    continue
                flag_db = _load_flag_db(filename)
                for flag_id in data.get(f"{cat_key}_flags", []):
                    name = flag_db.get(flag_id)
                    if name:
                        conn.execute(
                            "INSERT OR IGNORE INTO item_collection (slot_index, item_name, category) VALUES (?, ?, ?)",
                            (slot_index, name, cat_key),
                        )

            for cat, names in data.get("inventory", {}).items():
                for name in names:
                    conn.execute(
                        "INSERT OR IGNORE INTO item_collection (slot_index, item_name, category) VALUES (?, ?, ?)",
                        (slot_index, name, cat),
                    )

            for ending_flag in data.get("ending_flags", []):
                conn.execute(
                    "INSERT OR IGNORE INTO endings (slot_index, ending_flag) VALUES (?, ?)",
                    (slot_index, ending_flag),
                )
    finally:
        conn.close()

    logger.info(
        "Sincronizado slot %d: %d boss flags, %d grace flags",
        slot_index, len(data.get("boss_flags", [])),
        len(data.get("grace_flags", [])),
    )
    return True


# "A simplicidade é a sofisticação suprema." -- Leonardo da Vinci
