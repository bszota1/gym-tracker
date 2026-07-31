from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from api_client import (
    create_alert_feedback,
    create_strength_goal,
    get_model_status,
    get_one_rm_analytics,
    get_strength_forecast,
    get_weight_suggestion,
    list_anomalies,
    list_exercises,
    list_strength_goals,
    train_anomaly_model,
    train_forecast_model,
    update_strength_goal,
)
from api_errors import ApiClientError, ApiNotFoundError, ApiValidationError
from ui import check_api_available, configure_page, empty_state, show_api_error

MODEL_FORECAST = "prophet_one_rm"
MODEL_ANOMALY = "isolation_forest_one_rm"

configure_page("Cele i modele", layout="wide")
st.title("Cele i modele")

if not check_api_available():
    st.warning("Najpierw uruchom API (`make run-api`).")
    st.stop()


def _freshness_label(status: str | None) -> str:
    if status is None:
        return "brak modelu"
    mapping = {
        "FRESH": "aktualny",
        "STALE_DATA": "nieaktualny (zmiana danych)",
        "STALE_AGE": "nieaktualny (wiek modelu)",
    }
    return mapping.get(status, status)


try:
    exercises = [item for item in list_exercises(is_active=True)]
except ApiClientError as exc:
    show_api_error(exc)
    st.stop()

if not exercises:
    empty_state(
        "Brak aktywnych ćwiczeń.",
        next_step="Dodaj ćwiczenie na stronie Ćwiczenia.",
    )
    st.stop()

labels = {f"{item['name']} (#{item['id']})": item["id"] for item in exercises}
choice = st.selectbox("Ćwiczenie", options=list(labels.keys()))
exercise_id = labels[choice]

tab_goals, tab_forecast, tab_anomalies, tab_weight = st.tabs(
    ["Cele 1RM", "Prognoza", "Anomalie", "Sugestia ciężaru"]
)

with tab_goals:
    st.subheader("Cel siłowy")
    with st.form("create_goal"):
        target = st.number_input("Target 1RM (kg)", min_value=1.0, value=120.0, step=2.5)
        use_target_date = st.checkbox("Ustaw planowaną datę użytkownika")
        target_date = st.date_input("Planowana data") if use_target_date else None
        submitted = st.form_submit_button("Zapisz cel")
        if submitted:
            try:
                create_strength_goal(
                    exercise_id=exercise_id,
                    target_1rm_kg=target,
                    target_date=target_date if isinstance(target_date, date) else None,
                )
                st.success("Cel zapisany (poprzedni ACTIVE został zarchiwizowany).")
            except ApiClientError as exc:
                show_api_error(exc)

    try:
        goals = list_strength_goals(exercise_id=exercise_id)
    except ApiClientError as exc:
        show_api_error(exc)
        goals = []

    if not goals:
        empty_state("Brak celów dla tego ćwiczenia.")
    else:
        st.dataframe(pd.DataFrame(goals), use_container_width=True, hide_index=True)
        active = [goal for goal in goals if goal.get("status") == "ACTIVE"]
        if active and st.button("Archiwizuj aktywny cel"):
            try:
                update_strength_goal(active[0]["id"], status="ARCHIVED")
                st.rerun()
            except ApiClientError as exc:
                show_api_error(exc)

