import functools
import json
import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from database import (
    get_active_session,
    get_boss_kills,
    get_grace_discoveries,
    get_latest_stats,
    initialize_db,
    start_session,
)
from log import get_logger
from map_config import CATEGORIES, CATEGORY_GROUPS, ICONS_DIR, REFERENCES_DIR, REGIONS
from map_renderer import build_map, pixel_to_fextra
from progress_tracker import get_progress
from save_parser import find_save_file, get_save_path, parse_slot, set_save_path, sync_to_db

logger = get_logger("dashboard")

CUSTOM_CSS = """
<style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100%;
    }
    header[data-testid="stHeader"] {
        display: none;
    }
    section[data-testid="stSidebar"] {
        background-color: #282a36;
        min-width: 280px;
        border-right: 2px solid #bd93f9;
    }
    section[data-testid="stSidebar"] > div:first-child {
        background:
            linear-gradient(#282a36 30%, transparent),
            linear-gradient(transparent, #282a36 70%) bottom,
            linear-gradient(to bottom, rgba(189,147,249,0.3), transparent 40px) top,
            linear-gradient(to top, rgba(189,147,249,0.3), transparent 40px) bottom;
        background-repeat: no-repeat;
        background-size: 100% 40px, 100% 40px, 100% 40px, 100% 40px;
        background-attachment: local, local, scroll, scroll;
    }
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stCheckbox label {
        font-family: monospace;
        text-transform: uppercase;
        font-size: 0.85rem;
        letter-spacing: 0.05em;
    }
    section[data-testid="stSidebar"] h3 {
        font-family: monospace;
        text-transform: uppercase;
        color: #bd93f9;
        font-size: 0.9rem;
        letter-spacing: 0.1em;
        margin-top: 1.5rem;
    }
    .stMetric label {
        font-family: monospace;
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 0.05em;
    }
    section[data-testid="stSidebar"] .stButton > button {
        border: 2px solid #bd93f9;
        background-color: #44475a;
        color: #f8f8f2;
        font-family: monospace;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-weight: bold;
        transition: background-color 0.2s, border-color 0.2s;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #bd93f9;
        color: #282a36;
    }
    section[data-testid="stSidebar"] .stTextInput input {
        border: 2px solid #6272a4;
        background-color: #44475a;
        color: #f8f8f2;
        font-family: monospace;
    }
    section[data-testid="stSidebar"] .stTextInput input:focus {
        border-color: #bd93f9;
        box-shadow: 0 0 0 2px rgba(189, 147, 249, 0.3);
    }
    .stProgress > div > div > div {
        background-color: #bd93f9;
    }

    /* Containers com borda (Dracula) */
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #282a36;
        border: 1px solid #44475a;
        border-radius: 8px;
        padding: 1rem;
    }

    /* Metricas em cards individuais */
    div[data-testid="stMetric"] {
        background-color: #282a36;
        border: 1px solid #44475a;
        border-radius: 6px;
        padding: 0.75rem 1rem;
        text-align: center;
    }
    div[data-testid="stMetric"] label {
        color: #6272a4;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #f8f8f2;
        font-family: monospace;
    }

    /* Divisor horizontal */
    hr {
        border-color: #44475a;
        margin: 1rem 0;
    }

    /* Borda no iframe do mapa */
    iframe {
        border: 1px solid #44475a !important;
        border-radius: 8px;
    }

    /* Titulos de secao */
    .section-title {
        font-family: monospace;
        text-transform: uppercase;
        color: #bd93f9;
        font-size: 0.85rem;
        letter-spacing: 0.1em;
        margin-bottom: 0.5rem;
        padding-bottom: 0.25rem;
        border-bottom: 1px solid #44475a;
    }

    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }
    }
</style>
"""


