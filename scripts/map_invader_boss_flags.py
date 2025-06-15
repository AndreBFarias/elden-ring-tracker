import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCES_DIR = PROJECT_ROOT / "data" / "references"

LOCATION_SUFFIXES = re.compile(
    r"\s*[-–]\s*(enir-ilim|royal capital moat|belurat tower settlement|"
    r"ruined forge lava intake|dragon['']s pit|writheblood ruins|"
    r"mountaintops.*|limgrave.*|liurnia.*|altus.*|caelid.*)[^)]*$",
    re.IGNORECASE,
)

PARENTHESES = re.compile(r"\s*\([^)]+\)")


def _normalize(name: str) -> str:
    name = LOCATION_SUFFIXES.sub("", name)
    name = PARENTHESES.sub("", name)
    return re.sub(r"[^a-z0-9]", "", name.lower().strip())



MANUAL_INVADER_FLAGS: dict[str, int] = {
    "Sanguine Noble": 1040530800,
    "Ancient Dragon-Man - Ruined Forge Lava Intake": 43010800,
    "Festering Fingerprint Vyke": 1053560800,
}


def main() -> None:
    npcs_path = REFERENCES_DIR / "npcs.json"
    boss_flags_path = REFERENCES_DIR / "boss_flags.json"

    with open(str(npcs_path), encoding="utf-8") as f:
        npcs: list[dict] = json.load(f)

    with open(str(boss_flags_path), encoding="utf-8") as f:
        boss_flags_raw: dict = json.load(f)

    boss_flags: dict[int, dict] = {int(k): v for k, v in boss_flags_raw.items()}

    boss_by_norm: dict[str, list[tuple[int, str]]] = {}
    for flag_id, info in boss_flags.items():
        norm = _normalize(info["name"])
        if norm not in boss_by_norm:
            boss_by_norm[norm] = []
        boss_by_norm[norm].append((flag_id, info["name"]))

    invaders = [e for e in npcs if e.get("category") == "npc_invader"]
    matched = 0
    unmatched_names: list[str] = []

    for entry in invaders:
        name = entry["name"]

        if name in MANUAL_INVADER_FLAGS:
            entry["boss_flag"] = MANUAL_INVADER_FLAGS[name]
            matched += 1
            print(f"  [manual] {name} -> {MANUAL_INVADER_FLAGS[name]}")
            continue

        norm_inv = _normalize(name)
        candidates = boss_by_norm.get(norm_inv)

        if not candidates:
            entry["boss_flag"] = None
            unmatched_names.append(name)
            continue

        flag_id, boss_name = candidates[0]
        entry["boss_flag"] = flag_id
        matched += 1
        print(f"  [auto]   {name} -> {flag_id} ({boss_name})")

    for entry in invaders:
        if "boss_flag" not in entry:
            entry["boss_flag"] = None

    with open(str(npcs_path), "w", encoding="utf-8") as f:
        json.dump(npcs, f, indent=2, ensure_ascii=False)

    print(f"\nInvasores processados: {len(invaders)}")
    print(f"  Com boss_flag linkada: {matched}")
    print(f"  Sem match: {len(unmatched_names)}")
    if unmatched_names:
        print("  Nao mapeados:")
        for n in unmatched_names:
            print(f"    - {n}")
    print(f"Arquivo salvo: {npcs_path}")


if __name__ == "__main__":
    main()


# "O homem que move montanhas comeca carregando pequenas pedras." -- Confucio
