"""Bind Skavan chat threads to persistent Hermes sessions.

Revision ID: 20260825_0002
Revises: 20260821_0001
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260825_0002"
down_revision: str | None = "20260821_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "threads",
        sa.Column("hermes_session_id", sa.String(length=255), nullable=True),
    )
    op.create_unique_constraint(
        "uq_threads_hermes_session_id", "threads", ["hermes_session_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_threads_hermes_session_id", "threads", type_="unique")
    op.drop_column("threads", "hermes_session_id")
