from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

import streamlit as st
from api_client import (
    create_session,
    create_set,
    delete_set,
    update_set,
)
from api_errors import ApiClientError, ApiNotFoundError
from data_cache import (
    as_cache_date,
    cached_get_session,
    cached_list_exercises,
    cached_list_session_sets,
    cached_list_sessions,
    invalidate_exercises_cache,
    invalidate_workout_cache,
)
from ui import check_api_available, configure_page, empty_state, show_api_error

SPLIT_TYPES = ("PUSH", "PULL", "LEGS", "OTHER")
ACTIVE_SESSION_KEY = "active_session_id"
SELECTED_EXERCISE_KEY = "workout_selected_exercise_id"
SUBMIT_LOCK_KEY = "workout_set_submitting"
LAST_1RM_KEY = "workout_last_1rm"
COPY_SET_KEY = "workout_copy_set"

configure_page("Trening", layout="wide")
st.title("Trening")
api_ok = check_api_available()

if not api_ok:
    st.warning("Najpierw uruchom API (`make run-api`).")
    st.stop()

if st.sidebar.button("Odśwież dane treningu"):
    invalidate_workout_cache()
    invalidate_exercises_cache()
    st.rerun()


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    number = _to_float(value)
    if number is None:
        return None
    return int(number)


def _load_sessions_for_day(workout_date: date) -> list[dict[str, Any]]:
    day = as_cache_date(workout_date)
    try:
        return cached_list_sessions(date_from=day, date_to=day)
    except ApiClientError as exc:
        show_api_error(exc)
        return []


def _load_active_exercises() -> list[dict[str, Any]]:
    try:
        exercises = cached_list_exercises(is_active=True)
    except ApiClientError as exc:
        show_api_error(exc)
        return []
    return sorted(exercises, key=lambda item: str(item["name"]).lower())


def _load_session(session_id: int) -> dict[str, Any] | None:
    try:
        return cached_get_session(session_id)
    except ApiNotFoundError:
        st.warning("Wybrana sesja nie istnieje już w API.")
        st.session_state.pop(ACTIVE_SESSION_KEY, None)
        invalidate_workout_cache()
        return None
    except ApiClientError as exc:
        show_api_error(exc)
        return None


def _load_sets(session_id: int) -> list[dict[str, Any]]:
    try:
        return cached_list_session_sets(session_id)
    except ApiClientError as exc:
        show_api_error(exc)
        return []


def _next_set_number(sets: list[dict[str, Any]], exercise_id: int) -> int:
    numbers = [int(item["set_number"]) for item in sets if int(item["exercise_id"]) == exercise_id]
    return (max(numbers) + 1) if numbers else 1


def _last_set_for_exercise(sets: list[dict[str, Any]], exercise_id: int) -> dict[str, Any] | None:
    matching = [item for item in sets if int(item["exercise_id"]) == exercise_id]
    if not matching:
        return None
    return max(matching, key=lambda item: int(item["set_number"]))


def _exercise_name_map(exercises: list[dict[str, Any]]) -> dict[int, str]:
    return {int(item["id"]): str(item["name"]) for item in exercises}


st.subheader("Sesja treningowa")
workout_date = st.date_input("Data treningu", value=date.today(), key="workout_date")
split_type = st.selectbox("Typ splitu", options=list(SPLIT_TYPES), key="workout_split")

day_sessions = _load_sessions_for_day(workout_date)
active_session_id = st.session_state.get(ACTIVE_SESSION_KEY)

if day_sessions:
    st.caption(f"Sesje tego dnia: {len(day_sessions)}")
    options = {
        f"#{item['id']} · {item['split_type']} · {item['workout_date']}": int(item["id"])
        for item in day_sessions
    }
    labels = list(options.keys())
    default_index = 0
    if active_session_id in options.values():
        default_index = list(options.values()).index(active_session_id)

    chosen_label = st.radio(
        "Wybierz istniejącą sesję",
        options=labels,
        index=default_index,
        key="workout_session_choice",
    )
    col_select, col_create, col_clear = st.columns(3)
    with col_select:
        if st.button("Użyj wybranej sesji", type="primary"):
            st.session_state[ACTIVE_SESSION_KEY] = options[chosen_label]
            invalidate_workout_cache()
            st.rerun()
    with col_create:
        if st.button("Utwórz nową sesję"):
            try:
                created = create_session(workout_date, split_type)
                invalidate_workout_cache()
                st.session_state[ACTIVE_SESSION_KEY] = int(created["id"])
                st.success(f"Utworzono sesję #{created['id']}.")
                st.rerun()
            except ApiClientError as exc:
                show_api_error(exc)
    with col_clear:
        if st.button("Odłącz sesję"):
            st.session_state.pop(ACTIVE_SESSION_KEY, None)
            st.rerun()
