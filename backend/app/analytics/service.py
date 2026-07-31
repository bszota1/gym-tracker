from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.analytics.queries import AnalyticsQueries
from backend.app.analytics.transforms import (
    body_weight_series,
    daily_one_rm_series,
    recovery_series,
    strength_vs_weight,
)
from backend.app.core.exceptions import AppError
from backend.app.domain.analytics_defs import (
    ANALYTICS_SEMANTICS_VERSION,
    BODY_WEIGHT_TARGET_KG,
    INCLUDE_WARMUPS_IN_VOLUME,
    MAX_REPS_FOR_STRENGTH_TREND,
    OVERVIEW_METRICS_WINDOW_DAYS,
    ROLLING_WINDOW_DAYS,
)


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self._queries = AnalyticsQueries(session)

    def _validate_range(self, date_from: date, date_to: date) -> None:
        if date_from > date_to:
            raise AppError(
                "date_from must be less than or equal to date_to",
                code="VALIDATION_ERROR",
                status_code=422,
            )

    def _base_meta(self, date_from: date, date_to: date, **extra: Any) -> dict[str, Any]:
        meta: dict[str, Any] = {
            "date_from": date_from,
            "date_to": date_to,
            "semantics_version": ANALYTICS_SEMANTICS_VERSION,
            "rolling_window_days": ROLLING_WINDOW_DAYS,
        }
        meta.update(extra)
        return meta

    async def body_weight_trend(self, date_from: date, date_to: date) -> dict[str, Any]:
        self._validate_range(date_from, date_to)
        rows = await self._queries.fetch_body_weight_rows(date_from, date_to)
        payload = body_weight_series(rows)
        rolling = payload.pop("rolling_window_days", ROLLING_WINDOW_DAYS)
        payload["meta"] = self._base_meta(
            date_from,
            date_to,
            rolling_window_days=rolling,
            units={"body_weight_kg": "kg"},
        )
        return payload

    async def one_rm_trend(
        self,
        date_from: date,
        date_to: date,
        exercise_id: int,
    ) -> dict[str, Any]:
        self._validate_range(date_from, date_to)
        rows = await self._queries.fetch_set_rows_for_strength(
            date_from=date_from,
            date_to=date_to,
            exercise_id=exercise_id,
        )
        payload = daily_one_rm_series(rows)
        rolling = payload.pop("rolling_window_days", ROLLING_WINDOW_DAYS)
        payload["meta"] = self._base_meta(
            date_from,
            date_to,
            rolling_window_days=rolling,
            exercise_id=exercise_id,
            max_reps_for_trend=MAX_REPS_FOR_STRENGTH_TREND,
            exclude_warmups=True,
            units={"one_rm_kg": "kg"},
        )
        return payload

    async def strength_vs_body_weight(
        self,
        date_from: date,
        date_to: date,
        exercise_id: int,
    ) -> dict[str, Any]:
        self._validate_range(date_from, date_to)
        weight_rows = await self._queries.fetch_body_weight_rows(date_from, date_to)
        set_rows = await self._queries.fetch_set_rows_for_strength(
            date_from=date_from,
            date_to=date_to,
            exercise_id=exercise_id,
        )
        weight = body_weight_series(weight_rows)
        one_rm = daily_one_rm_series(set_rows)
        points = strength_vs_weight(one_rm["points"], weight["points"])
        return {
            "points": points,
            "meta": self._base_meta(
                date_from,
                date_to,
                exercise_id=exercise_id,
                units={
                    "one_rm_kg": "kg",
                    "body_weight_kg": "kg",
                },
            ),
        }

    async def recovery(
        self,
        date_from: date,
        date_to: date,
        exercise_id: int | None = None,
    ) -> dict[str, Any]:
        self._validate_range(date_from, date_to)
        metric_rows = await self._queries.fetch_daily_metric_rows(date_from, date_to)
        set_rows = await self._queries.fetch_set_rows_for_strength(
            date_from=date_from,
            date_to=date_to,
            exercise_id=exercise_id,
        )
        one_rm_points = None
        if exercise_id is not None:
            one_rm_points = daily_one_rm_series(set_rows)["points"]

        points = recovery_series(
            metric_rows,
            set_rows,
            one_rm_points=one_rm_points,
        )
        return {
            "points": points,
            "meta": self._base_meta(
                date_from,
                date_to,
                exercise_id=exercise_id,
                include_warmups_in_volume=INCLUDE_WARMUPS_IN_VOLUME,
                note=(
                    "Co-occurrence of sleep, RPE, volume and 1RM changes "
                    "does not imply causation."
                ),
                units={
                    "sleep_hours": "h",
                    "volume_kg": "kg",
                    "one_rm_kg": "kg",
                    "rpe_avg": "RPE",
                },
            ),
        }

    async def overview(self, *, as_of: date | None = None) -> dict[str, Any]:
        today = as_of or date.today()
        window_from = today - timedelta(days=OVERVIEW_METRICS_WINDOW_DAYS - 1)
        week_from = today - timedelta(days=today.weekday())

        weight_rows = await self._queries.fetch_body_weight_rows(
            date_from=today - timedelta(days=365),
            date_to=today,
        )
        weight = body_weight_series(weight_rows)
        last_weight = weight["points"][-1] if weight["points"] else None

        metric_rows = await self._queries.fetch_daily_metric_rows(window_from, today)
        calories_values: list[int] = []
        sleep_values: list[float] = []
        for row in metric_rows:
            mapping = row._mapping if hasattr(row, "_mapping") else None
            calories = mapping["calories_kcal"] if mapping else row[2]
            sleep = mapping["sleep_hours"] if mapping else row[3]
            if calories is not None:
                calories_values.append(int(calories))
            if sleep is not None:
                sleep_values.append(float(sleep))

        sessions = await self._queries.fetch_session_dates(week_from, today)

        last_weight_value = last_weight["body_weight_kg"] if last_weight else None
        last_weight_as_of = last_weight["date"] if last_weight else None
        delta_to_target = None
        if last_weight_value is not None:
            delta_to_target = float(BODY_WEIGHT_TARGET_KG) - float(last_weight_value)

        return {
            "body_weight": {
                "value": last_weight_value,
                "as_of": last_weight_as_of,
            },
            "delta_to_target_kg": {
                "value": delta_to_target,
                "target_kg": BODY_WEIGHT_TARGET_KG,
                "as_of": last_weight_as_of,
            },
            "avg_calories_kcal": {
                "value": (
                    sum(calories_values) / len(calories_values)
                    if calories_values
                    else None
                ),
                "as_of": today,
                "window_from": window_from,
                "window_to": today,
                "sample_size": len(calories_values),
            },
            "avg_sleep_hours": {
                "value": (
                    sum(sleep_values) / len(sleep_values) if sleep_values else None
                ),
                "as_of": today,
                "window_from": window_from,
                "window_to": today,
                "sample_size": len(sleep_values),
            },
            "sessions_this_week": {
                "value": len(sessions),
                "as_of": today,
                "window_from": week_from,
                "window_to": today,
            },
            "meta": {
                "as_of": today,
                "semantics_version": ANALYTICS_SEMANTICS_VERSION,
                "metrics_window_days": OVERVIEW_METRICS_WINDOW_DAYS,
                "body_weight_target_kg": BODY_WEIGHT_TARGET_KG,
                "units": {
                    "body_weight": "kg",
                    "delta_to_target_kg": "kg",
                    "avg_calories_kcal": "kcal",
                    "avg_sleep_hours": "h",
                    "sessions_this_week": "count",
                },
            },
        }
