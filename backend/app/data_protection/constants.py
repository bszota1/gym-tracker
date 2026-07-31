from __future__ import annotations

EXPORT_SCHEMA_VERSION = "1"
BACKUP_RETENTION_COUNT = 10

EXPORT_TABLES: tuple[str, ...] = (
    "exercises",
    "daily_metrics",
    "workout_sessions",
    "workout_sets",
    "strength_goals",
)

DELETE_ORDER: tuple[str, ...] = (
    "workout_sets",
    "workout_sessions",
    "strength_goals",
    "daily_metrics",
    "exercises",
)