@functools.lru_cache(maxsize=1)
def _get_reference_totals() -> dict[str, dict[str, int]]:
    totals: dict[str, dict[str, int]] = {}
    ref_files: dict[str, str] = {
        "boss": "bosses.json",
        "grace": "graces.json",
        "dungeon": "dungeons.json",
        "waygate": "waygates.json",
        "weapon": "items.json",
        "armor": "items.json",
        "shield": "items.json",
        "talisman": "items.json",
        "ash_of_war": "items.json",
        "spell": "items.json",
        "consumable": "items.json",
        "material": "items.json",
        "upgrade_material": "items.json",
        "flask_upgrade": "items.json",
        "key_item": "items.json",
        "map_fragment": "items.json",
    }

    file_cache: dict[str, list[dict]] = {}
    for cat_key, filename in ref_files.items():
        if filename not in file_cache:
            path = REFERENCES_DIR / filename
            if not path.exists():
                logger.warning("Arquivo de referencia ausente: %s", path)
                file_cache[filename] = []
                continue
            try:
                with open(str(path), encoding="utf-8") as f:
                    file_cache[filename] = json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                logger.error("Falha ao carregar referencia %s: %s", path, exc)
                file_cache[filename] = []
                continue

        data = file_cache[filename]
        if filename == "items.json":
            data = [e for e in data if e.get("category") == cat_key]

        for entry in data:
            region = entry.get("region", "global")
            if region not in totals:
                totals[region] = {}
            totals[region][cat_key] = totals[region].get(cat_key, 0) + 1

    all_cats = set(ref_files.keys())
    for region in totals:
        for cat_key in all_cats:
            totals[region].setdefault(cat_key, 0)

    global_counts: dict[str, int] = {}
    for region_totals in totals.values():
        for cat_key, count in region_totals.items():
            global_counts[cat_key] = global_counts.get(cat_key, 0) + count
    totals["_global"] = global_counts

    return totals


def _load_slot_names() -> dict[int, str]:
    if "slot_names" in st.session_state:
        return st.session_state["slot_names"]

    save_path = find_save_file()
    names: dict[int, str] = {}
    for i in range(10):
        result = parse_slot(i, save_path)
        if result and result.get("name"):
            names[i] = result["name"]
        else:
            names[i] = "Vazio"

    st.session_state["slot_names"] = names
    return names


def _format_slot(slot_names: dict[int, str], index: int) -> str:
    name = slot_names.get(index, "Vazio")
    return f"Slot {index} - {name}"


