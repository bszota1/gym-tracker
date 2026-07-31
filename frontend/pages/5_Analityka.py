from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from api_errors import ApiClientError
from data_cache import (
    as_cache_date,
    cached_body_weight_analytics,
    cached_list_exercises,
    cached_one_rm_analytics,
    cached_overview,
    cached_recovery,
    cached_strength_vs_weight,
    invalidate_analytics_cache,
)
from plotly.subplots import make_subplots
from ui import check_api_available, configure_page, empty_state, show_api_error

BODY_WEIGHT_GOAL_MIN_KG = 70
BODY_WEIGHT_GOAL_MAX_KG = 95

configure_page("Analityka", layout="wide")
st.title("Analityka")
api_ok = check_api_available()

if not api_ok:
    st.warning("Najpierw uruchom API (`make run-api`).")
    st.stop()

if st.sidebar.button("Odśwież analitykę"):
    invalidate_analytics_cache()
    st.rerun()

today = date.today()
col_from, col_to = st.columns(2)
with col_from:
    date_from = st.date_input(
        "Od",
        value=today - timedelta(days=90),
        key="analytics_from",
    )
with col_to:
    date_to = st.date_input("Do", value=today, key="analytics_to")

if date_from > date_to:
    st.error("Data „Od” nie może być późniejsza niż „Do”.")
    st.stop()

date_from_s = as_cache_date(date_from)
date_to_s = as_cache_date(date_to)


def _fmt_value(value: Any, *, suffix: str = "", decimals: int = 2) -> str:
    if value is None:
        return "brak danych"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return f"{float(value):.{decimals}f}{suffix}"
    try:
        return f"{float(value):.{decimals}f}{suffix}"
    except (TypeError, ValueError):
        return f"{value}{suffix}"


def _metric_as_of(block: dict[str, Any] | None) -> str:
    if not block:
        return ""
    as_of = block.get("as_of")
    return f"stan na {as_of}" if as_of else "brak daty"


def _date_only(series: Any) -> pd.Series:
    return pd.to_datetime(series).dt.strftime("%Y-%m-%d")


def _apply_date_axis(fig: go.Figure) -> None:
    fig.update_xaxes(tickformat="%Y-%m-%d", hoverformat="%Y-%m-%d")


st.subheader("Przegląd")
try:
    overview = cached_overview(as_of=as_cache_date(today))
except ApiClientError as exc:
    show_api_error(exc)
    overview = None

if overview is None:
    st.stop()

body = overview.get("body_weight") or {}
delta = overview.get("delta_to_target_kg") or {}
avg_cal = overview.get("avg_calories_kcal") or {}
avg_sleep = overview.get("avg_sleep_hours") or {}
sessions = overview.get("sessions_this_week") or {}

if body.get("value") is None and sessions.get("value") in (None, 0):
    empty_state(
        "Brak danych do przeglądu.",
        next_step="Dodaj metryki na stronie Metryki i trening na stronie Trening.",
    )
else:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Masa", _fmt_value(body.get("value"), suffix=" kg"))
    c1.caption(_metric_as_of(body))
    c2.metric("Do celu 90 kg", _fmt_value(delta.get("value"), suffix=" kg"))
    c2.caption(_metric_as_of(delta))
    c3.metric("Śr. kalorie [kcal]", _fmt_value(avg_cal.get("value")))
    c3.caption(_metric_as_of(avg_cal))
    c4.metric("Śr. sen [h]", _fmt_value(avg_sleep.get("value")))
    c4.caption(_metric_as_of(avg_sleep))
    sessions_value = sessions.get("value")
    sessions_label = (
        "brak danych" if sessions_value is None else str(int(sessions_value))
    )
    c5.metric("Sesje w tygodniu", sessions_label)
    c5.caption(_metric_as_of(sessions))

st.divider()

st.subheader("Trend masy")
try:
    weight_payload = cached_body_weight_analytics(date_from_s, date_to_s)
except ApiClientError as exc:
    show_api_error(exc)
    weight_payload = {"points": [], "trend": []}

weight_points = weight_payload.get("points") or []
weight_trend = weight_payload.get("trend") or []

if not weight_points:
    empty_state(
        "Brak pomiarów masy w zakresie.",
        next_step="Uzupełnij masę na stronie Metryki.",
    )
