import streamlit as st

from database import get_stats_history
from log import get_logger

logger = get_logger("pages.sessions")


def render(slot_index: int) -> None:
    st.markdown(
        '<p style="font-family:monospace;color:#bd93f9;text-transform:uppercase;'
        'letter-spacing:0.1em;font-size:0.85rem;border-bottom:1px solid #44475a;'
        'padding-bottom:0.25rem;">Histórico de Sessões</p>',
        unsafe_allow_html=True,
    )

    rows = get_stats_history(slot_index, limit=20)

    if not rows:
        st.info("Nenhum histórico disponível. Sincronize o save para registrar snapshots.")
        return

    first = rows[0]
    last = rows[-1]
    level_gain = first["level"] - last["level"]

    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        c1.metric("Nível Atual", first["level"])
        c2.metric("Snapshots", len(rows))
        c3.metric("Ganho de Nível", f"+{level_gain}" if level_gain >= 0 else str(level_gain))

    st.markdown("")

    st.markdown(
        '<p style="font-family:monospace;color:#bd93f9;text-transform:uppercase;'
        'letter-spacing:0.1em;font-size:0.8rem;margin-top:1rem;'
        'border-bottom:1px solid #44475a;padding-bottom:0.25rem;">'
        'Snapshots Recentes</p>',
        unsafe_allow_html=True,
    )

    for row in rows:
        recorded_at = row["recorded_at"].replace("T", " ").replace("Z", "")
        attrs = (
            f"VIG {row['vigor']} | MND {row['mind']} | END {row['endurance']} | "
            f"STR {row['strength']} | DEX {row['dexterity']} | "
            f"INT {row['intelligence']} | FAI {row['faith']} | ARC {row['arcane']}"
        )
        st.markdown(
            f'<div style="background-color:#282a36;border:1px solid #44475a;'
            f'border-radius:6px;padding:0.6rem 0.8rem;margin-bottom:0.4rem;'
            f'font-family:monospace;">'
            f'<span style="color:#6272a4;font-size:0.75rem;">{recorded_at}</span>'
            f'<span style="color:#f8f8f2;margin-left:1rem;">Nível <b>{row["level"]}</b></span>'
            f'<span style="color:#50fa7b;margin-left:0.75rem;">{row["runes_held"]:,} runas</span>'
            f'<br><span style="color:#8be9fd;font-size:0.75rem;">{attrs}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


# "O passado e o prologo." -- William Shakespeare
