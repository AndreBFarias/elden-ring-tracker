import base64
import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from map_config import REGIONS, MAP_TILES_DIR
from recalibrate import OLD_COORDS

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("elden_tracker.calibration")
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
CALIBRATION_FILE = PROJECT_ROOT / "data" / "calibration_points.json"

REFERENCE_POINTS = {
    "surface": [
        {"id": "stranded_graveyard", "label": "Stranded Graveyard"},
        {"id": "first_step", "label": "The First Step"},
        {"id": "church_elleh", "label": "Church of Elleh"},
        {"id": "gatefront", "label": "Gatefront"},
        {"id": "stormveil", "label": "Stormveil Castle"},
        {"id": "godrick", "label": "Godrick the Grafted"},
        {"id": "raya_lucaria", "label": "Raya Lucaria Academy"},
        {"id": "volcano_manor", "label": "Volcano Manor"},
        {"id": "leyndell", "label": "Leyndell / Erdtree"},
        {"id": "radahn", "label": "Starscourge Radahn"},
        {"id": "castle_sol", "label": "Castle Sol"},
        {"id": "fire_giant", "label": "Fire Giant"},
        {"id": "malenia", "label": "Miquella's Haligtree"},
        {"id": "farum_azula", "label": "Crumbling Farum Azula"},
        {"id": "weeping_peninsula", "label": "Weeping Peninsula"},
    ],
    "underground": [
        {"id": "siofra_river", "label": "Siofra River Bank"},
        {"id": "ainsel_river", "label": "Ainsel River Main"},
        {"id": "nokron", "label": "Nokron, Eternal City"},
        {"id": "deeproot_depths", "label": "Deeproot Depths"},
        {"id": "mohgwyn_palace", "label": "Mohgwyn Palace"},
        {"id": "lake_of_rot", "label": "Lake of Rot"},
    ],
    "dlc": [
        {"id": "gravesite_plain", "label": "Gravesite Plain"},
        {"id": "castle_ensis", "label": "Castle Ensis"},
        {"id": "shadow_keep", "label": "Shadow Keep"},
        {"id": "abyssal_woods", "label": "Abyssal Woods"},
        {"id": "enir_ilim", "label": "Enir-Ilim"},
    ],
}


def _get_optimized_image_path(region_name: str) -> str:
    region = REGIONS[region_name]
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
        return str(cached)

    if source.stat().st_size > 10 * 1024 * 1024:
        cache_prefix = f"{region.name}_upscaled" if "upscaled" in source.name else region.name
        quality = 70 if "upscaled" in source.name else 85
        cached = CACHE_DIR / f"{cache_prefix}_opt.jpg"
        if not cached.exists():
            logger.info("Otimizando %s para JPEG (q%d)...", source.name, quality)
            img = Image.open(str(source))
            if img.mode == "RGBA":
                img = img.convert("RGB")
            img.save(str(cached), "JPEG", quality=quality, optimize=True)
        return str(cached)

    return str(source)


def _image_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        data = f.read()
    ext = Path(path).suffix.lstrip(".")
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png"}.get(ext, "png")
    return f"data:image/{mime};base64,{base64.b64encode(data).decode()}"