else:
    empty_state(
        "Brak sesji dla tej daty.",
        next_step=(
            "Utwórz sesję świadomie przyciskiem poniżej — nie powstanie sama przy odświeżeniu."
        ),
    )
    if st.button("Utwórz sesję", type="primary"):
        try:
            created = create_session(workout_date, split_type)
            invalidate_workout_cache()
            st.session_state[ACTIVE_SESSION_KEY] = int(created["id"])
            st.success(f"Utworzono sesję #{created['id']}.")
            st.rerun()
        except ApiClientError as exc:
            show_api_error(exc)

active_session_id = st.session_state.get(ACTIVE_SESSION_KEY)
if active_session_id is None:
    st.info("Wybierz lub utwórz sesję, żeby dodawać serie.")
    st.stop()

session = _load_session(int(active_session_id))
if session is None:
    st.stop()

st.success(
    f"Aktywna sesja **#{session['id']}** · {session['workout_date']} · {session['split_type']}"
)

sets = _load_sets(int(session["id"]))
exercises = _load_active_exercises()
all_exercises_for_names = exercises
try:
    archived = cached_list_exercises(is_active=False)
    all_exercises_for_names = exercises + archived
except ApiClientError:
    pass
name_by_id = _exercise_name_map(all_exercises_for_names)

st.subheader("Podsumowanie sesji")
exercise_ids = {int(item["exercise_id"]) for item in sets}
st.write(f"Ćwiczenia: **{len(exercise_ids)}** · Serie: **{len(sets)}**")
if not sets:
    empty_state(
        "Ta sesja nie ma jeszcze serii.",
        next_step="Dodaj pierwszą serię formularzem poniżej.",
    )

st.divider()
st.subheader("Dodaj serię")
st.caption(
    "RPE: skala 1–10 z krokiem 0.5 (opcjonalnie). 1RM liczy backend — UI tylko wyświetla wynik."
)

if not exercises:
    empty_state(
        "Brak aktywnych ćwiczeń.",
        next_step="Dodaj ćwiczenie na stronie Ćwiczenia (archiwalne nie pojawią się tutaj).",
    )
else:
    exercise_labels = {
        f"{item['name']}" + (f" · {item['muscle_group']}" if item.get("muscle_group") else ""): int(
            item["id"]
        )
        for item in exercises
    }
    label_list = list(exercise_labels.keys())
    selected_exercise_id = st.session_state.get(SELECTED_EXERCISE_KEY)
    default_ex_index = 0
    if selected_exercise_id in exercise_labels.values():
        default_ex_index = list(exercise_labels.values()).index(selected_exercise_id)

    chosen_exercise_label = st.selectbox(
        "Ćwiczenie",
        options=label_list,
        index=default_ex_index,
        key="add_set_exercise",
    )
    exercise_id = exercise_labels[chosen_exercise_label]
    st.session_state[SELECTED_EXERCISE_KEY] = exercise_id

    suggested_number = _next_set_number(sets, exercise_id)
    previous = _last_set_for_exercise(sets, exercise_id)
    copy_defaults = st.session_state.pop(COPY_SET_KEY, None)

    if previous is not None and st.button("Przepisz wartości poprzedniej serii tego ćwiczenia"):
        st.session_state[COPY_SET_KEY] = {
            "weight_kg": _to_float(previous.get("weight_kg")) or 0.0,
            "reps": _to_int(previous.get("reps")) or 1,
            "rpe": _to_float(previous.get("rpe")),
            "is_warmup": bool(previous.get("is_warmup")),
        }
        st.rerun()

    weight_default = 0.0
    reps_default = 5
    rpe_default = 0.0
    warmup_default = False
    if copy_defaults:
        weight_default = float(copy_defaults.get("weight_kg") or 0.0)
        reps_default = int(copy_defaults.get("reps") or 1)
        rpe_raw = copy_defaults.get("rpe")
        rpe_default = float(rpe_raw) if rpe_raw is not None else 0.0
        warmup_default = bool(copy_defaults.get("is_warmup"))

    locked = bool(st.session_state.get(SUBMIT_LOCK_KEY))
    with st.form("add_set_form", clear_on_submit=False):
        set_number = st.number_input(
            "Numer serii",
            min_value=1,
            value=suggested_number,
            step=1,
        )
        weight_kg = st.number_input(
            "Ciężar [kg]",
            min_value=0.0,
            max_value=1000.0,
            value=weight_default,
            step=2.5,
            format="%.2f",
        )
        reps = st.number_input("Powtórzenia", min_value=1, max_value=100, value=reps_default)
        rpe = st.number_input(
            "RPE (0 = pomiń)",
            min_value=0.0,
            max_value=10.0,
            value=rpe_default,
            step=0.5,
            format="%.1f",
            help="Wartości 1–10 z krokiem 0.5. 0 oznacza brak RPE.",
        )
        is_warmup = st.checkbox("Rozgrzewka", value=warmup_default)
        submitted = st.form_submit_button(
            "Dodaj serię",
            type="primary",
            disabled=locked,
        )

    if submitted:
        fingerprint = (
            int(session["id"]),
            exercise_id,
            int(set_number),
            float(weight_kg),
            int(reps),
            float(rpe),
            bool(is_warmup),
        )
        if st.session_state.get(SUBMIT_LOCK_KEY):
            st.warning("Trwa zapis serii — poczekaj na zakończenie requestu.")
        elif st.session_state.get("last_set_fingerprint") == fingerprint:
            st.warning("Ta sama seria została już wysłana. Zmień dane albo numer serii.")
        else:
            st.session_state[SUBMIT_LOCK_KEY] = True
            payload_rpe = None if rpe == 0 else rpe
            try:
                created = create_set(
                    int(session["id"]),
                    exercise_id=exercise_id,
                    set_number=int(set_number),
                    weight_kg=weight_kg,
                    reps=int(reps),
                    rpe=payload_rpe,
                    is_warmup=is_warmup,
                )
                invalidate_workout_cache()
                st.session_state[LAST_1RM_KEY] = created.get("calculated_1rm")
                st.session_state[SELECTED_EXERCISE_KEY] = exercise_id
                st.session_state["last_set_fingerprint"] = fingerprint
                st.success(
                    f"Dodano serię #{created['set_number']}. "
                    f"1RM z API: {created['calculated_1rm']} kg"
                )
                st.session_state[SUBMIT_LOCK_KEY] = False
                st.rerun()
            except ApiClientError as exc:
                st.session_state[SUBMIT_LOCK_KEY] = False
                show_api_error(exc)

    last_1rm = st.session_state.get(LAST_1RM_KEY)
    if last_1rm is not None:
        st.info(f"Ostatnio zapisany 1RM (z API): **{last_1rm} kg**")

