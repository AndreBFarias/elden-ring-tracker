import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import streamlit as st

from missable_checker import (
    STATUS_DISPONIVEL,
    STATUS_PERDIDO,
    get_missable_status,
    get_missable_summary,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_DIR = PROJECT_ROOT / "logs"

logger = logging.getLogger("elden_tracker.pages.missable")
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

STATUS_COLORS = {
    STATUS_DISPONIVEL: "#f8f8f2",
    STATUS_PERDIDO: "#ff5555",
}

STATUS_LABELS = {
    STATUS_DISPONIVEL: "Disponível",
    STATUS_PERDIDO: "Perdido",
}

SEVERITY_COLORS = {
    "critical": "#ff5555",
    "moderate": "#ffb86c",
    "minor": "#f1fa8c",
}

SEVERITY_LABELS = {
    "critical": "Crítico",
    "moderate": "Moderado",
    "minor": "Menor",
}


def _render_event_card(slot_index: int, event: dict) -> None:
    status = event["status"]
    severity = event["severity"]
    status_color = STATUS_COLORS.get(status, "#f8f8f2")
    severity_color = SEVERITY_COLORS.get(severity, "#f8f8f2")
    status_label = STATUS_LABELS.get(status, status)
    severity_label = SEVERITY_LABELS.get(severity, severity)

    st.markdown(
        f'<div style="background-color:#282a36;border:1px solid #44475a;'
        f'border-left:4px solid {severity_color};border-radius:6px;padding:0.75rem;margin-bottom:0.5rem;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<span style="font-family:monospace;font-weight:bold;color:#f8f8f2;">{event["name"]}</span>'
        f'<span style="font-family:monospace;font-size:0.75rem;color:{status_color};'
        f'text-transform:uppercase;letter-spacing:0.05em;">{status_label}</span>'
        f'</div>'
        f'<div style="font-family:monospace;font-size:0.8rem;color:#6272a4;margin-top:0.25rem;">'
        f'NPC: {event["related_npc"]} | Severidade: '
        f'<span style="color:{severity_color};">{severity_label}</span></div>'
        f'<div style="font-family:monospace;font-size:0.8rem;color:#8be9fd;margin-top:0.25rem;">'
        f'{event["description"]}</div>'
        f'<div style="font-family:monospace;font-size:0.75rem;color:#ff5555;margin-top:0.25rem;">'
        f'Perde se: {event["loss_condition"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    event_id = event["event_id"]
    if st.button("Ver no Mapa", key=f"miss_map_{event_id}", use_container_width=True):
        st.session_state["_pending_map_search"] = event["related_npc"]
        st.session_state["_pending_map_region"] = event.get("region", "surface")
        st.rerun()


def render(slot_index: int, region: str = "") -> None:
    summary = get_missable_summary(slot_index)

    st.markdown(
        '<p style="font-family:monospace;color:#bd93f9;text-transform:uppercase;'
        'letter-spacing:0.1em;font-size:0.85rem;border-bottom:1px solid #44475a;'
        'padding-bottom:0.25rem;">Eventos Perdíveis</p>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        c1.metric("Total", summary["total"])
        c2.metric("Disponíveis", summary[STATUS_DISPONIVEL])
        c3.metric("Perdidos", summary[STATUS_PERDIDO])

    st.markdown(
        '<div style="font-family:monospace;font-size:0.75rem;margin-bottom:0.5rem;">'
        '<span style="color:#ff5555;">Vermelho = Crítico</span> | '
        '<span style="color:#ffb86c;">Laranja = Moderado</span> | '
        '<span style="color:#f1fa8c;">Amarelo = Menor</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    events = get_missable_status(slot_index)
    if region:
        events = [e for e in events if e.get("region") == region]

    filter_status = st.selectbox(
        "Filtrar por status",
        options=["Todos", "Disponível", "Perdido"],
        index=0,
        key="missable_status_filter",
    )

    status_map = {"Disponível": STATUS_DISPONIVEL, "Perdido": STATUS_PERDIDO}
    if filter_status != "Todos":
        s = status_map.get(filter_status, "")
        events = [e for e in events if e["status"] == s]

    if not events:
        if region:
            st.info("Nenhum evento perdível nesta região para os filtros selecionados.")
        else:
            st.info("Nenhum evento encontrado para o filtro selecionado.")
        return

    for event in events:
        _render_event_card(slot_index, event)


# "A sorte favorece a mente preparada." -- Louis Pasteur
