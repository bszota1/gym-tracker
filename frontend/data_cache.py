from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st
from api_client import (
    get_body_weight_analytics,
    get_daily_metric,
    get_one_rm_analytics,
    get_overview,
    get_recovery,
    get_session,
    get_strength_vs_weight,
    list_daily_metrics,
    list_exercises,
    list_session_sets,
    list_sessions,
)
from api_errors import ApiNotFoundError

_CACHE_TTL_SECONDS = 30


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False)
def cached_list_exercises(is_active: bool | None = None) -> list[dict[str, Any]]:
    return list_exercises(is_active=is_active)


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False)
def cached_list_daily_metrics(
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict[str, Any]]:
    return list_daily_metrics(date_from=date_from, date_to=date_to)


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False)
def cached_get_daily_metric(metric_date: str) -> dict[str, Any] | None:
    try:
        return get_daily_metric(metric_date)
    except ApiNotFoundError:
        return None


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False)
def cached_list_sessions(
    date_from: str | None = None,
    date_to: str | None = None,
    split_type: str | None = None,
) -> list[dict[str, Any]]:
    return list_sessions(
        date_from=date_from,
        date_to=date_to,
        split_type=split_type,
    )


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False)
def cached_get_session(session_id: int) -> dict[str, Any]:
    return get_session(session_id)


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False)
def cached_list_session_sets(session_id: int) -> list[dict[str, Any]]:
    return list_session_sets(session_id)


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False)
def cached_body_weight_analytics(date_from: str, date_to: str) -> dict[str, Any]:
    return get_body_weight_analytics(date_from, date_to)


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False)
def cached_one_rm_analytics(
    exercise_id: int,
    date_from: str,
    date_to: str,
) -> dict[str, Any]:
    return get_one_rm_analytics(
        exercise_id=exercise_id,
        date_from=date_from,
        date_to=date_to,
    )


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False)
def cached_strength_vs_weight(
    exercise_id: int,
    date_from: str,
    date_to: str,
) -> dict[str, Any]:
    return get_strength_vs_weight(
        exercise_id=exercise_id,
        date_from=date_from,
        date_to=date_to,
    )


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False)
def cached_recovery(
    date_from: str,
    date_to: str,
    exercise_id: int | None = None,
) -> dict[str, Any]:
    return get_recovery(date_from, date_to, exercise_id=exercise_id)


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False)
def cached_overview(as_of: str | None = None) -> dict[str, Any]:
    return get_overview(as_of=as_of)


def invalidate_analytics_cache() -> None:
    cached_body_weight_analytics.clear()
    cached_one_rm_analytics.clear()
    cached_strength_vs_weight.clear()
    cached_recovery.clear()
    cached_overview.clear()


def invalidate_metrics_cache() -> None:
    cached_list_daily_metrics.clear()
    cached_get_daily_metric.clear()
    invalidate_analytics_cache()


def invalidate_exercises_cache() -> None:
    cached_list_exercises.clear()
    invalidate_analytics_cache()


def invalidate_workout_cache() -> None:
    cached_list_sessions.clear()
    cached_get_session.clear()
    cached_list_session_sets.clear()
    invalidate_analytics_cache()


def invalidate_all_reads() -> None:
    invalidate_metrics_cache()
    invalidate_exercises_cache()
    invalidate_workout_cache()
    invalidate_analytics_cache()


def as_cache_date(value: date | str) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return value
