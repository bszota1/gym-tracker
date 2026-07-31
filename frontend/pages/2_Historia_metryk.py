from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd
import streamlit as st
from api_errors import ApiClientError
from data_cache import as_cache_date, cached_list_daily_metrics, invalidate_metrics_cache
from ui import check_api_available, configure_page, empty_state, show_api_error

configure_page("Historia metryk", layout="wide")
st.title("Historia metryk")
api_ok = check_api_available()

if not api_ok:
    st.warning("Najpierw uruchom API (`make run-api`).")
    st.stop()

if st.sidebar.button("Odśwież historię"):
    invalidate_metrics_cache()
    st.rerun()


def _display_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


today = date.today()
col_from, col_to = st.columns(2)
with col_from:
    date_from = st.date_input("Od", value=today - timedelta(days=30), key="history_from")
with col_to:
    date_to = st.date_input("Do", value=today, key="history_to")

if date_from > date_to:
    st.error("Data „Od” nie może być późniejsza niż „Do”.")
    st.stop()

try:
    rows = cached_list_daily_metrics(
        date_from=as_cache_date(date_from),
        date_to=as_cache_date(date_to),
    )
except ApiClientError as exc:
    show_api_error(exc)
    st.stop()

if not rows:
    empty_state(
        "Brak metryk w wybranym zakresie dat.",
        next_step="Dodaj wpis na stronie Metryki albo poszerz zakres.",
    )
    st.stop()

sorted_rows = sorted(rows, key=lambda row: row["metric_date"], reverse=True)
table = pd.DataFrame(
    [
        {
            "Data": row["metric_date"],
            "Masa [kg]": _display_value(row.get("body_weight_kg")),
            "Kalorie [kcal]": _display_value(row.get("calories_kcal")),
            "Sen [h]": _display_value(row.get("sleep_hours")),
            "Notatki": _display_value(row.get("notes")),
        }
        for row in sorted_rows
    ]
)

st.caption(f"Wpisów: {len(table)} · sortowanie: data malejąco")
st.dataframe(table, use_container_width=True, hide_index=True)
