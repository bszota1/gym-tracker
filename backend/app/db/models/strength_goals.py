from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class StrengthGoal(Base):
    __tablename__ = "strength_goals"
    __table_args__ = (
        CheckConstraint("target_1rm_kg > 0 AND target_1rm_kg <= 1000", name="target_1rm_kg_range"),
        CheckConstraint(
            "status IN ('ACTIVE', 'ACHIEVED', 'ARCHIVED')",
            name="strength_goal_status_allowed",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_1rm_kg: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
