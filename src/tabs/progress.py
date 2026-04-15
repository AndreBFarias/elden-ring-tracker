import base64
import json
import re
from pathlib import Path

import streamlit as st

from log import get_logger
from map_config import CATEGORIES, CATEGORY_GROUPS
from progress_tracker import get_overall_stats, get_progress
from subcategory_resolver import group_by_subcategory, has_subcategories

logger = get_logger("pages.progress")

ITEMS_PER_PAGE = 50

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
IMAGES_DIR = PROJECT_ROOT / "assets" / "item_images"
REFERENCES_DIR = PROJECT_ROOT / "data" / "references"

_wiki_links: dict[str, str] | None = None
_image_cache: dict[str, str] = {}


def _load_wiki_links() -> dict[str, str]:
    global _wiki_links
    if _wiki_links is not None:
        return _wiki_links
    path = REFERENCES_DIR / "wiki_links.json"
    if path.exists():
        try:
            with open(str(path), encoding="utf-8") as f:
                _wiki_links = json.load(f)
        except (json.JSONDecodeError, OSError):
            _wiki_links = {}
    else:
        _wiki_links = {}
    return _wiki_links


def _sanitize_filename(name: str) -> str:
    clean = re.sub(r"[^\w\s\-'.()]", "", name)
    clean = re.sub(r"\s+", "_", clean.strip())
    return clean[:120]


def _get_image_b64(item_name: str, category: str) -> str:
    cache_key = f"{category}/{item_name}"
    if cache_key in _image_cache:
        return _image_cache[cache_key]

    filename = _sanitize_filename(item_name) + ".webp"
    path = IMAGES_DIR / category / filename
    if path.exists():
        data = path.read_bytes()
        b64 = base64.b64encode(data).decode()
        _image_cache[cache_key] = b64
        return b64

    _image_cache[cache_key] = ""
    return ""


def _get_wiki_url(item_name: str) -> str:
    links = _load_wiki_links()
    return links.get(item_name, "")

