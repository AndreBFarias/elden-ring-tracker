import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from map_config import MAP_TILES_DIR, REGIONS

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("elden_tracker.stitch_tiles")
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

TILE_SIZE = 256


def stitch_zoom_level(region_name: str, zoom: int) -> Path | None:
    tile_dir = MAP_TILES_DIR / region_name / str(zoom)
    if not tile_dir.exists():
        logger.warning("Diretório de tiles não encontrado: %s", tile_dir)
        return None

    meta_path = MAP_TILES_DIR / region_name / "metadata.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        zoom_info = meta.get("zoom_levels", {}).get(str(zoom))
        if zoom_info:
            min_x = zoom_info["min_x"]
            max_x = zoom_info["max_x"]
            min_y = zoom_info["min_y"]
            max_y = zoom_info["max_y"]
        else:
            min_x, max_x, min_y, max_y = _scan_tile_bounds(tile_dir)
    else:
        min_x, max_x, min_y, max_y = _scan_tile_bounds(tile_dir)

    cols = max_x - min_x + 1
    rows = max_y - min_y + 1
    width = cols * TILE_SIZE
    height = rows * TILE_SIZE

    logger.info(
        "Stitching %s zoom %d: %dx%d tiles = %dx%d pixels",
        region_name, zoom, cols, rows, width, height,
    )

    stitched = Image.new("RGB", (width, height), (26, 27, 38))

    missing = 0
    for x in range(min_x, max_x + 1):
        for y in range(min_y, max_y + 1):
            tile_path = tile_dir / str(x) / f"{y}.jpg"
            if not tile_path.exists():
                missing += 1
                continue
            tile_img = Image.open(str(tile_path))
            px = (x - min_x) * TILE_SIZE
            py = (y - min_y) * TILE_SIZE
            stitched.paste(tile_img, (px, py))
            tile_img.close()

    if missing > 0:
        logger.warning("  %d tiles faltando", missing)

    output_path = MAP_TILES_DIR / f"{region_name}_stitched_z{zoom}.jpg"
    stitched.save(str(output_path), "JPEG", quality=90, optimize=True)
    stitched.close()

    size_mb = output_path.stat().st_size / 1024 / 1024
    logger.info("Imagem stitched salva: %s (%.1f MB)", output_path.name, size_mb)
    return output_path


def _scan_tile_bounds(tile_dir: Path) -> tuple[int, int, int, int]:
    x_dirs = sorted(int(d.name) for d in tile_dir.iterdir() if d.is_dir() and d.name.isdigit())
    if not x_dirs:
        return 0, 0, 0, 0
    min_x, max_x = x_dirs[0], x_dirs[-1]
    all_y = set()
    for x_dir in tile_dir.iterdir():
        if not x_dir.is_dir() or not x_dir.name.isdigit():
            continue
        for f in x_dir.iterdir():
            if f.suffix == ".jpg" and f.stem.isdigit():
                all_y.add(int(f.stem))
    if not all_y:
        return min_x, max_x, 0, 0
    return min_x, max_x, min(all_y), max(all_y)


def main() -> None:
    regions = sys.argv[1:] if len(sys.argv) > 1 else list(REGIONS.keys())
    for region_name in regions:
        if region_name not in REGIONS:
            logger.error("Regiao desconhecida: %s", region_name)
            continue
        region = REGIONS[region_name]
        for z in range(1, region.tile_config.max_zoom + 1):
            stitch_zoom_level(region_name, z)


if __name__ == "__main__":
    main()


# "A paciencia e amarga, mas seu fruto e doce." -- Jean-Jacques Rousseau
