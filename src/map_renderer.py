import functools
import html as html_escape
import http.server
import json
import logging
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from string import Template
from typing import Optional

from map_config import (
    ASSETS_DIR,
    CATEGORIES,
    FEXTRALIFE_TILE_URL,
    ITEM_CATEGORIES,
    MAP_TILES_DIR,
    REFERENCES_DIR,
    REGIONS,
    CategoryConfig,
    MapRegion,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("elden_tracker.map_renderer")
if not logger.handlers:
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


class _SilentHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ASSETS_DIR), **kwargs)

    def log_message(self, format, *args):
        pass


_tile_server: Optional[http.server.HTTPServer] = None
_tile_server_port: Optional[int] = None
_tile_server_lock = threading.Lock()


def _ensure_tile_server() -> int:
    global _tile_server, _tile_server_port
    with _tile_server_lock:
        if _tile_server_port is not None:
            return _tile_server_port
        _tile_server = http.server.HTTPServer(("127.0.0.1", 0), _SilentHandler)
        _tile_server_port = _tile_server.server_address[1]
        thread = threading.Thread(target=_tile_server.serve_forever, daemon=True)
        thread.start()
        logger.info("Tile server iniciado na porta %d", _tile_server_port)
        return _tile_server_port


@functools.lru_cache(maxsize=8)
def _detect_max_native_zoom(region_name: str, configured_max: int) -> int:
    tile_dir = MAP_TILES_DIR / region_name
    if not tile_dir.is_dir():
        return configured_max

    zoom_counts: dict[int, int] = {}
    for child in tile_dir.iterdir():
        if child.is_dir() and child.name.isdigit():
            count = sum(1 for _ in child.rglob("*.jpg"))
            if count > 0:
                zoom_counts[int(child.name)] = count

    if not zoom_counts:
        return configured_max

    sorted_zooms = sorted(zoom_counts.keys())
    max_native = sorted_zooms[0]

    for i in range(1, len(sorted_zooms)):
        curr_count = zoom_counts[sorted_zooms[i]]
        prev_count = zoom_counts[sorted_zooms[i - 1]]
        if curr_count >= prev_count * 2:
            max_native = sorted_zooms[i]
        else:
            break

    logger.debug(
        "maxNativeZoom detectado para '%s': %d (contagens: %s)",
        region_name, max_native, zoom_counts,
    )
    return max_native


def _get_tile_url(region: MapRegion) -> str:
    tile_dir = MAP_TILES_DIR / region.name
    has_local = tile_dir.is_dir() and any(tile_dir.rglob("*.jpg"))

    if has_local:
        port = _ensure_tile_server()
        return f"http://127.0.0.1:{port}/map_tiles/{region.name}/{{z}}/{{x}}/{{y}}.jpg"

    tc = region.tile_config
    return FEXTRALIFE_TILE_URL.format(
        map_id=tc.map_id, tileset_id=tc.tileset_id,
        z="{z}", x="{x}", y="{y}",
    )


