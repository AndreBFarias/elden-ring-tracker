import base64
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

import folium
from PIL import Image

from map_config import (
    CATEGORIES,
    ICONS_DIR,
    MAP_TILES_DIR,
    REFERENCES_DIR,
    REGIONS,
    CategoryConfig,
    MapRegion,
    game_to_pixel,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("elden_tracker.map_renderer")
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

CACHE_DIR = PROJECT_ROOT / "assets" / "cache"


def _get_optimized_image_path(region: MapRegion) -> str:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    for ext in (".png", ".jpg"):
        upscaled = MAP_TILES_DIR / f"{region.name}_upscaled{ext}"
        if upscaled.exists():
            source = upscaled
            logger.info("Usando imagem upscaled: %s", upscaled.name)
            break
    else:
        source = MAP_TILES_DIR / region.image_filename

    if not source.exists():
        logger.error("Imagem do mapa nao encontrada: %s", source)
        return str(source)

    if source.suffix == ".webp":
        cached = CACHE_DIR / f"{region.name}.png"
        if not cached.exists():
            logger.info("Convertendo %s para PNG...", source.name)
            img = Image.open(str(source))
            img.save(str(cached), "PNG", optimize=True)
            logger.info("Conversao concluida: %s", cached.name)
        return str(cached)

    if source.stat().st_size > 10 * 1024 * 1024:
        cache_prefix = f"{region.name}_upscaled" if "upscaled" in source.name else region.name
        cached = CACHE_DIR / f"{cache_prefix}_opt.jpg"
        if not cached.exists():
            logger.info("Otimizando %s para JPEG...", source.name)
            img = Image.open(str(source))
            if img.mode == "RGBA":
                img = img.convert("RGB")
            img.save(str(cached), "JPEG", quality=85, optimize=True)
            logger.info("Otimizacao concluida: %s (%.1f MB)", cached.name, cached.stat().st_size / 1024 / 1024)
        return str(cached)

    return str(source)


def _image_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        data = f.read()
    ext = Path(path).suffix.lstrip(".")
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png"}.get(ext, "png")
    return f"data:image/{mime};base64,{base64.b64encode(data).decode()}"


def _load_reference(filename: str) -> list[dict]:
    path = REFERENCES_DIR / filename
    if not path.exists():
        logger.warning("Arquivo de referencia nao encontrado: %s", path)
        return []
    with open(str(path), encoding="utf-8") as f:
        data = json.load(f)
    logger.debug("Referencia carregada: %s (%d entradas)", filename, len(data))
    return data


def _make_icon(category_key: str) -> Optional[folium.CustomIcon]:
    config = CATEGORIES.get(category_key)
    if not config:
        return None
    icon_path = ICONS_DIR / config.icon_filename
    if not icon_path.exists():
        logger.warning("Icone nao encontrado: %s, usando marcador padrao", icon_path)
        return None
    return folium.CustomIcon(
        str(icon_path),
        icon_size=config.icon_size,
        icon_anchor=(config.icon_size[0] // 2, config.icon_size[1] // 2),
    )


def _add_boss_layer(
    m: folium.Map,
    region: MapRegion,
    defeated_flags: set[int],
    visible: bool,
) -> None:
    bosses = _load_reference("bosses.json")
    fg = folium.FeatureGroup(name="Bosses", show=visible)
    count = 0
    for boss in bosses:
        if boss.get("region") != region.name:
            continue
        px, py = game_to_pixel(boss["pos_x"], boss["pos_y"])
        if px < 0 or py < 0 or px > region.width or py > region.height:
            logger.warning("Boss '%s' fora dos limites do mapa: (%.0f, %.0f)", boss["name"], px, py)
            continue
        defeated = boss.get("flag", 0) in defeated_flags
        status = "Derrotado" if defeated else "Vivo"
        opacity = 0.5 if defeated else 1.0
        popup_html = f"<b>{boss['name']}</b><br>Status: {status}"
        if boss.get("is_main"):
            popup_html += "<br><i>Boss principal</i>"
        icon = _make_icon("boss")
        folium.Marker(
            location=[region.height - py, px],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=boss["name"],
            icon=icon,
            opacity=opacity,
        ).add_to(fg)
        count += 1
    fg.add_to(m)
    logger.debug("Camada de bosses: %d marcadores para regiao '%s'", count, region.name)


def _add_grace_layer(
    m: folium.Map,
    region: MapRegion,
    discovered_flags: set[int],
    visible: bool,
) -> None:
    graces = _load_reference("graces.json")
    fg = folium.FeatureGroup(name="Gracas", show=visible)
    count = 0
    for grace in graces:
        if grace.get("region") != region.name:
            continue
        px, py = game_to_pixel(grace["pos_x"], grace["pos_y"])
        if px < 0 or py < 0 or px > region.width or py > region.height:
            logger.warning("Graca '%s' fora dos limites do mapa: (%.0f, %.0f)", grace["name"], px, py)
            continue
        discovered = grace.get("flag", 0) in discovered_flags
        status = "Descoberta" if discovered else "Oculta"
        opacity = 1.0 if discovered else 0.5
        popup_html = f"<b>{grace['name']}</b><br>Status: {status}"
        icon = _make_icon("grace")
        folium.Marker(
            location=[region.height - py, px],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=grace["name"],
            icon=icon,
            opacity=opacity,
        ).add_to(fg)
        count += 1
    fg.add_to(m)
    logger.debug("Camada de gracas: %d marcadores para regiao '%s'", count, region.name)


def _add_dungeon_layer(
    m: folium.Map,
    region: MapRegion,
    visible: bool,
) -> None:
    dungeons = _load_reference("dungeons.json")
    fg = folium.FeatureGroup(name="Dungeons", show=visible)
    count = 0
    for dungeon in dungeons:
        if dungeon.get("region") != region.name:
            continue
        px, py = game_to_pixel(dungeon["pos_x"], dungeon["pos_y"])
        if px < 0 or py < 0 or px > region.width or py > region.height:
            logger.warning("Dungeon '%s' fora dos limites do mapa: (%.0f, %.0f)", dungeon["name"], px, py)
            continue
        dtype = dungeon.get("type", "unknown").replace("_", " ").title()
        popup_html = f"<b>{dungeon['name']}</b><br>Tipo: {dtype}"
        icon = _make_icon("dungeon")
        folium.Marker(
            location=[region.height - py, px],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=dungeon["name"],
            icon=icon,
        ).add_to(fg)
        count += 1
    fg.add_to(m)
    logger.debug("Camada de dungeons: %d marcadores para regiao '%s'", count, region.name)


def _add_player_marker(
    m: folium.Map,
    region: MapRegion,
    pos_x: Optional[float],
    pos_y: Optional[float],
    visible: bool,
) -> None:
    if pos_x is None or pos_y is None:
        return
    fg = folium.FeatureGroup(name="Jogador", show=visible)
    px, py = game_to_pixel(pos_x, pos_y)
    icon = _make_icon("player")
    folium.Marker(
        location=[region.height - py, px],
        popup=folium.Popup("<b>Posicao atual</b>", max_width=200),
        tooltip="Jogador",
        icon=icon,
    ).add_to(fg)
    fg.add_to(m)


def build_map(
    region_name: str,
    defeated_boss_flags: Optional[set[int]] = None,
    discovered_grace_flags: Optional[set[int]] = None,
    player_pos: Optional[tuple[float, float]] = None,
    layer_visibility: Optional[dict[str, bool]] = None,
) -> folium.Map:
    region = REGIONS.get(region_name, REGIONS["surface"])
    defeated = defeated_boss_flags or set()
    discovered = discovered_grace_flags or set()
    visibility = layer_visibility or {
        "boss": True,
        "grace": True,
        "dungeon": True,
        "player": True,
    }

    center_y = region.height / 2
    center_x = region.width / 2

    m = folium.Map(
        location=[center_y, center_x],
        zoom_start=region.default_zoom,
        crs="Simple",
        tiles=None,
        attr="Elden Ring Tracker",
        minZoom=region.min_zoom,
        maxZoom=region.max_zoom,
        maxBounds=[[0, 0], [region.height, region.width]],
        maxBoundsViscosity=1.0,
    )

    from jinja2 import Template
    dark_style = folium.MacroElement()
    dark_style._template = Template(
        "{% macro script(this, kwargs) %}"
        "var style = document.createElement('style');"
        "style.textContent = '"
        ".leaflet-container{background:#1a1b26 !important;}"
        ".leaflet-control-zoom a{background:#44475a !important;color:#f8f8f2 !important;border-color:#6272a4 !important;}"
        ".leaflet-control-attribution{background:rgba(40,42,54,0.8) !important;color:#6272a4 !important;}"
        ".leaflet-control-attribution a{color:#bd93f9 !important;}"
        "';"
        "document.head.appendChild(style);"
        "{% endmacro %}"
    )
    m.add_child(dark_style)

    image_path = _get_optimized_image_path(region)
    image_data = _image_to_base64(image_path)

    folium.raster_layers.ImageOverlay(
        image=image_data,
        bounds=[[0, 0], [region.height, region.width]],
        opacity=1.0,
        interactive=False,
        zindex=0,
        control=False,
    ).add_to(m)

    m.fit_bounds([[0, 0], [region.height, region.width]])

    _add_boss_layer(m, region, defeated, visibility.get("boss", True))
    _add_grace_layer(m, region, discovered, visibility.get("grace", True))
    _add_dungeon_layer(m, region, visibility.get("dungeon", True))

    player_x = player_pos[0] if player_pos else None
    player_y = player_pos[1] if player_pos else None
    _add_player_marker(m, region, player_x, player_y, visibility.get("player", True))

    logger.info("Mapa construido: regiao='%s', bosses=%d, gracas=%d", region.name, len(defeated), len(discovered))
    return m


# "A unica maneira de lidar com um mundo sem liberdade e tornar-se tao absolutamente livre que sua propria existencia seja um ato de rebeliao." -- Albert Camus