def _render_sidebar() -> tuple[int, str, str, dict[str, bool], str]:
    with st.sidebar:
        icon_path = ICONS_DIR / "icon.png"
        if icon_path.exists():
            col_logo = st.columns([1, 2, 1])
            with col_logo[1]:
                st.image(str(icon_path), width=120)

        st.markdown("### PERSONAGEM")
        slot_names = _load_slot_names()
        slot_index = st.selectbox(
            "Personagem",
            options=list(range(10)),
            format_func=lambda x: _format_slot(slot_names, x),
            label_visibility="collapsed",
        )

        st.markdown("### SINCRONIZAR")

        current_save = get_save_path()
        found_save = find_save_file()
        if current_save:
            display_path = current_save
        elif found_save:
            display_path = str(found_save)
        else:
            display_path = ""

        new_path = st.text_input(
            "Caminho do save (ER0000.sl2)",
            value=display_path,
            placeholder="Ex: ~/.steam/steam/steamapps/compatdata/1245620/...",
            help="Caminho completo para ER0000.sl2 ou pasta que o contém",
        )
        if new_path != current_save:
            expanded = str(Path(new_path).expanduser()) if new_path else ""
            set_save_path(expanded)
            st.rerun()

        syncing = st.session_state.get("_syncing", False)
        if st.button("Sincronizar Save", use_container_width=True, disabled=syncing):
            st.session_state["_syncing"] = True
            save_path = find_save_file()
            if save_path:
                with st.spinner("Sincronizando save..."):
                    try:
                        sync_to_db(slot_index, save_path)
                    except Exception as exc:
                        logger.exception("Erro ao sincronizar slot %d", slot_index)
                        st.error(f"Erro na sincronização: {exc}")
                        st.session_state["_syncing"] = False
                        return slot_index, "surface", "", {}, ""
                st.session_state.pop("slot_names", None)
                st.session_state["_syncing"] = False
                st.session_state["_sync_success"] = True
                st.rerun()
            else:
                st.warning("Save não encontrado. Verifique o caminho acima.")
                st.session_state["_syncing"] = False

        if st.session_state.pop("_sync_success", False):
            st.success("Sincronização concluída")

        st.markdown("### MAPA")
        region_options: dict[str, str] = {"Todos": ""}
        region_options.update({r.display_name: r.name for r in REGIONS.values()})

        pending_region = st.session_state.pop("_pending_map_region", None)
        if pending_region:
            display_map = {r.name: r.display_name for r in REGIONS.values()}
            display_name = display_map.get(pending_region)
            if display_name:
                st.session_state["region_radio"] = display_name

        selected_display = st.radio(
            "Região",
            options=list(region_options.keys()),
            key="region_radio",
            label_visibility="collapsed",
        )
        region_name = region_options[selected_display]
        map_region = region_name if region_name else "surface"
        filter_region = region_name

        st.markdown("### BUSCA")
        pending_search = st.session_state.pop("_pending_map_search", None)
        if pending_search:
            st.session_state["sidebar_search"] = pending_search
        search_query = st.text_input(
            "Buscar marcador",
            key="sidebar_search",
            placeholder="Nome do local, item, NPC...",
            label_visibility="collapsed",
        ).strip()

        st.markdown("### PROGRESSO")
        boss_prog = get_progress(slot_index, "boss", region=filter_region)
        grace_prog = get_progress(slot_index, "grace", region=filter_region)

        if boss_prog["total"] > 0:
            st.markdown(f"**Bosses:** {boss_prog['completed']} / {boss_prog['total']}")
            st.progress(min(boss_prog["completed"] / boss_prog["total"], 1.0))
        else:
            st.markdown(f"**Bosses:** {boss_prog['completed']}")

        if grace_prog["total"] > 0:
            st.markdown(f"**Graças:** {grace_prog['completed']} / {grace_prog['total']}")
            st.progress(min(grace_prog["completed"] / grace_prog["total"], 1.0))
        else:
            st.markdown(f"**Graças:** {grace_prog['completed']}")

        st.markdown("### PROGRESSO DO MAPA")
        progress_mode = st.session_state.get("map_progress_mode", "total")
        cp1, cp2 = st.columns(2)
        with cp1:
            atual_type = "primary" if progress_mode == "atual" else "secondary"
            if st.button("Atual", use_container_width=True, type=atual_type):
                st.session_state["map_progress_mode"] = "atual"
                st.rerun()
        with cp2:
            total_type = "primary" if progress_mode == "total" else "secondary"
            if st.button("Total", use_container_width=True, type=total_type):
                st.session_state["map_progress_mode"] = "total"
                st.rerun()

        st.markdown("### CAMADAS")

        col_sel, col_desel = st.columns(2)
        with col_sel:
            if st.button("Tudo", use_container_width=True):
                for key in CATEGORIES:
                    if CATEGORIES[key].filterable:
                        st.session_state[f"layer_{key}"] = True
                st.rerun()
        with col_desel:
            if st.button("Nenhum", use_container_width=True):
                for key in CATEGORIES:
                    if CATEGORIES[key].filterable:
                        st.session_state[f"layer_{key}"] = False
                st.rerun()

        layer_visibility: dict[str, bool] = {}

        for group_name, cat_keys in CATEGORY_GROUPS.items():
            with st.expander(group_name, expanded=(group_name == "Locais")):
                for key in cat_keys:
                    cat = CATEGORIES.get(key)
                    if not cat:
                        logger.warning("Categoria '%s' em CATEGORY_GROUPS não existe em CATEGORIES", key)
                        continue
                    if not cat.filterable:
                        continue
                    default_on = True
                    layer_visibility[key] = st.checkbox(
                        cat.display_name,
                        value=default_on,
                        key=f"layer_{key}",
                    )

        layer_visibility["player"] = st.checkbox(
            CATEGORIES["player"].display_name,
            value=True,
            key="layer_player",
        )

    return slot_index, map_region, filter_region, layer_visibility, search_query


