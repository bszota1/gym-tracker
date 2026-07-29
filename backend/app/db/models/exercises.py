from sqlalchemy import Boolean, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class Exercise(Base):
    __tablename__ = "exercises"
    __table_args__ = (
        Index(
            "uq_exercises_name_lower",
            func.lower(text("name")),
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    muscle_group: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
