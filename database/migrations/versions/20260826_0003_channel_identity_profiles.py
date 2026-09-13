"""Add profile-scoped messaging identity grants.

Revision ID: 20260826_0003
Revises: 20260825_0002
Create Date: 2026-08-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


revision: str = "20260826_0003"
down_revision: str | None = "20260825_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "channel_identity_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "channel_identity_id", UUID(as_uuid=True),
            sa.ForeignKey("channel_identities.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("profile_key", sa.String(length=32), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("profile_key IN ('personal', 'work')", name="ck_channel_identity_profiles_profile"),
        sa.UniqueConstraint(
            "channel_identity_id", "profile_key",
            name="uq_channel_identity_profiles_identity_profile",
        ),
    )
    op.create_index(
        "ix_channel_identity_profiles_profile_key",
        "channel_identity_profiles", ["profile_key"],
    )


def downgrade() -> None:
    op.drop_table("channel_identity_profiles")
