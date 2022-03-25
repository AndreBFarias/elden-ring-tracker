import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from database import (
    get_active_session,
    get_boss_kills,
    get_grace_discoveries,
    get_latest_stats,
    get_stats_history,
    initialize_db,
)
from map_config import CATEGORIES, REGIONS
from map_renderer import build_map

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("elden_tracker.dashboard")
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
    iframe {
        border: 1px solid #44475a;
        border-radius: 4px;
    }
</style>
"""

TOTAL_BOSSES_REF = 15
TOTAL_GRACES_REF = 20


def _render_sidebar() -> tuple[int, str, dict[str, bool]]:
    with st.sidebar:
        st.markdown("### SLOT")
        slot_index = st.selectbox(
            "Personagem",
            options=list(range(10)),
            format_func=lambda x: f"Slot {x}",
            label_visibility="collapsed",
        )

        st.markdown("### MAPA")
        region_options = {r.display_name: r.name for r in REGIONS.values()}
        selected_display = st.radio(
            "Regiao",
            options=list(region_options.keys()),
            index=0,
            label_visibility="collapsed",
        )
        region_name = region_options[selected_display]

        st.markdown("### CAMADAS")
        layer_visibility = {}
        for cat in CATEGORIES.values():
            layer_visibility[cat.key] = st.checkbox(
                cat.display_name,
                value=True,
                key=f"layer_{cat.key}",
            )

        st.markdown("### PROGRESSO")
        boss_kills = get_boss_kills(slot_index)
        grace_discoveries = get_grace_discoveries(slot_index)
        boss_count = len(boss_kills)
        grace_count = len(grace_discoveries)

        col1, col2 = st.columns(2)
        col1.metric("Bosses", f"{boss_count}/{TOTAL_BOSSES_REF}")
        col2.metric("Gracas", f"{grace_count}/{TOTAL_GRACES_REF}")

        if TOTAL_BOSSES_REF > 0:
            st.progress(min(boss_count / TOTAL_BOSSES_REF, 1.0), text="Bosses")
        if TOTAL_GRACES_REF > 0:
            st.progress(min(grace_count / TOTAL_GRACES_REF, 1.0), text="Gracas")

    return slot_index, region_name, layer_visibility


def _render_metrics(slot_index: int) -> None:
    stats = get_latest_stats(slot_index)
    session = get_active_session(slot_index)
    boss_kills = get_boss_kills(slot_index)
    grace_discoveries = get_grace_discoveries(slot_index)

    c1, c2, c3, c4, c5 = st.columns(5)

    if stats:
        c1.metric("Nivel", stats["level"])
        c2.metric("Runas", f"{stats['runes_held']:,}")
    else:
        c1.metric("Nivel", "--")
        c2.metric("Runas", "--")

    c3.metric("Bosses", len(boss_kills))
    c4.metric("Gracas", len(grace_discoveries))

    if session:
        c5.metric("Sessao", "Ativa")
    else:
        c5.metric("Sessao", "Inativa")


def _render_map(
    slot_index: int,
    region_name: str,
    layer_visibility: dict[str, bool],
) -> None:
    boss_kills = get_boss_kills(slot_index)
    grace_discoveries = get_grace_discoveries(slot_index)
    defeated_flags = {row["boss_flag"] for row in boss_kills}
    discovered_flags = {row["grace_flag"] for row in grace_discoveries}

    stats = get_latest_stats(slot_index)
    player_pos = None
    if stats and stats["pos_x"] is not None and stats["pos_y"] is not None:
        player_pos = (stats["pos_x"], stats["pos_y"])

    m = build_map(
        region_name=region_name,
        defeated_boss_flags=defeated_flags,
        discovered_grace_flags=discovered_flags,
        player_pos=player_pos,
        layer_visibility=layer_visibility,
    )

    st_folium(
        m,
        width=None,
        height=700,
        key=f"map_{region_name}",
        returned_objects=[],
    )


def _render_charts(slot_index: int) -> None:
    history = get_stats_history(slot_index, limit=200)

    if not history:
        st.info("Sem dados historicos para exibir graficos. Os graficos aparecem conforme dados sao coletados.")
        return

    rows = [dict(row) for row in reversed(history)]
    df = pd.DataFrame(rows)
    df["recorded_at"] = pd.to_datetime(df["recorded_at"])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Nivel ao longo do tempo")
        st.line_chart(df, x="recorded_at", y="level")
    with col2:
        st.markdown("#### Runas ao longo do tempo")
        st.line_chart(df, x="recorded_at", y="runes_held")


def main() -> None:
    st.set_page_config(
        page_title="Elden Ring Tracker",
        page_icon="\u2694",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    initialize_db()

    slot_index, region_name, layer_visibility = _render_sidebar()

    _render_metrics(slot_index)

    _render_map(slot_index, region_name, layer_visibility)

    _render_charts(slot_index)

    logger.debug("Dashboard renderizado: slot=%d, regiao='%s'", slot_index, region_name)


if __name__ == "__main__":
    main()


# "O homem e condenado a ser livre." -- Jean-Paul Sartre
