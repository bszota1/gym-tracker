from datetime import UTC, date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class AlertFeedback(Base):
    __tablename__ = "alert_feedback"
    __table_args__ = (
        CheckConstraint(
            "rating IN ('USEFUL', 'NOT_USEFUL')",
            name="alert_feedback_rating_allowed",
        ),
        UniqueConstraint(
            "exercise_id",
            "alert_date",
            "model_run_id",
            name="uq_alert_feedback_exercise_date_run",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"),
        nullable=False,
    )
    alert_date: Mapped[date] = mapped_column(Date, nullable=False)
    model_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("model_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)
    feature_pipeline_version: Mapped[str] = mapped_column(String(20), nullable=False)
    threshold_version: Mapped[str] = mapped_column(String(20), nullable=False)
    rating: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