def _load_reference(filename: str) -> list[dict]:
    path = REFERENCES_DIR / filename
    if not path.exists():
        logger.warning("Arquivo de referência não encontrado: %s", path)
        return []
    try:
        with open(str(path), encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Falha ao carregar referência %s: %s", path, exc)
        return []
    logger.debug("Referência carregada: %s (%d entradas)", filename, len(data))
    return data


def pixel_to_fextra(pos_x: float, pos_y: float) -> tuple[float, float]:
    lat = -(pos_y / 3165.0) * 235.0
    lng = (pos_x / 3040.0) * 280.0
    return lat, lng


def _load_entries_for_region(region_name: str) -> list[dict]:
    file_cache: dict[str, list[dict]] = {}
    inferred_files: set[str] = set()
    entries: list[dict] = []

    for cat_key, cat_config in CATEGORIES.items():
        if not cat_config.reference_file:
            continue

        if cat_config.reference_file not in file_cache:
            file_cache[cat_config.reference_file] = _load_reference(cat_config.reference_file)

        for raw in file_cache[cat_config.reference_file]:
            entry_cat = raw.get("category", "")
            if not entry_cat:
                if cat_config.reference_file in inferred_files:
                    continue
                entry = {**raw, "category": cat_key}
            elif entry_cat == cat_key:
                entry = raw
            else:
                continue

            if entry.get("region") != region_name:
                continue
            entries.append(entry)

        if not all(r.get("category") for r in file_cache[cat_config.reference_file]):
            inferred_files.add(cat_config.reference_file)

    return entries


def _build_marker(
    entry: dict,
    defeated_flags: set[int],
    discovered_flags: set[int],
) -> Optional[dict]:
    category = entry.get("category", "")
    cat_config = CATEGORIES.get(category)
    if not cat_config:
        return None

    lat = entry.get("lat")
    lng = entry.get("lng")
    if lat is None or lng is None:
        pos_x = entry.get("pos_x")
        pos_y = entry.get("pos_y")
        if pos_x is not None and pos_y is not None:
            lat, lng = pixel_to_fextra(pos_x, pos_y)
        else:
            return None

    name = entry.get("name", "???")
    safe_name = html_escape.escape(name)
    opacity = 1.0
    status_line = ""

    if category == "boss":
        flag = entry.get("flag")
        if flag is not None and flag in defeated_flags:
            status = '<span style="color:#50fa7b">Derrotado</span>'
            opacity = 0.5
        else:
            status = '<span style="color:#ff5555">Vivo</span>'
            opacity = 1.0
        status_line = f"<br>Status: {status}"
        if entry.get("is_main"):
            status_line += "<br><i>Boss principal</i>"

    elif category == "grace":
        flag = entry.get("flag")
        if flag is not None and flag in discovered_flags:
            status = '<span style="color:#50fa7b">Descoberta</span>'
            opacity = 1.0
        else:
            status = '<span style="color:#6272a4">Não descoberta</span>'
            opacity = 0.5
        status_line = f"<br>Status: {status}"

    elif category == "dungeon":
        dtype = html_escape.escape(entry.get("type", "").replace("_", " ").title())
        if dtype:
            status_line = f"<br>Tipo: {dtype}"

    popup = f"<b>{safe_name}</b><br>{cat_config.display_name}{status_line}"

    return {
        "lat": lat,
        "lng": lng,
        "name": name,
        "popup": popup,
        "color": cat_config.color,
        "symbol": cat_config.symbol,
        "size": cat_config.icon_size[0],
        "opacity": opacity,
    }


def _build_player_marker(pos_lat: float, pos_lng: float) -> dict:
    cat = CATEGORIES["player"]
    return {
        "lat": pos_lat,
        "lng": pos_lng,
        "name": "Jogador",
        "popup": "<b>Posição atual</b>",
        "color": cat.color,
        "symbol": cat.symbol,
        "size": cat.icon_size[0],
        "opacity": 1.0,
    }


MAP_HTML = Template("""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
      integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
      crossorigin=""/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
        integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
        crossorigin=""></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
#map{width:100%;height:${height}px;background:#1a1b26}
.leaflet-container{background:#1a1b26!important}
.leaflet-control-zoom a{
    background:#44475a!important;color:#f8f8f2!important;
    border-color:#6272a4!important;
}
.leaflet-control-attribution{
    background:rgba(40,42,54,0.8)!important;color:#6272a4!important;
}
.leaflet-control-attribution a{color:#bd93f9!important}
.leaflet-popup-content-wrapper{
    background:#282a36!important;color:#f8f8f2!important;
    border:1px solid #44475a;border-radius:6px;
    font-family:monospace;font-size:13px;
}
.leaflet-popup-tip{background:#282a36!important}
.leaflet-tooltip{
    background:#44475a!important;color:#f8f8f2!important;
    border:1px solid #6272a4!important;border-radius:4px;
    font-family:monospace;font-size:12px;
}
.leaflet-tooltip-top:before{border-top-color:#6272a4!important}
.leaflet-tooltip-bottom:before{border-bottom-color:#6272a4!important}
.marker-icon{
    border-radius:50%;
    border:2px solid rgba(255,255,255,0.8);
    display:flex;align-items:center;justify-content:center;
    color:#fff;text-shadow:1px 1px 2px rgba(0,0,0,0.5);
    box-shadow:0 2px 4px rgba(0,0,0,0.4);
    transition:transform 0.15s;
}
.marker-icon:hover{transform:scale(1.2)}
.map-legend{
    background:rgba(40,42,54,0.9)!important;
    border:1px solid #44475a;border-radius:6px;
    padding:8px 12px;color:#f8f8f2;
    font-family:monospace;font-size:11px;
    line-height:1.8;
}
.map-legend i{
    display:inline-block;width:12px;height:12px;
    border-radius:50%;margin-right:6px;vertical-align:middle;
}
</style>
</head>
<body>
<div id="map"></div>
<script>
(function(){
    var map=L.map('map',{
        crs:L.CRS.Simple,
        minZoom:$min_zoom,
        maxZoom:$max_zoom,
        zoomControl:true,
        attributionControl:true,
        maxBoundsViscosity:1.0
    });

    L.tileLayer('$tile_url',{
        minZoom:$min_zoom,
        maxZoom:$max_zoom,
        maxNativeZoom:$max_native_zoom,
        noWrap:true,
        errorTileUrl:'',
        attribution:'Elden Ring Tracker'
    }).addTo(map);

    var data=$markers_json;
    var pts=[];

    data.forEach(function(m){
        var sz=m.size;
        var icon=L.divIcon({
            className:'',
            html:'<div class="marker-icon" style="'+
                'background:'+m.color+';'+
                'width:'+sz+'px;height:'+sz+'px;'+
                'font-size:'+Math.floor(sz*0.5)+'px;'+
                'opacity:'+m.opacity+';'+
                '">'+m.symbol+'</div>',
            iconSize:[sz,sz],
            iconAnchor:[sz/2,sz/2],
            popupAnchor:[0,-sz/2]
        });
        L.marker([m.lat,m.lng],{icon:icon})
            .bindPopup(m.popup,{maxWidth:250})
            .bindTooltip(m.name,{direction:'top',offset:[0,-sz/2]})
            .addTo(map);
        pts.push([m.lat,m.lng]);
    });

    if(pts.length>0){
        map.fitBounds(pts,{padding:[50,50],maxZoom:$default_zoom});
    }else{
        map.setView([$center_lat,$center_lng],$default_zoom);
    }

    var sw,ne;
    if(pts.length>0){
        var b=L.latLngBounds(pts);
        var padV=Math.max((b.getNorth()-b.getSouth())*0.3,80);
        var padH=Math.max((b.getEast()-b.getWest())*0.3,80);
        sw=[b.getSouth()-padV,b.getWest()-padH];
        ne=[b.getNorth()+padV,b.getEast()+padH];
    }else{
        sw=[$center_lat-200,$center_lng-200];
        ne=[$center_lat+200,$center_lng+200];
    }
    map.setMaxBounds([sw,ne]);

    var legend=L.control({position:'bottomright'});
    legend.onAdd=function(){
        var div=L.DomUtil.create('div','map-legend');
        var cats=$legend_json;
        for(var i=0;i<cats.length;i++){
            div.innerHTML+='<i style="background:'+cats[i].color+'"></i>'+cats[i].name+'<br>';
        }
        return div;
    };
    legend.addTo(map);
})();
</script>
</body>
</html>""")

DEFAULT_CENTERS = {
    "surface": (-150.0, 150.0),
    "underground": (-150.0, 150.0),
    "dlc": (-100.0, 100.0),
    "extra": (-100.0, 100.0),
}


def build_map(
    region_name: str,
    defeated_boss_flags: Optional[set[int]] = None,
    discovered_grace_flags: Optional[set[int]] = None,
    player_pos: Optional[tuple[float, float]] = None,
    layer_visibility: Optional[dict[str, bool]] = None,
    search_query: str = "",
    map_height: int = 700,
    progress_mode: str = "total",
) -> str:
    region = REGIONS.get(region_name, REGIONS["surface"])
    defeated = defeated_boss_flags or set()
    discovered = discovered_grace_flags or set()
    visibility = layer_visibility or {}

    tile_url = _get_tile_url(region)
    entries = _load_entries_for_region(region_name)

    markers: list[dict] = []
    for entry in entries:
        category = entry.get("category", "")
        if not visibility.get(category, True):
            continue
        if search_query and search_query.lower() not in entry.get("name", "").lower():
            continue
        if progress_mode == "atual":
            if category == "boss":
                flag = entry.get("flag")
                if flag is None or flag not in defeated:
                    continue
            elif category == "grace":
                flag = entry.get("flag")
                if flag is None or flag not in discovered:
                    continue
        marker = _build_marker(entry, defeated, discovered)
        if marker:
            markers.append(marker)

    if player_pos and visibility.get("player", True):
        markers.append(_build_player_marker(player_pos[0], player_pos[1]))

    active_cats: dict[str, str] = {}
    for m_entry in entries:
        cat_key = m_entry.get("category", "")
        if cat_key and visibility.get(cat_key, True) and cat_key not in active_cats:
            cat_cfg = CATEGORIES.get(cat_key)
            if cat_cfg:
                active_cats[cat_key] = cat_cfg.color
    legend_items = [
        {"name": CATEGORIES[k].display_name, "color": c}
        for k, c in active_cats.items()
    ]
    if visibility.get("player", True):
        legend_items.append({"name": "Jogador", "color": CATEGORIES["player"].color})

    center = DEFAULT_CENTERS.get(region_name, (-150.0, 150.0))
    markers_json = json.dumps(markers, ensure_ascii=True).replace("</", "<\\/")
    legend_json = json.dumps(legend_items, ensure_ascii=True)

    result = MAP_HTML.safe_substitute(
        height=map_height,
        min_zoom=region.min_zoom,
        max_zoom=region.max_zoom,
        max_native_zoom=_detect_max_native_zoom(region.name, region.max_zoom),
        default_zoom=region.default_zoom,
        tile_url=tile_url,
        markers_json=markers_json,
        center_lat=center[0],
        center_lng=center[1],
        legend_json=legend_json,
    )

    logger.info(
        "Mapa construído: região='%s', marcadores=%d",
        region.name, len(markers),
    )
    return result


# "A única maneira de lidar com um mundo sem liberdade é tornar-se tão absolutamente livre que sua própria existência seja um ato de rebelião." -- Albert Camus
