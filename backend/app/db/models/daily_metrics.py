from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base, TimestampMixin


class DailyMetric(TimestampMixin, Base):
    __tablename__ = "daily_metrics"
    __table_args__ = (
        CheckConstraint(
            "body_weight_kg IS NULL OR (body_weight_kg >= 30 AND body_weight_kg <= 300)",
            name="body_weight_kg_range",
        ),
        CheckConstraint(
            "calories_kcal IS NULL OR (calories_kcal >= 500 AND calories_kcal <= 10000)",
            name="calories_kcal_range",
        ),
        CheckConstraint(
            "sleep_hours IS NULL OR (sleep_hours >= 0 AND sleep_hours <= 24)",
            name="sleep_hours_range",
        ),
        CheckConstraint(
            "notes IS NULL OR length(notes) <= 2000",
            name="notes_length",
        ),
    )

    metric_date: Mapped[date] = mapped_column(Date, primary_key=True)
    body_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    calories_kcal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sleep_hours: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
