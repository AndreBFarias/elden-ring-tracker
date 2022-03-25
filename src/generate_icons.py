import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from map_config import CATEGORIES, ICONS_DIR, CategoryConfig

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("elden_tracker.icons")
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

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    logger.warning("Nenhuma fonte TrueType encontrada, usando fonte padrao bitmap")
    return ImageFont.load_default()


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def generate_icon(config: CategoryConfig) -> Path:
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = ICONS_DIR / config.icon_filename
    w, h = config.icon_size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = _hex_to_rgb(config.color)

    if config.key == "player":
        cx, cy = w // 2, h // 2
        r = min(w, h) // 2 - 2
        diamond = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
        draw.polygon(diamond, fill=color, outline=(255, 255, 255, 255))
    else:
        margin = 2
        draw.ellipse(
            [margin, margin, w - margin - 1, h - margin - 1],
            fill=color,
            outline=(255, 255, 255, 255),
            width=2,
        )

    font_size = int(min(w, h) * 0.5)
    font = _load_font(font_size)
    bbox = draw.textbbox((0, 0), config.symbol, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (w - tw) // 2
    ty = (h - th) // 2 - bbox[1]
    draw.text((tx, ty), config.symbol, fill=(255, 255, 255, 255), font=font)

    img.save(str(output_path), "PNG")
    logger.info("Icone gerado: %s (%dx%d)", output_path.name, w, h)
    return output_path


def generate_all_icons() -> list[Path]:
    paths = []
    for config in CATEGORIES.values():
        paths.append(generate_icon(config))
    logger.info("Todos os %d icones gerados em %s", len(paths), ICONS_DIR)
    return paths


if __name__ == "__main__":
    generated = generate_all_icons()
    for p in generated:
        sys.stdout.write(f"{p}\n")


# "Quem controla os outros pode ser poderoso, mas quem controla a si mesmo e mais poderoso ainda." -- Lao Tzu
