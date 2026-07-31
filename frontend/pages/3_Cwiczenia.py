from __future__ import annotations

from typing import Any

import streamlit as st
from api_client import create_exercise, update_exercise
from api_errors import ApiClientError
from data_cache import cached_list_exercises, invalidate_exercises_cache
from ui import check_api_available, configure_page, empty_state, show_api_error

configure_page("Ćwiczenia")
st.title("Ćwiczenia")
api_ok = check_api_available()

if not api_ok:
    st.warning("Najpierw uruchom API (`make run-api`).")
    st.stop()

if st.sidebar.button("Odśwież ćwiczenia"):
    invalidate_exercises_cache()
    st.rerun()


def _load_exercises(*, is_active: bool) -> list[dict[str, Any]]:
    try:
        return cached_list_exercises(is_active=is_active)
    except ApiClientError as exc:
        show_api_error(exc)
        return []


st.subheader("Nowe ćwiczenie")
with st.form("create_exercise_form", clear_on_submit=False):
    new_name = st.text_input("Nazwa", max_chars=120)
    new_muscle = st.text_input("Grupa mięśniowa (opcjonalnie)", max_chars=50)
    create_submitted = st.form_submit_button("Dodaj", type="primary")

if create_submitted:
    name = new_name.strip()
    muscle = new_muscle.strip() or None
    if not name:
        st.error("Nazwa jest wymagana.")
    else:
        try:
            create_exercise(name, muscle_group=muscle)
            invalidate_exercises_cache()
            st.success(f"Dodano ćwiczenie „{name}”.")
            st.rerun()
        except ApiClientError as exc:
            show_api_error(exc)

st.divider()
st.subheader("Aktywne")

active = _load_exercises(is_active=True)
if not active:
    empty_state(
        "Brak aktywnych ćwiczeń.",
        next_step="Dodaj pierwsze ćwiczenie formularzem powyżej.",
    )
else:
    for exercise in sorted(active, key=lambda item: item["name"].lower()):
        label = exercise["name"]
        muscle = exercise.get("muscle_group") or "—"
        with st.expander(f"{label} · {muscle}"):
            with st.form(f"edit_exercise_{exercise['id']}"):
                edited_name = st.text_input(
                    "Nazwa",
                    value=exercise["name"],
                    max_chars=120,
                    key=f"name_{exercise['id']}",
                )
                edited_muscle = st.text_input(
                    "Grupa mięśniowa",
                    value=exercise.get("muscle_group") or "",
                    max_chars=50,
                    key=f"muscle_{exercise['id']}",
                )
                save = st.form_submit_button("Zapisz zmiany")

            if save:
                name = edited_name.strip()
                muscle = edited_muscle.strip() or None
                if not name:
                    st.error("Nazwa jest wymagana.")
                else:
                    try:
                        update_exercise(
                            exercise["id"],
                            name=name,
                            muscle_group=muscle,
                        )
                        invalidate_exercises_cache()
                        st.success("Zaktualizowano ćwiczenie.")
                        st.rerun()
                    except ApiClientError as exc:
                        show_api_error(exc)

            confirm_archive = st.checkbox(
                "Potwierdzam archiwizację",
                key=f"archive_confirm_{exercise['id']}",
            )
            if st.button(
                "Archiwizuj",
                key=f"archive_{exercise['id']}",
                type="secondary",
                disabled=not confirm_archive,
            ):
                try:
                    update_exercise(exercise["id"], is_active=False)
                    invalidate_exercises_cache()
                    st.success(f"Zarchiwizowano „{exercise['name']}”.")
                    st.rerun()
                except ApiClientError as exc:
                    show_api_error(exc)

st.divider()
st.subheader("Archiwalne")

archived = _load_exercises(is_active=False)
if not archived:
    st.caption("Brak zarchiwizowanych ćwiczeń.")
else:
    st.caption("Historia nie jest usuwana — ćwiczenie można przywrócić.")
    for exercise in sorted(archived, key=lambda item: item["name"].lower()):
        muscle = exercise.get("muscle_group") or "—"
        col_name, col_action = st.columns([3, 1])
        with col_name:
            st.write(f"**{exercise['name']}** · {muscle}")
        with col_action:
            if st.button("Przywróć", key=f"restore_{exercise['id']}"):
                try:
                    update_exercise(exercise["id"], is_active=True)
                    invalidate_exercises_cache()
                    st.success(f"Przywrócono „{exercise['name']}”.")
                    st.rerun()
                except ApiClientError as exc:
                    show_api_error(exc)
