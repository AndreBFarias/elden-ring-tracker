import json
import logging
import sys
import time
import urllib.error
import urllib.request
from logging.handlers import RotatingFileHandler
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from map_config import FEXTRALIFE_TILE_URL, MAP_TILES_DIR, REGIONS

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("elden_tracker.download_tiles")
logger.setLevel(logging.DEBUG)

_handler = RotatingFileHandler(
    LOG_DIR / "tracker.log",
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8",
)
_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)
logger.addHandler(_handler)

_console = logging.StreamHandler()
_console.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
logger.addHandler(_console)

REQUEST_DELAY = 0.15
REQUEST_TIMEOUT = 15
MAX_TILE_COORD = 32


def _build_tile_url(map_id: str, tileset_id: int, z: int, x: int, y: int) -> str:
    return FEXTRALIFE_TILE_URL.format(
        map_id=map_id, tileset_id=tileset_id, z=z, x=x, y=y,
    )


def _download_tile(url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EldenRingTracker/1.0"})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = resp.read()
        if len(data) < 100:
            return False
        dest.write_bytes(data)
        return True
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return False


def _discover_tile_bounds(map_id: str, tileset_id: int, z: int) -> tuple[int, int, int, int]:
    min_x, min_y = 0, 0
    max_x, max_y = 0, 0

    for coord in range(MAX_TILE_COORD):
        url = _build_tile_url(map_id, tileset_id, z, coord, 0)
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "EldenRingTracker/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                if resp.status == 200:
                    max_x = coord
                    time.sleep(0.05)
                    continue
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            pass
        if coord > max_x + 2:
            break
        time.sleep(0.05)

    for coord in range(MAX_TILE_COORD):
        url = _build_tile_url(map_id, tileset_id, z, 0, coord)
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "EldenRingTracker/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                if resp.status == 200:
                    max_y = coord
                    time.sleep(0.05)
                    continue
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            pass
        if coord > max_y + 2:
            break
        time.sleep(0.05)

    return min_x, min_y, max_x, max_y


def download_region(region_name: str) -> dict:
    region = REGIONS[region_name]
    tc = region.tile_config
    tile_dir = MAP_TILES_DIR / region_name
    metadata = {"region": region_name, "map_id": tc.map_id, "zoom_levels": {}}

    for z in range(region.min_zoom, region.max_zoom + 1):
        logger.info("Descobrindo bounds para %s zoom %d...", region_name, z)
        min_x, min_y, max_x, max_y = _discover_tile_bounds(tc.map_id, tc.tileset_id, z)
        logger.info(
            "Bounds para %s zoom %d: x=[%d, %d] y=[%d, %d]",
            region_name, z, min_x, max_x, min_y, max_y,
        )

        total = (max_x - min_x + 1) * (max_y - min_y + 1)
        downloaded = 0
        skipped = 0
        failed = 0

        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                url = _build_tile_url(tc.map_id, tc.tileset_id, z, x, y)
                dest = tile_dir / str(z) / str(x) / f"{y}.jpg"
                if dest.exists() and dest.stat().st_size > 0:
                    skipped += 1
                    continue
                if _download_tile(url, dest):
                    downloaded += 1
                else:
                    failed += 1
                time.sleep(REQUEST_DELAY)

        metadata["zoom_levels"][str(z)] = {
            "min_x": min_x, "max_x": max_x,
            "min_y": min_y, "max_y": max_y,
            "total": total, "downloaded": downloaded,
            "skipped": skipped, "failed": failed,
        }
        logger.info(
            "Zoom %d completo: %d baixados, %d existentes, %d falhos (de %d)",
            z, downloaded, skipped, failed, total,
        )

    meta_path = tile_dir / "metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    logger.info("Metadata salvo em %s", meta_path)
    return metadata


def check_tiles() -> dict[str, dict]:
    status: dict[str, dict] = {}
    for name, region in REGIONS.items():
        tile_dir = MAP_TILES_DIR / name
        tile_count = len(list(tile_dir.rglob("*.jpg"))) if tile_dir.is_dir() else 0
        meta_path = tile_dir / "metadata.json"

        if tile_count == 0:
            state = "pendente"
        elif meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            total_failed = sum(
                zl.get("failed", 0) for zl in meta.get("zoom_levels", {}).values()
            )
            total_expected = sum(
                zl.get("total", 0) for zl in meta.get("zoom_levels", {}).values()
            )
            total_ok = sum(
                zl.get("downloaded", 0) + zl.get("skipped", 0)
                for zl in meta.get("zoom_levels", {}).values()
            )
            if total_failed > 0 or total_ok < total_expected:
                state = "incompleto"
            else:
                state = "completo"
        else:
            state = "incompleto"

        status[name] = {"tiles": tile_count, "state": state}
    return status


def main() -> None:
    if "--check" in sys.argv:
        result = check_tiles()
        all_complete = True
        for name, info in result.items():
            print(f"  {name:<14} {info['tiles']:>5}  [{info['state']}]")
            if info["state"] != "completo":
                all_complete = False
        sys.exit(0 if all_complete else 1)

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    regions = args if args else list(REGIONS.keys())
    for region_name in regions:
        if region_name not in REGIONS:
            logger.error("Regiao desconhecida: %s", region_name)
            continue
        logger.info("=== Baixando tiles para %s ===", region_name)
        download_region(region_name)
    logger.info("Download concluido.")


if __name__ == "__main__":
    main()


# "O homem que move montanhas comeca carregando pequenas pedras." -- Confucio