with tab_forecast:
    st.subheader("Prognoza celu")
    status_box = st.empty()
    try:
        forecast_status = get_model_status(
            exercise_id=exercise_id,
            model_type=MODEL_FORECAST,
        )
        status_box.info(
            "Świeżość modelu: "
            f"**{_freshness_label(forecast_status.get('freshness'))}** | "
            f"próbki treningu: {forecast_status.get('sample_count')} | "
            f"trained_at: {forecast_status.get('trained_at') or '—'} | "
            f"usunięty automatycznie: {forecast_status.get('deleted')}"
        )
        if forecast_status.get("warnings"):
            st.caption("Ostrzeżenia: " + ", ".join(forecast_status["warnings"]))
    except ApiClientError as exc:
        show_api_error(exc)

    if st.button("Trenuj model prognozy (ręcznie)", key="train_forecast"):
        with st.spinner("Trening Prophet…"):
            try:
                result = train_forecast_model(exercise_id=exercise_id)
                if result.get("accepted"):
                    st.success(f"Model zaakceptowany (run #{result['model_run_id']}).")
                else:
                    st.warning(
                        "Model odrzucony vs baseline. "
                        f"Zachowano poprzedni dobry model: {result.get('kept_previous_model')}"
                    )
            except ApiValidationError as exc:
                empty_state(exc.user_message(), next_step="Dodaj więcej sesji siłowych.")
            except ApiClientError as exc:
                show_api_error(exc)

    goals = list_strength_goals(exercise_id=exercise_id)
    goal_options = {
        f"#{goal['id']} {goal['target_1rm_kg']} kg ({goal['status']})": goal["id"]
        for goal in goals
    }
    if not goal_options:
        empty_state("Najpierw utwórz cel 1RM.")
    else:
        goal_label = st.selectbox("Cel do prognozy", options=list(goal_options.keys()))
        goal_id = goal_options[goal_label]
        try:
            one_rm = get_one_rm_analytics(
                exercise_id=exercise_id,
                date_from=date(1970, 1, 1),
                date_to=date.today(),
            )
            forecast = get_strength_forecast(exercise_id=exercise_id, goal_id=goal_id)
            points = one_rm.get("points") or []
            fig = go.Figure()
            if points:
                fig.add_trace(
                    go.Scatter(
                        x=[point["date"] for point in points],
                        y=[point["one_rm_kg"] for point in points],
                        mode="lines+markers",
                        name="1RM historia",
                    )
                )
            target_value = float(forecast["target_1rm_kg"])
            fig.add_hline(y=target_value, line_dash="dash", annotation_text="target")
            if forecast.get("crossing_date"):
                fig.add_vline(
                    x=forecast["crossing_date"],
                    line_dash="dot",
                    annotation_text="prognoza",
                )
            if forecast.get("crossing_date_lower"):
                fig.add_vline(
                    x=forecast["crossing_date_lower"],
                    line_dash="dot",
                    annotation_text="dolny",
                )
            if forecast.get("crossing_date_upper"):
                fig.add_vline(
                    x=forecast["crossing_date_upper"],
                    line_dash="dot",
                    annotation_text="górny",
                )
            fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), height=420)
            st.plotly_chart(fig, use_container_width=True)

            st.write(
                {
                    "status": forecast.get("status"),
                    "crossing_date": forecast.get("crossing_date"),
                    "interval": [
                        forecast.get("crossing_date_upper"),
                        forecast.get("crossing_date_lower"),
                    ],
                    "trend": forecast.get("trend"),
                    "reason": forecast.get("reason"),
                    "sample_count": forecast.get("sample_count"),
                    "freshness": forecast.get("freshness"),
                    "trained_at": forecast.get("trained_at"),
                    "warnings": forecast.get("warnings"),
                }
            )
        except ApiValidationError as exc:
            empty_state(
                "Za mało danych do prognozy.",
                next_step=exc.user_message(),
            )
        except ApiNotFoundError:
            empty_state(
                "Brak wytrenowanego modelu prognozy.",
                next_step="Użyj przycisku treningu powyżej.",
            )
        except ApiClientError as exc:
            show_api_error(exc)

