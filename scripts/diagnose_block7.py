import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from event_flags import _load_bst_map, read_flag
from save_parser import _find_event_flags, _get_slot_data, find_save_file

BND4_MAGIC = b"BND4"
EVENT_FLAGS_SIZE = 0x1BF99F

BLOCK7_RANGE_START = 7000
BLOCK7_RANGE_END = 7999

KNOWN_FLAGS: dict[int, str] = {
    7606: "Iron Fist Alexander",
    7611: "Millicent",
}


def scan_block7(event_data: bytes, bst_map: dict[int, int]) -> list[int]:
    active: list[int] = []
    for flag_id in range(BLOCK7_RANGE_START, BLOCK7_RANGE_END + 1):
        if read_flag(event_data, flag_id, bst_map):
            active.append(flag_id)
    return active


def analyze_scattered(active: list[int]) -> None:
    regular_ranges = [
        (7040, 7071),
        (7080, 7111),
        (7120, 7151),
        (7160, 7191),
        (7200, 7231),
        (7240, 7271),
        (7280, 7311),
        (7320, 7351),
        (7360, 7391),
        (7400, 7431),
        (7440, 7471),
        (7480, 7511),
        (7520, 7551),
        (7560, 7591),
        (7600, 7631),
        (7640, 7671),
        (7680, 7711),
    ]

    def in_regular(flag_id: int) -> bool:
        return any(lo <= flag_id <= hi for lo, hi in regular_ranges)

    scattered = [f for f in active if not in_regular(f)]
    return scattered


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Escaneia block 7 do event flags para identificar flags de NPCs/invasores"
    )
    parser.add_argument("--save", type=Path, help="Caminho para ER0000.sl2")
    parser.add_argument("--slot", type=int, default=0, help="Indice do slot (padrao: 0)")
    parser.add_argument("--full", action="store_true", help="Mostrar todos os flags ativos do block 7")
    args = parser.parse_args()

    save_path = args.save or find_save_file()
    if save_path is None:
        print("ERRO: save nao encontrado. Use --save para especificar.")
        sys.exit(1)
    if not save_path.is_file():
        print(f"ERRO: arquivo nao encontrado: {save_path}")
        sys.exit(1)

    raw = save_path.read_bytes()
    if raw[:4] != BND4_MAGIC:
        print(f"ERRO: arquivo nao e BND4 valido: {save_path}")
        sys.exit(1)

    slot_data = _get_slot_data(raw, args.slot)
    if slot_data is None:
        print(f"ERRO: slot {args.slot} indisponivel")
        sys.exit(1)

    event_offset = _find_event_flags(slot_data)
    if event_offset is None:
        print(f"ERRO: event flags nao localizados no slot {args.slot}")
        sys.exit(1)

    event_data = slot_data[event_offset : event_offset + EVENT_FLAGS_SIZE]
    bst_map = _load_bst_map()

    active = scan_block7(event_data, bst_map)
    scattered = analyze_scattered(active)

    print(f"=== BLOCK 7 SCAN: slot={args.slot} ===")
    print(f"Flags ativos no block 7: {len(active)}/{BLOCK7_RANGE_END - BLOCK7_RANGE_START + 1}")

    print()
    print("[REFERENCIAS CONHECIDAS]")
    for flag_id, name in KNOWN_FLAGS.items():
        state = "SET" if flag_id in active else "not set"
        print(f"  {flag_id}: {name} [{state}]")

    print()
    print(f"[FLAGS SCATTERED (fora dos ranges regulares)]: {len(scattered)}")
    if scattered:
        prev = None
        for flag_id in scattered:
            diff = f" (delta={flag_id - prev})" if prev is not None else ""
            label = KNOWN_FLAGS.get(flag_id, "")
            suffix = f" -- {label}" if label else ""
            print(f"  {flag_id}{diff}{suffix}")
            prev = flag_id

    if args.full:
        print()
        print("[TODOS OS FLAGS ATIVOS NO BLOCK 7]")
        for flag_id in active:
            label = KNOWN_FLAGS.get(flag_id, "")
            suffix = f" -- {label}" if label else ""
            print(f"  {flag_id}{suffix}")


if __name__ == "__main__":
    main()


# "Nao e a forca, mas o conhecimento que vence." -- Francis Bacon
