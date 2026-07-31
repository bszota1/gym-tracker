from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st
from api_client import create_daily_metric, delete_daily_metric, update_daily_metric
from api_errors import ApiClientError
from data_cache import (
    as_cache_date,
    cached_get_daily_metric,
    invalidate_metrics_cache,
    invalidate_workout_cache,
)
from ui import check_api_available, configure_page, show_api_error

configure_page("Metryki")
st.title("Metryki dzienne")
api_ok = check_api_available()

if not api_ok:
    st.warning("Najpierw uruchom API (`make run-api`).")
    st.stop()

if st.sidebar.button("Odśwież metryki"):
    invalidate_metrics_cache()
    st.rerun()


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
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


def _load_metric(metric_date: date) -> dict[str, Any] | None:
    try:
        return cached_get_daily_metric(as_cache_date(metric_date))
    except ApiClientError as exc:
        show_api_error(exc)
        return None


selected_date = st.date_input("Data", value=date.today())
existing = _load_metric(selected_date)
exists = existing is not None

if exists:
    st.caption("Znaleziono wpis dla tej daty — zapis zaktualizuje metryki.")
else:
    st.info("Brak wpisu dla tej daty — zapis utworzy nowy dzień (pola mogą być puste).")

defaults = existing or {}
body_weight_default = _to_float(defaults.get("body_weight_kg"))
calories_default = _to_int(defaults.get("calories_kcal"))
sleep_default = _to_float(defaults.get("sleep_hours"))
notes_default = defaults.get("notes") or ""

with st.form("daily_metrics_form", clear_on_submit=False):
    body_weight_kg = st.number_input(
        "Masa ciała [kg]",
        min_value=0.0,
        max_value=300.0,
        value=body_weight_default if body_weight_default is not None else 0.0,
        step=0.1,
        format="%.2f",
        help="Zakres 30–300. 0 = pomiń pole.",
    )
    calories_kcal = st.number_input(
        "Kalorie [kcal]",
        min_value=0,
        max_value=10000,
        value=calories_default if calories_default is not None else 0,
        step=50,
        help="Zakres 500–10000 przy zapisie wartości. 0 = pomiń pole.",
    )
    sleep_hours = st.number_input(
        "Sen [h]",
        min_value=0.0,
        max_value=24.0,
        value=sleep_default if sleep_default is not None else 0.0,
        step=0.25,
        format="%.2f",
        help="Zakres 0–24 godzin.",
    )
    notes = st.text_area("Notatki", value=notes_default, max_chars=2000)
    submitted = st.form_submit_button("Zapisz", type="primary")

if submitted:
    payload_weight = None if body_weight_kg == 0 else body_weight_kg
    payload_calories = None if calories_kcal == 0 else calories_kcal
    payload_sleep = sleep_hours
    payload_notes = notes.strip() or None

    if payload_weight is not None and not (30 <= payload_weight <= 300):
        st.error("Masa ciała musi być w zakresie 30–300 kg albo 0 (puste).")
    elif payload_calories is not None and not (500 <= payload_calories <= 10000):
        st.error("Kalorie muszą być w zakresie 500–10000 albo 0 (puste).")
    else:
        try:
            if exists:
                update_daily_metric(
                    selected_date,
                    body_weight_kg=payload_weight,
                    calories_kcal=payload_calories,
                    sleep_hours=payload_sleep,
                    notes=payload_notes,
                )
                st.success("Zaktualizowano metryki dnia.")
            else:
                create_daily_metric(
                    selected_date,
                    body_weight_kg=payload_weight,
                    calories_kcal=payload_calories,
                    sleep_hours=payload_sleep,
                    notes=payload_notes,
                )
                st.success("Utworzono metryki dnia.")
            invalidate_metrics_cache()
            st.rerun()
        except ApiClientError as exc:
            show_api_error(exc)

st.divider()
st.subheader("Usuń dzień")

if not exists:
    st.caption("Nie ma wpisu do usunięcia dla tej daty.")
else:
    confirm_delete = st.checkbox("Potwierdzam usunięcie metryk tego dnia")
    if st.button("Usuń", type="secondary", disabled=not confirm_delete):
        try:
            delete_daily_metric(selected_date)
            invalidate_metrics_cache()
            invalidate_workout_cache()
            st.success("Usunięto metryki dnia.")
            st.rerun()
        except ApiClientError as exc:
            show_api_error(exc)
