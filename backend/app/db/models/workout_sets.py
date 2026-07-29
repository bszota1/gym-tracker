from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base, TimestampMixin


class WorkoutSet(TimestampMixin, Base):
    __tablename__ = "workout_sets"
    __table_args__ = (
        CheckConstraint("set_number >= 1", name="set_number_min"),
        CheckConstraint(
            "weight_kg >= 0 AND weight_kg <= 1000",
            name="weight_kg_range",
        ),
        CheckConstraint("reps >= 1 AND reps <= 100", name="reps_range"),
        CheckConstraint(
            "rpe IS NULL OR (rpe >= 1 AND rpe <= 10 AND (rpe * 2) = CAST(rpe * 2 AS INTEGER))",
            name="rpe_range_step",
        ),
        UniqueConstraint(
            "session_id",
            "exercise_id",
            "set_number",
            name="uq_set_order",
        ),
        Index("ix_sets_session_id", "session_id"),
        Index("ix_sets_exercise_id", "exercise_id"),
        Index("ix_sets_exercise_created", "exercise_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("workout_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="RESTRICT"),
        nullable=False,
    )
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    reps: Mapped[int] = mapped_column(Integer, nullable=False)
    rpe: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    is_warmup: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    calculated_1rm: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