else:
    points_df = pd.DataFrame(weight_points)
    trend_df = pd.DataFrame(weight_trend)
    points_df["date"] = _date_only(points_df["date"])
    if not trend_df.empty:
        trend_df["date"] = _date_only(trend_df["date"])
    fig_w = go.Figure()
    fig_w.add_trace(
        go.Scatter(
            x=points_df["date"],
            y=points_df["body_weight_kg"],
            mode="markers",
            name="Pomiar [kg]",
        )
    )
    if not trend_df.empty:
        fig_w.add_trace(
            go.Scatter(
                x=trend_df["date"],
                y=trend_df["rolling_avg_kg"],
                mode="lines",
                name="Średnia 7 dni [kg]",
            )
        )
    fig_w.add_hline(
        y=BODY_WEIGHT_GOAL_MIN_KG,
        line_dash="dot",
        annotation_text=f"cel min {BODY_WEIGHT_GOAL_MIN_KG} kg",
    )
    fig_w.add_hline(
        y=BODY_WEIGHT_GOAL_MAX_KG,
        line_dash="dot",
        annotation_text=f"cel max {BODY_WEIGHT_GOAL_MAX_KG} kg",
    )
    fig_w.update_layout(
        xaxis_title="Data",
        yaxis_title="Masa [kg]",
        legend_title="",
        hovermode="x unified",
    )
    _apply_date_axis(fig_w)
    rate = weight_payload.get("rate_kg_per_week")
    if rate is not None:
        st.caption(f"Tempo zmiany (szacunek): {rate:.2f} kg/tydzień")
    st.plotly_chart(fig_w, use_container_width=True)

st.divider()

try:
    exercises = cached_list_exercises(is_active=True)
except ApiClientError as exc:
    show_api_error(exc)
    exercises = []

if not exercises:
    empty_state(
        "Brak aktywnych ćwiczeń — wykresy 1RM i siła–masa są niedostępne.",
        next_step="Dodaj ćwiczenie na stronie Ćwiczenia.",
    )
    selected_exercise_id = None
else:
    exercise_labels = {
        f"{item['name']}"
        + (f" · {item['muscle_group']}" if item.get("muscle_group") else ""): int(
            item["id"]
        )
        for item in sorted(exercises, key=lambda item: str(item["name"]).lower())
    }
    chosen = st.selectbox("Ćwiczenie do analityki siły", options=list(exercise_labels))
    selected_exercise_id = exercise_labels[chosen]

st.subheader("Trend 1RM")

if selected_exercise_id is None:
    st.info("Wybierz ćwiczenie, żeby zobaczyć trend 1RM.")
else:
    try:
        one_rm_payload = cached_one_rm_analytics(
            selected_exercise_id,
            date_from_s,
            date_to_s,
        )
    except ApiClientError as exc:
        show_api_error(exc)
        one_rm_payload = {"points": [], "trend": []}

    one_rm_points = one_rm_payload.get("points") or []
    one_rm_trend = one_rm_payload.get("trend") or []
    if not one_rm_points:
        empty_state(
            "Brak serii kwalifikujących się do trendu 1RM.",
            next_step="Dodaj serie robocze (bez rozgrzewki, ≤12 powtórzeń) w Treningu.",
        )
    else:
        orm_df = pd.DataFrame(one_rm_points)
        trend_df = pd.DataFrame(one_rm_trend)
        orm_df["date"] = _date_only(orm_df["date"])
        if not trend_df.empty:
            trend_df["date"] = _date_only(trend_df["date"])
        weights = []
        reps_list = []
        for point in one_rm_points:
            source = point.get("source_set") or {}
            weights.append(source.get("weight_kg"))
            reps_list.append(source.get("reps"))
        fig_orm = go.Figure()
        fig_orm.add_trace(
            go.Scatter(
                x=orm_df["date"],
                y=orm_df["one_rm_kg"],
                mode="markers+lines",
                name="Dzienny 1RM [kg]",
                customdata=list(zip(weights, reps_list, strict=True)),
                hovertemplate=(
                    "Data=%{x}<br>1RM=%{y:.2f} kg"
                    "<br>Seria: %{customdata[0]} kg × %{customdata[1]}"
                    "<extra></extra>"
                ),
            )
        )
        if not trend_df.empty:
            fig_orm.add_trace(
                go.Scatter(
                    x=trend_df["date"],
                    y=trend_df["rolling_avg_kg"],
                    mode="lines",
                    name="Średnia 7 dni [kg]",
                )
            )
        pr = orm_df.loc[orm_df["is_lifetime_pr"].astype(bool)]
        if not pr.empty:
            fig_orm.add_trace(
                go.Scatter(
                    x=pr["date"],
                    y=pr["one_rm_kg"],
                    mode="markers",
                    marker={"size": 14, "symbol": "star"},
                    name="Rekord (w zakresie)",
                )
            )
        fig_orm.update_layout(
            xaxis_title="Data",
            yaxis_title="1RM [kg]",
            hovermode="closest",
        )
        _apply_date_axis(fig_orm)
        st.plotly_chart(fig_orm, use_container_width=True)

