import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import streamlit as st

from achievement_resolver import get_achievement_summary, get_all_achievements

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_DIR = PROJECT_ROOT / "logs"

logger = logging.getLogger("elden_tracker.pages.achievements")
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
    "concluido": "#50fa7b",
    "em_progresso": "#f1fa8c",
    "pendente": "#6272a4",
}

TYPE_LABELS = {
    "ending": "Final",
    "boss": "Boss",
    "collection": "Coleção",
    "progression": "Progressão",
    "misc": "Misc",
}


def _render_achievement_card(slot_index: int, ach: dict) -> None:
    status = ach["status"]
    color = STATUS_COLORS.get(status, "#6272a4")
    type_label = TYPE_LABELS.get(ach["type"], ach["type"])
    pct = ach["progress_pct"]

    border_color = color if status == "concluido" else "#44475a"

    st.markdown(
        f'<div style="background-color:#282a36;border:1px solid {border_color};'
        f'border-radius:6px;padding:0.75rem;margin-bottom:0.5rem;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<span style="font-family:monospace;font-weight:bold;color:#f8f8f2;">'
        f'{ach["name_pt"]}</span>'
        f'<span style="font-family:monospace;font-size:0.7rem;color:{color};'
        f'background-color:#44475a;padding:2px 8px;border-radius:4px;">'
        f'{type_label}</span>'
        f'</div>'
        f'<div style="font-family:monospace;font-size:0.8rem;color:#8be9fd;margin-top:0.25rem;">'
        f'{ach["description"]}</div>'
        f'<div style="background-color:#44475a;border-radius:4px;height:8px;margin-top:0.5rem;">'
        f'<div style="background-color:{color};height:100%;border-radius:4px;'
        f'width:{min(pct, 100):.0f}%;transition:width 0.3s;"></div>'
        f'</div>'
        f'<div style="font-family:monospace;font-size:0.7rem;color:#6272a4;margin-top:0.25rem;">'
        f'{pct:.0f}% concluído</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if ach["missing_items"]:
        with st.expander("Itens faltando", expanded=False):
            for item in ach["missing_items"]:
                st.markdown(
                    f'<span style="font-family:monospace;font-size:0.8rem;color:#ff5555;">'
                    f'- {item}</span>',
                    unsafe_allow_html=True,
                )


def render(slot_index: int) -> None:
    summary = get_achievement_summary(slot_index)

    st.markdown(
        '<p style="font-family:monospace;color:#bd93f9;text-transform:uppercase;'
        'letter-spacing:0.1em;font-size:0.85rem;border-bottom:1px solid #44475a;'
        'padding-bottom:0.25rem;">Conquistas Steam</p>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total", summary["total"])
        c2.metric("Concluídas", summary["concluido"])
        c3.metric("Em Progresso", summary["em_progresso"])
        c4.metric("Pendentes", summary["pendente"])
        st.progress(min(summary["percentage"] / 100, 1.0))

    achievements = get_all_achievements(slot_index)

    filter_type = st.selectbox(
        "Filtrar por tipo",
        options=["Todos", "Boss", "Final", "Coleção", "Progressão"],
        index=0,
        key="ach_type_filter",
    )

    type_map = {
        "Boss": "boss",
        "Final": "ending",
        "Coleção": "collection",
        "Progressão": "progression",
    }
    if filter_type != "Todos":
        t = type_map.get(filter_type, "")
        achievements = [a for a in achievements if a["type"] == t]

    filter_status = st.selectbox(
        "Filtrar por status",
        options=["Todos", "Concluído", "Em Progresso", "Pendente"],
        index=0,
        key="ach_status_filter",
    )

    status_map = {
        "Concluído": "concluido",
        "Em Progresso": "em_progresso",
        "Pendente": "pendente",
    }
    if filter_status != "Todos":
        s = status_map.get(filter_status, "")
        achievements = [a for a in achievements if a["status"] == s]

    if not achievements:
        if filter_type != "Todos" or filter_status != "Todos":
            st.info("Nenhuma conquista encontrada para os filtros selecionados.")
        else:
            st.info("Sincronize seu save para ver o progresso das conquistas.")
        return

    for ach in achievements:
        _render_achievement_card(slot_index, ach)


# "A glória pertence àquele que persiste." -- Marcus Aurelius