def _load_saved_points() -> dict:
    if CALIBRATION_FILE.exists():
        with open(str(CALIBRATION_FILE), encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_points(points: dict) -> None:
    CALIBRATION_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(str(CALIBRATION_FILE), "w", encoding="utf-8") as f:
        json.dump(points, f, indent=2, ensure_ascii=False)


_MAP_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
html, body { margin:0; padding:0; height:100%; overflow:hidden;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }
#map { width:100%; height:100%; }
.leaflet-container { background:#1a1b26 !important; }

#panel {
  position:absolute; top:10px; right:10px; width:300px;
  max-height:calc(100% - 20px); overflow-y:auto;
  background:#282a36; border:1px solid #44475a; border-radius:8px;
  padding:12px; z-index:1000; color:#f8f8f2; font-size:12px;
  box-shadow:0 4px 12px rgba(0,0,0,0.4);
}
#panel h3 { font-size:14px; margin:0 0 8px; color:#bd93f9; }
.prog-bar { width:100%; height:6px; background:#44475a;
  border-radius:3px; margin-bottom:4px; overflow:hidden; }
.prog-fill { height:100%; background:#50fa7b; border-radius:3px;
  transition:width 0.3s; }
.prog-text { font-size:11px; color:#6272a4; margin-bottom:8px; }

.pt-item { display:flex; align-items:center; padding:3px 6px;
  border-radius:4px; cursor:pointer; margin-bottom:1px; }
.pt-item:hover { background:#44475a; }
.badge { width:20px; height:20px; border-radius:50%; display:flex;
  align-items:center; justify-content:center; font-weight:bold;
  font-size:10px; margin-right:6px; flex-shrink:0; color:#282a36; }
.badge-r { background:#ff5555; }
.badge-g { background:#50fa7b; }
.pt-lbl { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.pt-crd { font-size:10px; color:#6272a4; margin-left:4px; flex-shrink:0; }

#copy-btn { width:100%; padding:8px; margin-top:8px; background:#bd93f9;
  color:#282a36; border:none; border-radius:6px; font-weight:bold;
  font-size:12px; cursor:pointer; }
#copy-btn:hover { background:#caa8ff; }

#json-out { width:100%; height:100px; margin-top:6px; background:#1a1b26;
  color:#f8f8f2; border:1px solid #44475a; border-radius:4px; padding:6px;
  font-family:monospace; font-size:10px; resize:vertical; display:none; }

.leaflet-tooltip { background:#282a36 !important; color:#f8f8f2 !important;
  border:1px solid #44475a !important; font-size:10px !important;
  padding:2px 5px !important; border-radius:3px !important;
  box-shadow:0 2px 4px rgba(0,0,0,0.3) !important; white-space:nowrap !important; }
.leaflet-tooltip-right::before { border-right-color:#44475a !important; }
.leaflet-tooltip-top::before { border-top-color:#44475a !important; }

#toast { position:fixed; bottom:20px; left:50%; transform:translateX(-50%);
  background:#50fa7b; color:#282a36; padding:8px 20px; border-radius:6px;
  font-weight:bold; font-size:13px; z-index:2000; opacity:0;
  transition:opacity 0.3s; pointer-events:none; }

#panel::-webkit-scrollbar { width:5px; }
#panel::-webkit-scrollbar-track { background:transparent; }
#panel::-webkit-scrollbar-thumb { background:#44475a; border-radius:3px; }
</style>
</head>
<body>
<div id="map"></div>
<div id="panel">
  <h3>Pontos de Referencia</h3>
  <div class="prog-bar"><div class="prog-fill" id="prog-fill"></div></div>
  <div class="prog-text" id="prog-text"></div>
  <div id="pt-list"></div>
  <button id="copy-btn" onclick="copyJSON()">Copiar JSON</button>
  <textarea id="json-out" readonly></textarea>
</div>
<div id="toast">JSON copiado!</div>

<script>
var C = __CONFIG__;
var IMG = "__IMAGE_URL__";

var map = L.map('map', {
  crs: L.CRS.Simple,
  minZoom: C.minZoom,
  maxZoom: C.maxZoom,
  maxBounds: [[0, 0], [C.h, C.w]],
  maxBoundsViscosity: 1.0,
  zoomSnap: 0.5
});

L.imageOverlay(IMG, [[0, 0], [C.h, C.w]]).addTo(map);
map.fitBounds([[0, 0], [C.h, C.w]]);

var pts = C.markers;

function mkIcon(n, ok) {
  var bg = ok ? '#50fa7b' : '#ff5555';
  var bd = ok ? '#44cf62' : '#cc4444';
  return L.divIcon({
    className: '',
    html: '<div style="background:'+bg+';border:2px solid '+bd+
      ';border-radius:50%;width:30px;height:30px;display:flex;'+
      'align-items:center;justify-content:center;font-weight:bold;'+
      'font-size:13px;color:#282a36;box-shadow:0 2px 6px rgba(0,0,0,0.5);'+
      'cursor:grab;">'+n+'</div>',
    iconSize: [30, 30],
    iconAnchor: [15, 15]
  });
}

pts.forEach(function(p) {
  p.marker = L.marker([p.lat, p.lng], {
    draggable: true,
    icon: mkIcon(p.num, p.ok),
    zIndexOffset: 1000
  }).addTo(map);

  p.marker.bindTooltip(p.num + '. ' + p.label, {
    permanent: true,
    direction: 'right',
    offset: [15, 0]
  });

  p.marker.on('dragend', function(e) {
    var pos = e.target.getLatLng();
    p.lat = pos.lat;
    p.lng = pos.lng;
    p.ok = true;
    e.target.setIcon(mkIcon(p.num, true));
    upd();
  });

  p.marker.on('dblclick', function(e) {
    p.ok = true;
    e.target.setIcon(mkIcon(p.num, true));
    upd();
    L.DomEvent.stopPropagation(e);
  });
});

function upd() {
  var ok = 0;
  pts.forEach(function(p) { if (p.ok) ok++; });
  var pct = pts.length > 0 ? (ok / pts.length * 100) : 0;
  document.getElementById('prog-fill').style.width = pct + '%';
  document.getElementById('prog-text').textContent = ok + '/' + pts.length + ' confirmados';

  var list = document.getElementById('pt-list');
  list.innerHTML = '';
  pts.forEach(function(p) {
    var d = document.createElement('div');
    d.className = 'pt-item';
    d.onclick = function() { map.setView([p.lat, p.lng], Math.max(map.getZoom(), 0)); };

    var b = document.createElement('div');
    b.className = 'badge ' + (p.ok ? 'badge-g' : 'badge-r');
    b.textContent = p.num;

    var l = document.createElement('span');
    l.className = 'pt-lbl';
    l.textContent = p.label;

    var c = document.createElement('span');
    c.className = 'pt-crd';
    c.textContent = Math.round(p.lng) + ', ' + Math.round(C.h - p.lat);

    d.appendChild(b);
    d.appendChild(l);
    d.appendChild(c);
    list.appendChild(d);
  });
}

function copyJSON() {
  var r = {};
  pts.forEach(function(p) {
    r[p.id] = {
      pos_x: Math.round(p.lng * 10) / 10,
      pos_y: Math.round((C.h - p.lat) * 10) / 10
    };
  });
  var s = JSON.stringify(r, null, 2);
  var ta = document.getElementById('json-out');
  ta.value = s;
  ta.style.display = 'block';
  ta.select();
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(s).catch(function(){});
  }
  try { document.execCommand('copy'); } catch(e) {}
  var t = document.getElementById('toast');
  t.style.opacity = '1';
  setTimeout(function() { t.style.opacity = '0'; }, 2000);
}

upd();
</script>
</body>
</html>"""


def _build_map_html(
    region_name: str,
    ref_points: list[dict],
    image_data: str,
    saved_region: dict,
) -> str:
    region = REGIONS[region_name]
    old_coords = OLD_COORDS.get(region_name, {})
    markers = []

    for i, ref in enumerate(ref_points):
        pid = ref["id"]
        if pid in saved_region:
            pos_x = saved_region[pid]["pos_x"]
            pos_y = saved_region[pid]["pos_y"]
            confirmed = True
        elif pid in old_coords:
            pos_x, pos_y = old_coords[pid]
            confirmed = False
        else:
            pos_x = region.width / 2
            pos_y = region.height / 2
            confirmed = False

        markers.append({
            "id": pid,
            "label": ref["label"],
            "num": i + 1,
            "lat": region.height - pos_y,
            "lng": pos_x,
            "ok": confirmed,
        })

    config = json.dumps({
        "h": region.height,
        "w": region.width,
        "minZoom": region.min_zoom,
        "maxZoom": region.max_zoom,
        "defaultZoom": region.default_zoom,
        "markers": markers,
    })

    return _MAP_HTML.replace("__CONFIG__", config).replace("__IMAGE_URL__", image_data)


def main() -> None:
    st.set_page_config(
        page_title="Calibracao do Mapa",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        "<style>"
        ".block-container{padding-top:1rem;max-width:100%}"
        "header[data-testid='stHeader']{display:none}"
        "</style>",
        unsafe_allow_html=True,
    )

    saved = _load_saved_points()

    with st.sidebar:
        st.markdown("### Calibracao de Coordenadas")

        region_options = {r.display_name: r.name for r in REGIONS.values()}
        selected_display = st.radio(
            "Regiao",
            options=list(region_options.keys()),
            index=0,
            label_visibility="collapsed",
        )
        region_name = region_options[selected_display]

        st.markdown("---")
        st.markdown(
            "1. Arraste as flags para as posicoes corretas\n"
            "2. Duplo-clique confirma sem mover\n"
            "3. Clique **Copiar JSON** no painel\n"
            "4. Cole abaixo e clique **Salvar**"
        )

        st.markdown("---")
        json_text = st.text_area(
            "Cole o JSON copiado aqui",
            height=120,
            key=f"json_input_{region_name}",
        )

        if st.button("Salvar", type="primary"):
            if not json_text.strip():
                st.error("Cole o JSON copiado do painel do mapa.")
            else:
                try:
                    parsed = json.loads(json_text)
                    if not isinstance(parsed, dict):
                        st.error("JSON invalido: esperado um objeto.")
                    else:
                        valid = True
                        for key, val in parsed.items():
                            if (
                                not isinstance(val, dict)
                                or "pos_x" not in val
                                or "pos_y" not in val
                            ):
                                st.error(
                                    f"Formato invalido para '{key}': "
                                    "esperado {pos_x, pos_y}."
                                )
                                valid = False
                                break
                        if valid:
                            if region_name not in saved:
                                saved[region_name] = {}
                            saved[region_name].update(parsed)
                            _save_points(saved)
                            logger.info(
                                "Calibracao salva [%s]: %d pontos",
                                region_name,
                                len(parsed),
                            )
                            st.success(
                                f"Salvo {len(parsed)} pontos "
                                f"para {selected_display}."
                            )
                except json.JSONDecodeError as exc:
                    st.error(f"JSON invalido: {exc}")

        st.markdown("---")
        st.markdown("### Status por regiao")
        for rname, rdata in REFERENCE_POINTS.items():
            region_saved = saved.get(rname, {})
            total = len(rdata)
            done = sum(1 for ref in rdata if ref["id"] in region_saved)
            display = REGIONS[rname].display_name
            if done == total:
                st.markdown(f"**{display}:** {done}/{total} (completo)")
            elif done > 0:
                st.markdown(f"**{display}:** {done}/{total}")
            else:
                st.markdown(f"**{display}:** nao calibrado")

        all_done = all(
            all(ref["id"] in saved.get(rn, {}) for ref in rd)
            for rn, rd in REFERENCE_POINTS.items()
        )
        if all_done:
            st.markdown("---")
            st.success("Todas as regioes calibradas!")
            st.markdown(
                "Execute `python src/recalibrate.py` para aplicar "
                "as coordenadas nos JSONs."
            )

    region = REGIONS[region_name]
    ref_points = REFERENCE_POINTS[region_name]
    image_path = _get_optimized_image_path(region_name)
    image_data = _image_to_base64(image_path)
    saved_region = saved.get(region_name, {})

    html = _build_map_html(region_name, ref_points, image_data, saved_region)
    components.html(html, height=750)


if __name__ == "__main__":
    main()


# "O mapa nao e o territorio." -- Alfred Korzybski