st.divider()

st.subheader("Siła względem masy")

if selected_exercise_id is None:
    st.info("Wybierz ćwiczenie powyżej.")
else:
    try:
        vs_payload = cached_strength_vs_weight(
            selected_exercise_id,
            date_from_s,
            date_to_s,
        )
    except ApiClientError as exc:
        show_api_error(exc)
        vs_payload = {"points": []}

    vs_points = vs_payload.get("points") or []
    if not vs_points:
        empty_state(
            "Brak wspólnych danych siły/masy w zakresie.",
            next_step="Dodaj pomiary masy i serie ćwiczenia.",
        )
    else:
        vs_df = pd.DataFrame(vs_points)
        vs_df["date"] = _date_only(vs_df["date"])
        fig_vs = make_subplots(specs=[[{"secondary_y": True}]])
        fig_vs.add_trace(
            go.Scatter(
                x=vs_df["date"],
                y=vs_df["one_rm_kg"],
                mode="markers+lines",
                name="1RM [kg]",
                connectgaps=False,
            ),
            secondary_y=False,
        )
        fig_vs.add_trace(
            go.Scatter(
                x=vs_df["date"],
                y=vs_df["body_weight_kg"],
                mode="markers+lines",
                name="Masa [kg]",
                connectgaps=False,
            ),
            secondary_y=True,
        )
        fig_vs.update_xaxes(title_text="Data")
        fig_vs.update_yaxes(title_text="1RM [kg]", secondary_y=False)
        fig_vs.update_yaxes(title_text="Masa ciała [kg]", secondary_y=True)
        fig_vs.update_layout(hovermode="x unified")
        _apply_date_axis(fig_vs)
        st.plotly_chart(fig_vs, use_container_width=True)

st.divider()

st.subheader("Regeneracja")

recovery_exercise_id = selected_exercise_id
try:
    recovery_payload = cached_recovery(
        date_from_s,
        date_to_s,
        exercise_id=recovery_exercise_id,
    )
except ApiClientError as exc:
    show_api_error(exc)
    recovery_payload = {"points": []}

recovery_points = recovery_payload.get("points") or []
if not recovery_points:
    empty_state(
        "Brak danych regeneracji w zakresie.",
        next_step="Uzupełnij sen/metryki i treningi.",
    )
else:
    rec_df = pd.DataFrame(recovery_points)
    rec_df["date"] = _date_only(rec_df["date"])
    metric_options = {
        "Sen [h]": "sleep_hours",
        "Objętość [kg]": "volume_kg",
        "RPE średnie": "rpe_avg",
        "1RM [kg]": "one_rm_kg",
        "Δ 1RM": "one_rm_delta",
    }
    selected_metrics = st.multiselect(
        "Metryki na wykresie (max 3)",
        options=list(metric_options.keys()),
        default=["Sen [h]", "Objętość [kg]"],
        max_selections=3,
    )
    if not selected_metrics:
        st.info("Wybierz co najmniej jedną metrykę.")
    else:
        long_rows: list[dict[str, Any]] = []
        for _, row in rec_df.iterrows():
            for label in selected_metrics:
                col = metric_options[label]
                value = row.get(col)
                if pd.isna(value):
                    value = None
                long_rows.append(
                    {
                        "date": row["date"],
                        "metric": label,
                        "value": value,
                    }
                )
        long_df = pd.DataFrame(long_rows)
        fig_rec = px.line(
            long_df,
            x="date",
            y="value",
            color="metric",
            markers=True,
            labels={"date": "Data", "value": "Wartość", "metric": "Metryka"},
        )
        fig_rec.update_traces(connectgaps=False)
        _apply_date_axis(fig_rec)
        st.plotly_chart(fig_rec, use_container_width=True)