with tab_anomalies:
    st.subheader("Anomalie 1RM")
    try:
        anomaly_status = get_model_status(
            exercise_id=exercise_id,
            model_type=MODEL_ANOMALY,
        )
        st.info(
            "Świeżość: "
            f"**{_freshness_label(anomaly_status.get('freshness'))}** | "
            f"deleted={anomaly_status.get('deleted')}"
        )
    except ApiClientError as exc:
        show_api_error(exc)

    if st.button("Trenuj Isolation Forest (ręcznie)", key="train_anomaly"):
        with st.spinner("Trening anomalii…"):
            try:
                result = train_anomaly_model(exercise_id=exercise_id)
                st.success(f"Zapisano model anomalii (run #{result['model_run_id']}).")
            except ApiValidationError as exc:
                empty_state(exc.user_message())
            except ApiClientError as exc:
                show_api_error(exc)

    try:
        anomaly_payload = list_anomalies(exercise_id=exercise_id)
        points = anomaly_payload.get("points") or []
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=[point["date"] for point in points],
                y=[point["one_rm_kg"] for point in points],
                mode="lines+markers",
                name="1RM",
                customdata=[
                    "<br>".join(
                        (point.get("facts") or [])
                        + [f"założenie: {item}" for item in (point.get("assumptions") or [])]
                    )
                    for point in points
                ],
                hovertemplate="%{x}<br>1RM=%{y}<br>%{customdata}<extra></extra>",
            )
        )
        alert_points = [point for point in points if point.get("alert")]
        outlier_points = [
            point for point in points if point.get("is_outlier") and not point.get("alert")
        ]
        if outlier_points:
            fig.add_trace(
                go.Scatter(
                    x=[point["date"] for point in outlier_points],
                    y=[point["one_rm_kg"] for point in outlier_points],
                    mode="markers",
                    name="outlier (bez alertu)",
                    marker=dict(size=10, symbol="diamond"),
                )
            )
        if alert_points:
            fig.add_trace(
                go.Scatter(
                    x=[point["date"] for point in alert_points],
                    y=[point["one_rm_kg"] for point in alert_points],
                    mode="markers",
                    name="alert spadku",
                    marker=dict(size=12, symbol="x"),
                    text=[
                        f"{point.get('severity')}: {point.get('message')}"
                        for point in alert_points
                    ],
                    hovertemplate="%{x}<br>%{text}<extra></extra>",
                )
            )
        fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), height=420)
        st.plotly_chart(fig, use_container_width=True)

        if alert_points:
            st.write("Alerty:")
            for point in alert_points:
                st.markdown(
                    f"- **{point['date']}** [{point.get('severity')}] "
                    f"{point.get('message')}"
                )
                useful_col, not_col = st.columns(2)
                with useful_col:
                    if st.button(
                        f"Przydatny ({point['date']})",
                        key=f"useful_{point['date']}",
                    ):
                        try:
                            create_alert_feedback(
                                exercise_id=exercise_id,
                                alert_date=point["date"],
                                model_type=MODEL_ANOMALY,
                                rating="USEFUL",
                                model_run_id=anomaly_payload.get("model_run_id"),
                            )
                            st.success("Zapisano feedback.")
                        except ApiClientError as exc:
                            show_api_error(exc)
                with not_col:
                    if st.button(
                        f"Nieprzydatny ({point['date']})",
                        key=f"not_{point['date']}",
                    ):
                        try:
                            create_alert_feedback(
                                exercise_id=exercise_id,
                                alert_date=point["date"],
                                model_type=MODEL_ANOMALY,
                                rating="NOT_USEFUL",
                                model_run_id=anomaly_payload.get("model_run_id"),
                            )
                            st.success("Zapisano feedback.")
                        except ApiClientError as exc:
                            show_api_error(exc)
        else:
            st.caption("Brak alertów spadku (outlier ≠ automatyczny deload).")
    except ApiNotFoundError:
        empty_state(
            "Brak modelu anomalii.",
            next_step="Uruchom ręczny trening Isolation Forest.",
        )
    except ApiValidationError as exc:
        empty_state("Za mało danych do anomalii.", next_step=exc.user_message())
    except ApiClientError as exc:
        show_api_error(exc)

with tab_weight:
    st.subheader("Sugestia ciężaru")
    try:
        suggestion = get_weight_suggestion(exercise_id=exercise_id)
        if suggestion.get("status") == "INSUFFICIENT_DATA":
            empty_state(
                "Za mało kompletnych sesji do regresji ciężaru.",
                next_step="Potrzeba więcej treningów z RPE, snem i masą.",
            )
        else:
            st.metric(
                "Sugerowany ciężar",
                f"{suggestion.get('suggested_weight_kg')} kg",
            )
            st.caption(suggestion.get("disclaimer"))
            st.write(
                {
                    "status": suggestion.get("status"),
                    "last_successful_weight_kg": suggestion.get(
                        "last_successful_weight_kg"
                    ),
                    "raw_prediction_kg": suggestion.get("raw_prediction_kg"),
                    "clamped_±10%": suggestion.get("clamped"),
                    "rounded_down_to_plate": suggestion.get("rounded_down"),
                    "model_mae": suggestion.get("model_mae"),
                    "baseline_mae": suggestion.get("baseline_mae"),
                    "beats_baseline": suggestion.get("beats_baseline"),
                    "sample_count": suggestion.get("sample_count"),
                }
            )
    except ApiClientError as exc:
        show_api_error(exc)
