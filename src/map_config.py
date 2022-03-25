from dataclasses import dataclass
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
MAP_TILES_DIR = ASSETS_DIR / "map_tiles"
REFERENCES_DIR = PROJECT_ROOT / "data" / "references"


@dataclass(frozen=True)
class MapRegion:
    name: str
    display_name: str
    image_filename: str
    width: int
    height: int
    default_zoom: int
    min_zoom: int
    max_zoom: int


SURFACE = MapRegion(
    name="surface",
    display_name="Superficie",
    image_filename="base.png",
    width=6780,
    height=7049,
    default_zoom=-4,
    min_zoom=-5,
    max_zoom=3,
)

UNDERGROUND = MapRegion(
    name="underground",
    display_name="Subterraneo",
    image_filename="base-underground.webp",
    width=1080,
    height=1059,
    default_zoom=-1,
    min_zoom=-3,
    max_zoom=5,
)

DLC = MapRegion(
    name="dlc",
    display_name="DLC",
    image_filename="dlc.png",
    width=3040,
    height=3165,
    default_zoom=-3,
    min_zoom=-4,
    max_zoom=3,
)

REGIONS: dict[str, MapRegion] = {
    "surface": SURFACE,
    "underground": UNDERGROUND,
    "dlc": DLC,
}


@dataclass(frozen=True)
class CategoryConfig:
    key: str
    display_name: str
    color: str
    symbol: str
    icon_filename: str
    icon_size: tuple[int, int]


BOSS = CategoryConfig(
    key="boss",
    display_name="Bosses",
    color="#e74c3c",
    symbol="\u2620",
    icon_filename="boss.png",
    icon_size=(32, 32),
)

GRACE = CategoryConfig(
    key="grace",
    display_name="Gracas",
    color="#f1c40f",
    symbol="\u2605",
    icon_filename="grace.png",
    icon_size=(32, 32),
)

DUNGEON = CategoryConfig(
    key="dungeon",
    display_name="Dungeons",
    color="#95a5a6",
    symbol="\u26EA",
    icon_filename="dungeon.png",
    icon_size=(32, 32),
)

PLAYER = CategoryConfig(
    key="player",
    display_name="Jogador",
    color="#3498db",
    symbol="\u25C6",
    icon_filename="player.png",
    icon_size=(36, 36),
)

CATEGORIES: dict[str, CategoryConfig] = {
    "boss": BOSS,
    "grace": GRACE,
    "dungeon": DUNGEON,
    "player": PLAYER,
}


@dataclass(frozen=True)
class CoordCalibration:
    scale_x: float = 1.0
    scale_y: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0


DEFAULT_CALIBRATION = CoordCalibration()


def game_to_pixel(
    game_x: float,
    game_y: float,
    calibration: Optional[CoordCalibration] = None,
) -> tuple[float, float]:
    cal = calibration or DEFAULT_CALIBRATION
    px = game_x * cal.scale_x + cal.offset_x
    py = game_y * cal.scale_y + cal.offset_y
    return px, py


# "A felicidade e o significado da vida, todo o objetivo e finalidade da existencia humana." -- Aristoteles
