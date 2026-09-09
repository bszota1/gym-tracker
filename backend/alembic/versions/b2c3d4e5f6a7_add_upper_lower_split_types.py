"""add upper lower split types

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-03
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("workout_sessions", schema=None) as batch_op:
        batch_op.drop_constraint(
            op.f("ck_workout_sessions_split_type_allowed"),
            type_="check",
        )
        batch_op.create_check_constraint(
            op.f("ck_workout_sessions_split_type_allowed"),
            "split_type IN ('PUSH', 'PULL', 'LEGS', 'UPPER', 'LOWER', 'OTHER')",
        )


def downgrade() -> None:
    with op.batch_alter_table("workout_sessions", schema=None) as batch_op:
        batch_op.drop_constraint(
            op.f("ck_workout_sessions_split_type_allowed"),
            type_="check",
        )
        batch_op.create_check_constraint(
            op.f("ck_workout_sessions_split_type_allowed"),
            "split_type IN ('PUSH', 'PULL', 'LEGS', 'OTHER')",
        )
