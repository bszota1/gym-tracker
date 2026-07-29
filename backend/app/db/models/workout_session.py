from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base, TimestampMixin


class WorkoutSession(TimestampMixin, Base):
    __tablename__ = "workout_sessions"
    __table_args__ = (
        CheckConstraint(
            "split_type IN ('PUSH', 'PULL', 'LEGS', 'OTHER')",
            name="split_type_allowed",
        ),
        Index("ix_sessions_workout_date", "workout_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    workout_date: Mapped[date] = mapped_column(
        Date,
        ForeignKey("daily_metrics.metric_date", ondelete="RESTRICT"),
        nullable=False,
    )
    split_type: Mapped[str] = mapped_column(String(10), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
