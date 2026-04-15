"""Baixa thumbnails de itens da wiki Fextralife.

Uso:
    python scripts/fetch_item_images.py [--category weapon] [--limit 10] [--dry-run]

Salva imagens em assets/item_images/{category}/{nome_normalizado}.webp
Idempotente: pula imagens que já existem localmente.
Respeita rate limit com delay entre requests.
"""
import argparse
import json
import re
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCES_DIR = PROJECT_ROOT / "data" / "references"
IMAGES_DIR = PROJECT_ROOT / "assets" / "item_images"

GITHUB_RAW_BASE = (
    "https://raw.githubusercontent.com/CyberGiant7/"
    "Elden-Ring-Automatic-Checklist/main/assets/img"
)
REQUEST_DELAY = 0.3
USER_AGENT = "EldenRingTracker/1.0 (item-image-fetcher)"

CATEGORY_TO_GITHUB_DIR = {
    "weapon": "armament",
    "shield": "armament",
    "armor": "armor",
    "talisman": "talisman",
    "spell": "magic",
    "spirit_ash": "spiritAshes",
    "consumable": None,
    "material": None,
    "upgrade_material": None,
}


def _sanitize_filename(name: str) -> str:
    clean = re.sub(r"[^\w\s\-'.()]", "", name)
    clean = re.sub(r"\s+", "_", clean.strip())
    return clean[:120]


def _build_github_image_url(item_name: str, category: str) -> str | None:
    github_dir = CATEGORY_TO_GITHUB_DIR.get(category)
    if not github_dir:
        return None
    encoded = urllib.parse.quote(item_name)
    return f"{GITHUB_RAW_BASE}/{github_dir}/{encoded}.webp"


def _try_download(url: str, dest: Path) -> bool:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                data = resp.read()
                if len(data) > 500:
                    dest.write_bytes(data)
                    return True
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        pass
    return False


def fetch_images(category: str | None = None, limit: int = 0, dry_run: bool = False) -> None:
    ids = json.loads((REFERENCES_DIR / "item_ids.json").read_text())

    categories_to_fetch = [category] if category else list(ids.keys())

    total_fetched = 0
    total_skipped = 0
    total_failed = 0

    for cat in categories_to_fetch:
        entries = ids.get(cat, {})
        if not entries:
            print(f"[{cat}] Nenhuma entrada encontrada")
            continue

        cat_dir = IMAGES_DIR / cat
        cat_dir.mkdir(parents=True, exist_ok=True)

        items = list(entries.values())
        if limit > 0:
            items = items[:limit]

        print(f"\n[{cat}] {len(items)} itens para processar")

        for i, name in enumerate(items):
            filename = _sanitize_filename(name) + ".webp"
            dest = cat_dir / filename

            if dest.exists():
                total_skipped += 1
                continue

            if dry_run:
                print(f"  [{i+1}/{len(items)}] {name} -> {dest.name} (dry-run)")
                continue

            url = _build_github_image_url(name, cat)
            if not url:
                total_failed += 1
                continue

            success = _try_download(url, dest)

            if success:
                total_fetched += 1
                if total_fetched % 20 == 0:
                    print(f"  [{i+1}/{len(items)}] {total_fetched} baixadas...")
            else:
                total_failed += 1

            time.sleep(REQUEST_DELAY)

    print(f"\nResultados:")
    print(f"  Baixadas: {total_fetched}")
    print(f"  Já existiam: {total_skipped}")
    print(f"  Falhas: {total_failed}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Baixa thumbnails de itens da wiki Fextralife")
    parser.add_argument("--category", type=str, default=None, help="Categoria específica (weapon, armor, etc.)")
    parser.add_argument("--limit", type=int, default=0, help="Limite de itens por categoria (0 = todos)")
    parser.add_argument("--dry-run", action="store_true", help="Apenas mostra o que seria feito")
    args = parser.parse_args()

    fetch_images(category=args.category, limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()


# "Uma imagem vale mais que mil palavras." -- Fred R. Barnard
