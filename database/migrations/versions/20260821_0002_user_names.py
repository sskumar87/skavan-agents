"""Store structured user names from the identity provider.

Revision ID: 20260821_0002
Revises: 20260821_0001
Create Date: 2026-08-21 00:00:00
"""

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260821_0002"
down_revision: Union[str, Sequence[str], None] = "20260821_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("given_name", sa.String(200), nullable=True))
    op.add_column("users", sa.Column("family_name", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "family_name")
    op.drop_column("users", "given_name")