st.divider()
st.subheader("Serie w sesji")

if not sets:
    st.caption("Brak serii do wyświetlenia.")
else:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for item in sets:
        grouped[int(item["exercise_id"])].append(item)

    for exercise_id, exercise_sets in grouped.items():
        exercise_name = name_by_id.get(exercise_id, f"Ćwiczenie #{exercise_id}")
        st.markdown(f"#### {exercise_name}")
        ordered = sorted(exercise_sets, key=lambda item: int(item["set_number"]))
        for workout_set in ordered:
            set_id = int(workout_set["id"])
            warmup_mark = " · rozgrzewka" if workout_set.get("is_warmup") else ""
            title = (
                f"Seria {workout_set['set_number']}{warmup_mark} · "
                f"{workout_set['weight_kg']} kg × {workout_set['reps']} · "
                f"RPE {workout_set.get('rpe') or '—'} · "
                f"1RM {workout_set['calculated_1rm']} kg"
            )
            with st.expander(title):
                with st.form(f"edit_set_{set_id}"):
                    edit_weight = st.number_input(
                        "Ciężar [kg]",
                        min_value=0.0,
                        max_value=1000.0,
                        value=_to_float(workout_set.get("weight_kg")) or 0.0,
                        step=2.5,
                        format="%.2f",
                        key=f"w_{set_id}",
                    )
                    edit_reps = st.number_input(
                        "Powtórzenia",
                        min_value=1,
                        max_value=100,
                        value=_to_int(workout_set.get("reps")) or 1,
                        key=f"r_{set_id}",
                    )
                    edit_rpe_raw = _to_float(workout_set.get("rpe"))
                    edit_rpe = st.number_input(
                        "RPE (0 = pomiń)",
                        min_value=0.0,
                        max_value=10.0,
                        value=edit_rpe_raw if edit_rpe_raw is not None else 0.0,
                        step=0.5,
                        format="%.1f",
                        key=f"rpe_{set_id}",
                    )
                    edit_warmup = st.checkbox(
                        "Rozgrzewka",
                        value=bool(workout_set.get("is_warmup")),
                        key=f"wu_{set_id}",
                    )
                    edit_number = st.number_input(
                        "Numer serii",
                        min_value=1,
                        value=int(workout_set["set_number"]),
                        key=f"n_{set_id}",
                    )
                    save_edit = st.form_submit_button("Zapisz zmiany")

                if save_edit:
                    try:
                        updated = update_set(
                            set_id,
                            set_number=int(edit_number),
                            weight_kg=edit_weight,
                            reps=int(edit_reps),
                            rpe=None if edit_rpe == 0 else edit_rpe,
                            is_warmup=edit_warmup,
                        )
                        invalidate_workout_cache()
                        st.session_state[LAST_1RM_KEY] = updated.get("calculated_1rm")
                        st.success(
                            f"Zaktualizowano serię. Nowy 1RM z API: {updated['calculated_1rm']} kg"
                        )
                        st.rerun()
                    except ApiClientError as exc:
                        show_api_error(exc)

                confirm_delete = st.checkbox(
                    "Potwierdzam usunięcie serii",
                    key=f"del_confirm_{set_id}",
                )
                if st.button(
                    "Usuń serię",
                    key=f"del_{set_id}",
                    type="secondary",
                    disabled=not confirm_delete,
                ):
                    try:
                        delete_set(set_id)
                        invalidate_workout_cache()
                        st.success("Usunięto serię.")
                        st.rerun()
                    except ApiClientError as exc:
                        show_api_error(exc)