AUTO_DETECT_CATEGORIES = {
    "boss", "grace", "dungeon", "flask_upgrade", "ash_of_war", "map_fragment", "key_item",
    "weapon", "armor", "shield", "talisman", "spell", "consumable", "material",
    "upgrade_material", "spirit_ash", "npc", "npc_invader",
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

    base_cat = category.split("_")[0] if "_" in category else category

    for idx, item in enumerate(page_items, start=start):
        name = item["name"]
        region = item.get("region", "")
        key = f"chk_{category}_{status_key}_{idx}_{name}"

        img_b64 = _get_image_b64(name, base_cat)
        wiki_url = _get_wiki_url(name)

        img_html = ""
        if img_b64:
            img_html = (
                f'<img src="data:image/webp;base64,{img_b64}" '
                f'style="width:40px;height:40px;object-fit:contain;'
                f'border-radius:4px;background:#44475a;margin-right:0.5rem;'
                f'vertical-align:middle;" />'
            )

        region_tag = (
            f' <span style="color:#8be9fd;font-size:0.7rem;">({region})</span>'
            if region
            else ""
        )

        wiki_link = ""
        if wiki_url:
            wiki_link = (
                f' <a href="{wiki_url}" target="_blank" '
                f'style="color:#bd93f9;font-size:0.7rem;text-decoration:none;'
                f'margin-left:0.3rem;" title="Abrir na wiki">Wiki</a>'
            )

        completed = item.get("completed", False)
        border_color = "#50fa7b" if completed else "#44475a"

        card_html = (
            f'<div style="display:flex;align-items:center;'
            f'background:#282a36;border:1px solid {border_color};'
            f'border-radius:6px;padding:0.4rem 0.6rem;margin-bottom:0.3rem;">'
            f'{img_html}'
            f'<div style="flex:1;">'
            f'<span style="font-family:monospace;font-size:0.85rem;color:#f8f8f2;">'
            f'{name}</span>{region_tag}{wiki_link}'
            f'</div></div>'
        )

        col1, col2 = st.columns([0.85, 0.15])
        with col1:
            st.markdown(card_html, unsafe_allow_html=True)
        with col2:
            if st.button(
                "Mapa",
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


def _render_subcategory_header(
    sub_name: str, done: int, total: int, color: str,
) -> None:
    pct = (done / total * 100) if total > 0 else 0
    st.markdown(
        f'<div style="margin-top:0.8rem;margin-bottom:0.3rem;'
        f'padding:0.3rem 0.5rem;border-left:3px solid {color};'
        f'background:rgba(68,71,90,0.3);border-radius:0 4px 4px 0;">'
        f'<span style="color:#f8f8f2;font-family:monospace;font-weight:bold;'
        f'font-size:0.85rem;">{sub_name}</span>'
        f' <span style="color:#6272a4;font-family:monospace;font-size:0.8rem;">'
        f'{done}/{total} ({pct:.0f}%)</span></div>',
        unsafe_allow_html=True,
    )


def _render_category_auto(
    slot_index: int, category: str, region: str, completion_mode: str = "a_fazer",
    include_dlc: bool = True, include_altered: bool = True, search_query: str = "",
) -> None:
    cat_config = CATEGORIES.get(category)
    if not cat_config:
        return
    color = cat_config.color
    label = cat_config.display_name
    progress = get_progress(slot_index, category, region=region)

    progress["items"] = _apply_filters(
        progress["items"], include_dlc, include_altered, search_query,
    )
    progress["total"] = len(progress["items"])
    progress["completed"] = sum(1 for i in progress["items"] if i["completed"])
    progress["remaining"] = progress["total"] - progress["completed"]

    if search_query and not progress["items"]:
        return

    done_count = sum(1 for i in progress["items"] if i["completed"])
    pending_count = sum(1 for i in progress["items"] if not i["completed"])

    if completion_mode == "feito":
        expander_label = f"{label} — {done_count}/{progress['total']} concluídos"
    else:
        expander_label = f"{label} — {pending_count}/{progress['total']} pendentes"

    show_completed = completion_mode == "feito"

    if has_subcategories(category):
        grouped = group_by_subcategory(progress["items"], category)
        with st.expander(expander_label, expanded=False):
            _render_progress_bar(label, progress["completed"], progress["total"], color)

            sub_options = ["Todas"] + list(grouped.keys())
            filter_key = f"sub_filter_{category}"
            selected_sub = st.selectbox(
                "Subcategoria",
                options=sub_options,
                index=0,
                key=filter_key,
                label_visibility="collapsed",
            )

            if selected_sub == "Todas":
                for sub_name, sub_items in grouped.items():
                    done = sum(1 for i in sub_items if i["completed"])
                    _render_subcategory_header(sub_name, done, len(sub_items), color)
                    filtered = [i for i in sub_items if i["completed"] == show_completed]
                    if filtered:
                        for item in filtered[:5]:
                            region_tag = (
                                f' <span style="color:#8be9fd;font-size:0.7rem;">'
                                f'({item.get("region", "")})</span>'
                                if item.get("region")
                                else ""
                            )
                            st.markdown(
                                f'<span style="font-family:monospace;font-size:0.8rem;'
                                f'color:#f8f8f2;padding-left:0.5rem;">'
                                f'{item["name"]}{region_tag}</span>',
                                unsafe_allow_html=True,
                            )
                        if len(filtered) > 5:
                            st.caption(f"... +{len(filtered) - 5} itens")
            else:
                sub_items = grouped.get(selected_sub, [])
                done = sum(1 for i in sub_items if i["completed"])
                _render_subcategory_header(selected_sub, done, len(sub_items), color)
                _render_item_list(
                    slot_index, f"{category}_{selected_sub}",
                    sub_items, show_completed,
                )
    else:
        with st.expander(expander_label, expanded=False):
            _render_progress_bar(label, progress["completed"], progress["total"], color)
            _render_item_list(
                slot_index, category, progress["items"], show_completed=show_completed,
            )


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


def _apply_filters(
    items: list[dict], include_dlc: bool, include_altered: bool, search_query: str,
) -> list[dict]:
    result = items
    if not include_dlc:
        result = [i for i in result if not i.get("is_dlc")]
    if not include_altered:
        result = [i for i in result if not i.get("is_altered")]
    if search_query:
        query_lower = search_query.lower()
        result = [i for i in result if query_lower in i.get("name", "").lower()]
    return result


def render(
    slot_index: int, region: str = "", completion_mode: str = "a_fazer",
    include_dlc: bool = True, include_altered: bool = True,
) -> None:
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

    search_query = st.text_input(
        "Buscar itens",
        key="progress_search",
        placeholder="Buscar por nome...",
        label_visibility="collapsed",
    ).strip()

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
                _render_category_auto(
                    slot_index, category, region, completion_mode,
                    include_dlc=include_dlc, include_altered=include_altered,
                    search_query=search_query,
                )
            else:
                _render_category_ref(category, region)


# "O progresso e impossivel sem mudanca." -- George Bernard Shaw
