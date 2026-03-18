"""Validacao cruzada dos arquivos de referencia.

Cruza boss_flags <-> bosses, grace_flags <-> graces, e reporta:
- Flags orfaos (existem no _flags.json mas nao em bosses/graces.json)
- Entradas sem flag (existem em bosses/graces.json com flag null)
- Duplicatas de nome
- Flags referenciados em bosses/graces que nao existem em _flags.json
- Inconsistencias de contagem
"""

import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCES_DIR = PROJECT_ROOT / "data" / "references"


def load_json(filename: str) -> dict | list:
    path = REFERENCES_DIR / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_bosses() -> list[str]:
    issues: list[str] = []

    boss_flags = load_json("boss_flags.json")
    bosses = load_json("bosses.json")

    bf_keys = {int(k) for k in boss_flags}
    boss_flag_values = {b["flag"] for b in bosses if b.get("flag") is not None}
    boss_null_flags = [b["name"] for b in bosses if b.get("flag") is None]

    orphan_flags = bf_keys - boss_flag_values
    missing_in_bf = boss_flag_values - bf_keys

    issues.append(f"[BOSS] boss_flags.json: {len(boss_flags)} entradas")
    issues.append(f"[BOSS] bosses.json: {len(bosses)} entradas ({len(bosses) - len(boss_null_flags)} com flag)")

    if boss_null_flags:
        issues.append(f"[BOSS] AVISO: {len(boss_null_flags)} bosses sem flag:")
        for name in sorted(boss_null_flags):
            issues.append(f"  - {name}")

    if missing_in_bf:
        issues.append(f"[BOSS] ERRO: {len(missing_in_bf)} flags referenciados em bosses.json ausentes de boss_flags.json:")
        for fid in sorted(missing_in_bf):
            boss_name = next((b["name"] for b in bosses if b.get("flag") == fid), "?")
            issues.append(f"  - flag {fid} ({boss_name})")

    if orphan_flags:
        issues.append(f"[BOSS] INFO: {len(orphan_flags)} flags em boss_flags.json sem correspondencia em bosses.json")

    name_counts = Counter(b["name"] for b in bosses)
    dupes = {name: count for name, count in name_counts.items() if count > 1}
    if dupes:
        issues.append(f"[BOSS] AVISO: {len(dupes)} nomes duplicados em bosses.json:")
        for name, count in sorted(dupes.items()):
            issues.append(f"  - {name} (x{count})")

    flag_counts = Counter(b["flag"] for b in bosses if b.get("flag") is not None)
    flag_dupes = {fid: count for fid, count in flag_counts.items() if count > 1}
    if flag_dupes:
        issues.append(f"[BOSS] AVISO: {len(flag_dupes)} flags duplicados em bosses.json:")
        for fid, count in sorted(flag_dupes.items()):
            names = [b["name"] for b in bosses if b.get("flag") == fid]
            issues.append(f"  - flag {fid} usado por: {', '.join(names)}")

    return issues


def validate_graces() -> list[str]:
    issues: list[str] = []

    grace_flags = load_json("grace_flags.json")
    graces = load_json("graces.json")

    gf_keys = {int(k) for k in grace_flags}
    grace_flag_values = {g["flag"] for g in graces if g.get("flag") is not None}
    grace_null_flags = [g for g in graces if g.get("flag") is None]

    null_base = [g["name"] for g in grace_null_flags if g.get("region") != "dlc"]
    null_dlc = [g["name"] for g in grace_null_flags if g.get("region") == "dlc"]

    orphan_flags = gf_keys - grace_flag_values
    missing_in_gf = grace_flag_values - gf_keys

    issues.append(f"[GRACE] grace_flags.json: {len(grace_flags)} entradas")
    issues.append(f"[GRACE] graces.json: {len(graces)} entradas ({len(graces) - len(grace_null_flags)} com flag)")

    if null_base:
        issues.append(f"[GRACE] ERRO: {len(null_base)} graces base game sem flag:")
        for name in sorted(null_base):
            issues.append(f"  - {name}")

    if null_dlc:
        issues.append(f"[GRACE] AVISO: {len(null_dlc)} graces DLC sem flag (esperado ate extracdo de fontes externas)")

    if missing_in_gf:
        issues.append(f"[GRACE] AVISO: {len(missing_in_gf)} flags referenciados em graces.json ausentes de grace_flags.json:")
        for fid in sorted(missing_in_gf):
            grace_name = next((g["name"] for g in graces if g.get("flag") == fid), "?")
            issues.append(f"  - flag {fid} ({grace_name})")

    if orphan_flags:
        issues.append(f"[GRACE] INFO: {len(orphan_flags)} flags em grace_flags.json sem correspondencia em graces.json")

    name_counts = Counter(g["name"] for g in graces)
    dupes = {name: count for name, count in name_counts.items() if count > 1}
    if dupes:
        issues.append(f"[GRACE] AVISO: {len(dupes)} nomes duplicados em graces.json:")
        for name, count in sorted(dupes.items()):
            issues.append(f"  - {name} (x{count})")

    return issues


def validate_story_flags() -> list[str]:
    issues: list[str] = []

    story_flags = load_json("story_flags.json")
    issues.append(f"[STORY] story_flags.json: {len(story_flags)} entradas")

    by_type: dict[str, int] = {}
    for entry in story_flags:
        t = entry.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    for t, count in sorted(by_type.items()):
        issues.append(f"  {t}: {count}")

    flag_counts = Counter(e["flag_id"] for e in story_flags)
    dupes = {fid: count for fid, count in flag_counts.items() if count > 1}
    if dupes:
        issues.append(f"[STORY] ERRO: {len(dupes)} flag_ids duplicados:")
        for fid, count in sorted(dupes.items()):
            issues.append(f"  - flag {fid} (x{count})")

    return issues


def validate_npcs() -> list[str]:
    issues: list[str] = []

    npc_flags = load_json("npc_dead_flags.json")
    npcs = load_json("npcs.json")

    issues.append(f"[NPC] npc_dead_flags.json: {len(npc_flags)} entradas")
    issues.append(f"[NPC] npcs.json: {len(npcs)} entradas")

    trackable = [n for n in npcs if n.get("category") == "npc"]
    issues.append(f"[NPC] AVISO: Cobertura de NPC dead flags: {len(npc_flags)}/{len(trackable)} ({len(npc_flags)/max(len(trackable),1)*100:.1f}%)")

    return issues


def main() -> int:
    all_issues: list[str] = []

    all_issues.append("=" * 60)
    all_issues.append("VALIDACAO CRUZADA DE REFERENCIAS")
    all_issues.append("=" * 60)
    all_issues.append("")

    all_issues.extend(validate_bosses())
    all_issues.append("")
    all_issues.extend(validate_graces())
    all_issues.append("")
    all_issues.extend(validate_story_flags())
    all_issues.append("")
    all_issues.extend(validate_npcs())

    all_issues.append("")
    all_issues.append("=" * 60)

    has_errors = any("[ERRO]" in line or "ERRO:" in line for line in all_issues)

    for line in all_issues:
        print(line)

    if has_errors:
        print("\nValidacao concluida com ERROS.")
        return 1

    print("\nValidacao concluida sem erros criticos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# "Confiar e bom, verificar e melhor." -- Vladimir Lenin
