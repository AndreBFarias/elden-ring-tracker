import streamlit as st

from log import get_logger
from map_config import CATEGORIES, CATEGORY_GROUPS
from progress_tracker import get_overall_stats, get_progress

logger = get_logger("pages.progress")

ITEMS_PER_PAGE = 50

AUTO_DETECT_CATEGORIES = {
    "boss", "grace", "dungeon", "flask_upgrade", "ash_of_war", "map_fragment", "key_item",
    "weapon", "armor", "shield", "talisman", "spell", "consumable", "material",
    "upgrade_material", "npc", "npc_invader",
}


def _render_progress_bar(label: str, completed: int, total: int, color: str) -> None:
    pct = (completed / total * 100) if total > 0 else 0
    st.markdown(
        f'<div style="margin-bottom:0.5rem;">'
        f'<span style="color:{color};font-weight:bold;font-family:monospace;">{label}</span>'
        f' <span style="color:#6272a4;font-family:monospace;">{completed}/{total} ({pct:.0f}%)</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.progress(min(pct / 100, 1.0))


def _render_item_list(
    slot_index: int, category: str, items: list[dict], show_completed: bool
) -> None:
    filtered = [i for i in items if i["completed"] == show_completed]
    if not filtered:
        if show_completed:
            if category in ("boss", "grace"):
                st.caption("Nenhum registro. Sincronize seu save para ver o progresso automático.")
            else:
                st.caption("Nenhum item concluído.")
        else:
            st.caption("Todos concluídos nesta categoria.")
        return

    total_items = len(filtered)
    total_pages = max(1, (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    status_key = "done" if show_completed else "pending"
    page_key = f"page_{category}_{status_key}"

    if page_key not in st.session_state:
        st.session_state[page_key] = 0

    current_page = st.session_state[page_key]
    current_page = min(current_page, total_pages - 1)
    start = current_page * ITEMS_PER_PAGE
    end = min(start + ITEMS_PER_PAGE, total_items)
    page_items = filtered[start:end]

    st.caption(f"{total_items} itens | página {current_page + 1}/{total_pages}")

    for idx, item in enumerate(page_items, start=start):
        name = item["name"]
        region = item.get("region", "")
        key = f"chk_{category}_{status_key}_{idx}_{name}"

        region_tag = (
            f' <span style="color:#8be9fd;font-size:0.75rem;">({region})</span>'
            if region
            else ""
        )
        name_html = (
            f'<span style="font-family:monospace;">{name}{region_tag}</span>'
        )

        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            st.markdown(name_html, unsafe_allow_html=True)
        with col2:
            if st.button(
                "Ver no Mapa",
                key=f"map_{key}",
                use_container_width=True,
            ):
                st.session_state["_pending_map_search"] = name
                st.session_state["_pending_map_region"] = region
                st.rerun()

    if total_pages > 1:
        col_prev, col_info, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button("Anterior", key=f"prev_{page_key}", disabled=current_page == 0, use_container_width=True):
                st.session_state[page_key] = current_page - 1
                st.rerun()
        with col_info:
            st.markdown(
                f'<p style="text-align:center;font-family:monospace;color:#6272a4;margin-top:0.5rem;">'
                f'{start + 1}-{end} de {total_items}</p>',
                unsafe_allow_html=True,
            )
        with col_next:
            if st.button("Próximo", key=f"next_{page_key}", disabled=current_page >= total_pages - 1, use_container_width=True):
                st.session_state[page_key] = current_page + 1
                st.rerun()


def _render_ref_list(category: str, items: list[dict]) -> None:
    total_items = len(items)
    if not total_items:
        st.caption("Nenhum item nesta categoria.")
        return

    total_pages = max(1, (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    page_key = f"page_{category}_ref"

    if page_key not in st.session_state:
        st.session_state[page_key] = 0

    current_page = st.session_state[page_key]
    current_page = min(current_page, total_pages - 1)
    start = current_page * ITEMS_PER_PAGE
    end = min(start + ITEMS_PER_PAGE, total_items)
    page_items = items[start:end]

    st.caption(f"{total_items} itens | página {current_page + 1}/{total_pages}")

    for idx, item in enumerate(page_items, start=start):
        name = item["name"]
        region = item.get("region", "")

        region_tag = (
            f' <span style="color:#8be9fd;font-size:0.75rem;">({region})</span>'
            if region
            else ""
        )
        name_html = (
            f'<span style="font-family:monospace;">{name}{region_tag}</span>'
        )

        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            st.markdown(name_html, unsafe_allow_html=True)
        with col2:
            if st.button(
                "Ver no Mapa",
                key=f"map_ref_{category}_{idx}",
                use_container_width=True,
            ):
                st.session_state["_pending_map_search"] = name
                st.session_state["_pending_map_region"] = region
                st.rerun()

    if total_pages > 1:
        col_prev, col_info, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button("Anterior", key=f"prev_{page_key}", disabled=current_page == 0, use_container_width=True):
                st.session_state[page_key] = current_page - 1
                st.rerun()
        with col_info:
            st.markdown(
                f'<p style="text-align:center;font-family:monospace;color:#6272a4;margin-top:0.5rem;">'
                f'{start + 1}-{end} de {total_items}</p>',
                unsafe_allow_html=True,
            )
        with col_next:
            if st.button("Próximo", key=f"next_{page_key}", disabled=current_page >= total_pages - 1, use_container_width=True):
                st.session_state[page_key] = current_page + 1
                st.rerun()


def _render_category_auto(
    slot_index: int, category: str, region: str, completion_mode: str = "a_fazer"
) -> None:
    cat_config = CATEGORIES.get(category)
    if not cat_config:
        return
    color = cat_config.color
    label = cat_config.display_name
    progress = get_progress(slot_index, category, region=region)

    done_count = sum(1 for i in progress["items"] if i["completed"])
    pending_count = sum(1 for i in progress["items"] if not i["completed"])

    if completion_mode == "feito":
        expander_label = f"{label} — {done_count} concluídos"
    else:
        expander_label = f"{label} — {pending_count} pendentes"

    with st.expander(expander_label, expanded=False):
        _render_progress_bar(label, progress["completed"], progress["total"], color)
        show_completed = completion_mode == "feito"
        _render_item_list(slot_index, category, progress["items"], show_completed=show_completed)


def _render_category_ref(category: str, region: str) -> None:
    cat_config = CATEGORIES.get(category)
    if not cat_config:
        return
    color = cat_config.color
    label = cat_config.display_name
    progress = get_progress(0, category, region=region)

    with st.expander(
        f"{label} - {progress['total']} itens",
        expanded=False,
    ):
        st.markdown(
            f'<div style="margin-bottom:0.5rem;">'
            f'<span style="color:{color};font-weight:bold;font-family:monospace;">{label}</span>'
            f' <span style="color:#6272a4;font-family:monospace;">{progress["total"]} no total</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        _render_ref_list(category, progress["items"])


def render(slot_index: int, region: str = "", completion_mode: str = "a_fazer") -> None:
    overall = get_overall_stats(slot_index, region=region)

    st.markdown(
        '<p style="font-family:monospace;color:#bd93f9;text-transform:uppercase;'
        'letter-spacing:0.1em;font-size:0.85rem;border-bottom:1px solid #44475a;'
        'padding-bottom:0.25rem;">Progresso Geral</p>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        c1.metric("Total", overall["total"])
        c2.metric("Concluído", overall["completed"])
        c3.metric("Restante", overall["remaining"])
        st.progress(min(overall["percentage"] / 100, 1.0))

    st.markdown("")

    for group_name, cat_keys in CATEGORY_GROUPS.items():
        st.markdown(
            f'<p style="font-family:monospace;color:#bd93f9;text-transform:uppercase;'
            f'letter-spacing:0.1em;font-size:0.8rem;margin-top:1rem;'
            f'border-bottom:1px solid #44475a;padding-bottom:0.25rem;">'
            f'{group_name}</p>',
            unsafe_allow_html=True,
        )

        for category in cat_keys:
            if category not in CATEGORIES:
                continue
            if category in AUTO_DETECT_CATEGORIES:
                _render_category_auto(slot_index, category, region, completion_mode)
            else:
                _render_category_ref(category, region)


# "O progresso e impossivel sem mudanca." -- George Bernard Shaw