def _render_metrics(slot_index: int, region: str = "") -> None:
    stats = get_latest_stats(slot_index)
    session = get_active_session(slot_index)
    boss_progress = get_progress(slot_index, "boss", region=region)
    grace_progress = get_progress(slot_index, "grace", region=region)

    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns(5)

        if stats:
            c1.metric("Nível", stats["level"])
            c2.metric("Runas", f"{stats['runes_held']:,}")
        else:
            c1.metric("Nível", "--")
            c2.metric("Runas", "--")

        boss_label = (
            f"{boss_progress['completed']} / {boss_progress['total']}"
            if boss_progress["total"]
            else str(boss_progress["completed"])
        )
        grace_label = (
            f"{grace_progress['completed']} / {grace_progress['total']}"
            if grace_progress["total"]
            else str(grace_progress["completed"])
        )
        c3.metric("Bosses", boss_label)
        c4.metric("Graças", grace_label)

        if session:
            from datetime import datetime, timezone
            started = datetime.fromisoformat(session["started_at"].replace("Z", "+00:00"))
            elapsed = datetime.now(timezone.utc) - started
            hours = int(elapsed.total_seconds() // 3600)
            minutes = int((elapsed.total_seconds() % 3600) // 60)
            c5.metric("Sessão", f"{hours}h{minutes:02d}m")
        else:
            c5.metric("Sessão", "Inativa")


def _render_map(
    slot_index: int,
    region_name: str,
    layer_visibility: dict[str, bool],
    search_query: str,
) -> None:
    boss_kills = get_boss_kills(slot_index)
    grace_discoveries = get_grace_discoveries(slot_index)
    defeated_flags = {row["boss_flag"] for row in boss_kills}
    discovered_flags = {row["grace_flag"] for row in grace_discoveries}

    stats = get_latest_stats(slot_index)
    player_pos = None
    if stats and stats["pos_x"] is not None and stats["pos_z"] is not None:
        if stats["pos_x"] != 0.0 or stats["pos_z"] != 0.0:
            player_pos = pixel_to_fextra(stats["pos_x"], stats["pos_z"])

    progress_mode = st.session_state.get("map_progress_mode", "total")

    html = build_map(
        region_name=region_name,
        defeated_boss_flags=defeated_flags,
        discovered_grace_flags=discovered_flags,
        player_pos=player_pos,
        layer_visibility=layer_visibility,
        search_query=search_query,
        map_height=600,
        progress_mode=progress_mode,
    )

    if search_query:
        region = REGIONS.get(region_name)
        region_label = region.display_name if region else region_name
        st.caption(f"Região: {region_label} | Busca: \"{search_query}\"")

    st.markdown('<p class="section-title">Mapa</p>', unsafe_allow_html=True)
    with st.container(border=True):
        components.html(html, height=600)



def _auto_sync_if_needed(slot_index: int) -> None:
    sync_key = f"_synced_slot_{slot_index}"
    if st.session_state.get(sync_key):
        return
    save_path = find_save_file()
    if save_path is None:
        return
    try:
        sync_to_db(slot_index, save_path)
        st.session_state[sync_key] = True
        logger.info("Auto-sync realizado para slot %d", slot_index)

        if not get_active_session(slot_index):
            stats = get_latest_stats(slot_index)
            if stats:
                session_id = start_session(
                    slot_index, stats["level"], stats["runes_held"],
                )
                st.session_state["_active_session_id"] = session_id
                logger.info("Sessão %d iniciada automaticamente", session_id)
    except Exception as exc:
        logger.exception("Falha no auto-sync do slot %d: %s", slot_index, exc)


def main() -> None:
    st.set_page_config(
        page_title="Elden Ring Tracker",
        page_icon="\u2694",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    initialize_db()

    slot_index, map_region, filter_region, layer_visibility, search_query = _render_sidebar()

    _auto_sync_if_needed(slot_index)

    stats = get_latest_stats(slot_index)
    if not stats:
        st.info(
            "Nenhum dado encontrado para este slot. "
            "Use o botão **Sincronizar Save** na sidebar para começar o tracking."
        )

    _render_metrics(slot_index, region=filter_region)

    tab_map, tab_progress, tab_missable, tab_achievements = st.tabs(
        ["Mapa", "Progresso", "Eventos Perdíveis", "Conquistas"]
    )

    with tab_map:
        with st.spinner("Carregando mapa..."):
            _render_map(slot_index, map_region, layer_visibility, search_query)

    with tab_progress:
        from tabs import progress as page_progress
        page_progress.render(slot_index, region=filter_region)

    with tab_missable:
        from tabs import missable as page_missable
        page_missable.render(slot_index, region=filter_region)

    with tab_achievements:
        from tabs import achievements as page_achievements
        page_achievements.render(slot_index)

    logger.debug("Dashboard renderizado: slot=%d, região='%s'", slot_index, map_region)


if __name__ == "__main__":
    main()


# "O homem é condenado a ser livre." -- Jean-Paul Sartre
