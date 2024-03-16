import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from event_flags import (
    FLAG_CATEGORY_FILES,
    _load_boss_flags,
    _load_bst_map,
    _load_flag_db,
    _load_grace_flags,
    read_flag,
)
from log import get_logger
from save_parser import _find_event_flags, _get_slot_data, find_save_file

BND4_MAGIC = b"BND4"
EVENT_FLAGS_SIZE = 0x1BF99F

logger = get_logger("diagnose_flags")


def _scan_boss(event_data: bytes, bst_map: dict[int, int]) -> list[tuple[int, str]]:
    boss_db = _load_boss_flags()
    active: list[tuple[int, str]] = []
    for flag_id, info in boss_db.items():
        if read_flag(event_data, flag_id, bst_map):
            active.append((flag_id, info["name"]))
    return sorted(active, key=lambda x: x[0])


def _scan_grace(event_data: bytes, bst_map: dict[int, int]) -> list[tuple[int, str]]:
    grace_db = _load_grace_flags()
    active: list[tuple[int, str]] = []
    for flag_id, name in grace_db.items():
        if read_flag(event_data, flag_id, bst_map):
            active.append((flag_id, name))
    return sorted(active, key=lambda x: x[0])


def _scan_category(
    event_data: bytes, bst_map: dict[int, int], cat_key: str, filename: str
) -> list[tuple[int, str]]:
    flag_db = _load_flag_db(filename)
    active: list[tuple[int, str]] = []
    for flag_id, name in flag_db.items():
        if read_flag(event_data, flag_id, bst_map):
            active.append((flag_id, name))
    return sorted(active, key=lambda x: x[0])


def diagnose(save_path: Path, slot_index: int, category: str) -> None:
    raw = save_path.read_bytes()

    if raw[:4] != BND4_MAGIC:
        print(f"ERRO: arquivo nao e BND4 valido: {save_path}")
        sys.exit(1)

    slot_data = _get_slot_data(raw, slot_index)
    if slot_data is None:
        print(f"ERRO: slot {slot_index} indisponivel")
        sys.exit(1)

    event_offset = _find_event_flags(slot_data)
    if event_offset is None:
        print(f"ERRO: event flags nao localizados no slot {slot_index}")
        sys.exit(1)

    event_data = slot_data[event_offset : event_offset + EVENT_FLAGS_SIZE]
    bst_map = _load_bst_map()

    print(f"=== DIAGNOSTICO: slot={slot_index}, offset=0x{event_offset:x} ===\n")

    total_active = 0

    if category in ("all", "boss"):
        results = _scan_boss(event_data, bst_map)
        total_active += len(results)
        db_size = len(_load_boss_flags())
        print(f"[BOSS] {len(results)}/{db_size} ativos:")
        for flag_id, name in results:
            print(f"    {flag_id} | {name}")
        print()

    if category in ("all", "grace"):
        results = _scan_grace(event_data, bst_map)
        total_active += len(results)
        db_size = len(_load_grace_flags())
        print(f"[GRACE] {len(results)}/{db_size} ativos:")
        for flag_id, name in results:
            print(f"    {flag_id} | {name}")
        print()

    if category == "all":
        for cat_key, filename in FLAG_CATEGORY_FILES.items():
            if cat_key in ("boss", "grace"):
                continue
            results = _scan_category(event_data, bst_map, cat_key, filename)
            total_active += len(results)
            db_size = len(_load_flag_db(filename))
            print(f"[{cat_key.upper()}] {len(results)}/{db_size} ativos:")
            for flag_id, name in results:
                print(f"    {flag_id} | {name}")
            print()

    print(f"Total flags ativos: {total_active}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Lista event flags ativos no save de Elden Ring"
    )
    parser.add_argument(
        "--save",
        type=Path,
        help="Caminho para ER0000.sl2 (opcional, usa config se omitido)",
    )
    parser.add_argument(
        "--slot",
        type=int,
        default=0,
        help="Indice do slot (0-9, padrao: 0)",
    )
    parser.add_argument(
        "--category",
        choices=["all", "boss", "grace"],
        default="all",
        help="Categoria a escanear (padrao: all)",
    )
    args = parser.parse_args()

    save_path = args.save
    if save_path is None:
        save_path = find_save_file()
    if save_path is None:
        print("ERRO: save nao encontrado. Use --save para especificar o caminho.")
        sys.exit(1)

    if not save_path.is_file():
        print(f"ERRO: arquivo nao encontrado: {save_path}")
        sys.exit(1)

    diagnose(save_path, args.slot, args.category)


if __name__ == "__main__":
    main()


# "Conhece-te a ti mesmo." -- Socrates
