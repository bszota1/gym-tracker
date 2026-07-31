"""add alert_feedback

Revision ID: a1b2c3d4e5f6
Revises: 8ca3cc32c6ca
Create Date: 2026-07-31
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "8ca3cc32c6ca"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alert_feedback",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("alert_date", sa.Date(), nullable=False),
        sa.Column("model_run_id", sa.Integer(), nullable=True),
        sa.Column("model_type", sa.String(length=50), nullable=False),
        sa.Column("feature_pipeline_version", sa.String(length=20), nullable=False),
        sa.Column("threshold_version", sa.String(length=20), nullable=False),
        sa.Column("rating", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "rating IN ('USEFUL', 'NOT_USEFUL')",
            name=op.f("ck_alert_feedback_alert_feedback_rating_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
            name=op.f("fk_alert_feedback_exercise_id_exercises"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["model_run_id"],
            ["model_runs.id"],
            name=op.f("fk_alert_feedback_model_run_id_model_runs"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alert_feedback")),
        sa.UniqueConstraint(
            "exercise_id",
            "alert_date",
            "model_run_id",
            name="uq_alert_feedback_exercise_date_run",
        ),
    )


def downgrade() -> None:
    op.drop_table("alert_feedback")
