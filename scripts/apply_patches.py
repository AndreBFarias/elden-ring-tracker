"""Aplica golden patches sobre os arquivos de referência JSON.

Patches ficam em data/patches/ e são editados manualmente. Este script
lê cada patch e sobrescreve apenas os campos com valores concretos
(não-null / não-vazio) nas entradas correspondentes por nome.

É idempotente: pode ser rodado múltiplas vezes sem corromper dados.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATCHES_DIR = ROOT / "data" / "patches"
REFERENCES_DIR = ROOT / "data" / "references"


def _apply_patch(
    ref_path: Path,
    patch_entries: list[dict],
    key_field: str,
    patch_fields: list[str],
) -> tuple[int, int, int]:
    """Aplica patch sobre um arquivo de referência.

    Retorna (aplicados, ignorados_null, nao_encontrados).
    """
    with open(str(ref_path), encoding="utf-8") as f:
        ref_data = json.load(f)

    index: dict[str, int] = {entry.get("name", ""): i for i, entry in enumerate(ref_data)}

    aplicados = 0
    ignorados = 0
    nao_encontrados = 0

    for patch in patch_entries:
        name = patch.get("name", "")
        if name not in index:
            nao_encontrados += 1
            continue

        has_concrete = False
        for field in patch_fields:
            val = patch.get(field)
            if val is None:
                continue
            if isinstance(val, list) and len(val) == 0:
                continue
            has_concrete = True

        if not has_concrete:
            ignorados += 1
            continue

        idx = index[name]
        for field in patch_fields:
            val = patch.get(field)
            if val is None:
                continue
            if isinstance(val, list) and len(val) == 0:
                continue
            ref_data[idx][field] = val

        aplicados += 1

    with open(str(ref_path), "w", encoding="utf-8") as f:
        json.dump(ref_data, f, ensure_ascii=False, indent=2)

    return aplicados, ignorados, nao_encontrados


def apply_npc_invaders() -> None:
    patch_path = PATCHES_DIR / "npc_invaders.json"
    if not patch_path.exists():
        print(f"[AVISO] Patch nao encontrado: {patch_path}")
        return

    with open(str(patch_path), encoding="utf-8") as f:
        patch_data = json.load(f)

    entries = patch_data.get("invasores", [])
    ref_path = REFERENCES_DIR / "npcs.json"
    aplicados, ignorados, nao_encontrados = _apply_patch(
        ref_path, entries, key_field="name", patch_fields=["boss_flag"]
    )
    print(f"NPC invaders  | aplicados: {aplicados:3d}  ignorados (null): {ignorados:3d}  nao encontrados: {nao_encontrados:3d}")


def apply_dungeons() -> None:
    patch_path = PATCHES_DIR / "dungeons.json"
    if not patch_path.exists():
        print(f"[AVISO] Patch nao encontrado: {patch_path}")
        return

    with open(str(patch_path), encoding="utf-8") as f:
        patch_data = json.load(f)

    entries = patch_data.get("dungeons", [])
    ref_path = REFERENCES_DIR / "dungeons.json"
    aplicados, ignorados, nao_encontrados = _apply_patch(
        ref_path, entries, key_field="name", patch_fields=["boss_flags"]
    )
    print(f"Dungeons      | aplicados: {aplicados:3d}  ignorados (vazio): {ignorados:3d}  nao encontrados: {nao_encontrados:3d}")


def main() -> None:
    print("=== apply_patches.py ===")
    apply_npc_invaders()
    apply_dungeons()
    print("Concluido.")


if __name__ == "__main__":
    main()


# "Nao ha nada permanente exceto a mudanca." -- Heraclito
