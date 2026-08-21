"""Create the V1 product schema and pgvector-backed group memory.

Revision ID: 20260821_0001
Revises:
Create Date: 2026-08-21 00:00:00
"""

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260821_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())
TIMESTAMP = sa.DateTime(timezone=True)


def utcnow() -> sa.TextClause:
    return sa.text("timezone('utc', now())")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    group_role = postgresql.ENUM("OWNER", "ADMIN", "MEMBER", "VIEWER", name="group_role")

    op.create_table(
        "users",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("preferences", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", TIMESTAMP, nullable=False, server_default=utcnow()),
        sa.Column("updated_at", TIMESTAMP, nullable=False, server_default=utcnow()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "identity_accounts",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("issuer", sa.String(500), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("email_at_link", sa.String(320), nullable=True),
        sa.Column("claims", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", TIMESTAMP, nullable=False, server_default=utcnow()),
        sa.UniqueConstraint("issuer", "subject", name="uq_identity_accounts_issuer_subject"),
    )
    op.create_index("ix_identity_accounts_user_id", "identity_accounts", ["user_id"])

    op.create_table(
        "groups",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("settings", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", TIMESTAMP, nullable=False, server_default=utcnow()),
        sa.Column("updated_at", TIMESTAMP, nullable=False, server_default=utcnow()),
    )
    op.create_index("ix_groups_created_by", "groups", ["created_by"])

    op.create_table(
        "group_memberships",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("group_id", UUID, sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", group_role, nullable=False),
        sa.Column("created_at", TIMESTAMP, nullable=False, server_default=utcnow()),
        sa.Column("updated_at", TIMESTAMP, nullable=False, server_default=utcnow()),
        sa.UniqueConstraint("group_id", "user_id", name="uq_group_memberships_group_user"),
    )
    op.create_index("ix_group_memberships_user_id", "group_memberships", ["user_id"])

    op.create_table(
        "threads",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("group_id", UUID, sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("archived_at", TIMESTAMP, nullable=True),
        sa.Column("created_at", TIMESTAMP, nullable=False, server_default=utcnow()),
        sa.Column("updated_at", TIMESTAMP, nullable=False, server_default=utcnow()),
    )
    op.create_index("ix_threads_group_id_created_at", "threads", ["group_id", "created_at"])

    op.create_table(
        "messages",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("thread_id", UUID, sa.ForeignKey("threads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("author_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("author_kind", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", TIMESTAMP, nullable=False, server_default=utcnow()),
        sa.UniqueConstraint("thread_id", "sequence_number", name="uq_messages_thread_sequence"),
    )
    op.create_index("ix_messages_thread_id_created_at", "messages", ["thread_id", "created_at"])

    op.create_table(
        "group_memories",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("group_id", UUID, sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_thread_id", UUID, sa.ForeignKey("threads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_message_id", UUID, sa.ForeignKey("messages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.Text(), nullable=False),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", TIMESTAMP, nullable=False, server_default=utcnow()),
        sa.Column("updated_at", TIMESTAMP, nullable=False, server_default=utcnow()),
    )
    # `vector(1536)` fixes the V1 embedding contract and permits a cosine index.
    op.execute("ALTER TABLE group_memories ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector")
    op.create_index("ix_group_memories_group_id_status", "group_memories", ["group_id", "status"])
    op.execute(
        "CREATE INDEX ix_group_memories_embedding_cosine ON group_memories "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "channel_identities",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("external_subject", sa.String(500), nullable=False),
        sa.Column("linked_at", TIMESTAMP, nullable=False, server_default=utcnow()),
        sa.Column("last_seen_at", TIMESTAMP, nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.UniqueConstraint("provider", "external_subject", name="uq_channel_identities_provider_subject"),
    )
    op.create_index("ix_channel_identities_user_id", "channel_identities", ["user_id"])

    op.create_table(
        "hermes_profile_bindings",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("group_id", UUID, sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=True),
        sa.Column("hermes_profile_id", sa.String(255), nullable=False),
        sa.Column("binding_kind", sa.String(32), nullable=False),
        sa.Column("created_at", TIMESTAMP, nullable=False, server_default=utcnow()),
        sa.CheckConstraint(
            "(user_id IS NOT NULL AND group_id IS NULL) OR (user_id IS NULL AND group_id IS NOT NULL)",
            name="ck_hermes_profile_bindings_exactly_one_scope",
        ),
        sa.UniqueConstraint("hermes_profile_id", name="uq_hermes_profile_bindings_profile_id"),
    )

    op.create_table(
        "capability_permissions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("group_id", UUID, sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("resource_kind", sa.String(32), nullable=False),
        sa.Column("resource_key", sa.String(500), nullable=False),
        sa.Column("effect", sa.String(16), nullable=False),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", TIMESTAMP, nullable=False, server_default=utcnow()),
        sa.CheckConstraint("group_id IS NOT NULL OR user_id IS NOT NULL", name="ck_capability_permissions_has_scope"),
        sa.CheckConstraint("effect IN ('ALLOW', 'DENY')", name="ck_capability_permissions_effect"),
    )
    op.create_index("ix_capability_permissions_group_id", "capability_permissions", ["group_id"])
    op.create_index("ix_capability_permissions_user_id", "capability_permissions", ["user_id"])

    op.create_table(
        "approval_requests",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("group_id", UUID, sa.ForeignKey("groups.id", ondelete="SET NULL"), nullable=True),
        sa.Column("thread_id", UUID, sa.ForeignKey("threads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("requested_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approval_kind", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("request_payload", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("decided_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("decided_at", TIMESTAMP, nullable=True),
        sa.Column("expires_at", TIMESTAMP, nullable=True),
        sa.Column("created_at", TIMESTAMP, nullable=False, server_default=utcnow()),
        sa.CheckConstraint("status IN ('PENDING', 'APPROVED', 'REJECTED', 'EXPIRED', 'CANCELLED')", name="ck_approval_requests_status"),
    )
    op.create_index("ix_approval_requests_group_id_status", "approval_requests", ["group_id", "status"])

    op.create_table(
        "audit_events",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("actor_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("group_id", UUID, sa.ForeignKey("groups.id", ondelete="SET NULL"), nullable=True),
        sa.Column("thread_id", UUID, sa.ForeignKey("threads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("payload", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", TIMESTAMP, nullable=False, server_default=utcnow()),
    )
    op.create_index("ix_audit_events_group_id_created_at", "audit_events", ["group_id", "created_at"])
    op.create_index("ix_audit_events_actor_user_id_created_at", "audit_events", ["actor_user_id", "created_at"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("approval_requests")
    op.drop_table("capability_permissions")
    op.drop_table("hermes_profile_bindings")
    op.drop_table("channel_identities")
    op.execute("DROP INDEX IF EXISTS ix_group_memories_embedding_cosine")
    op.drop_table("group_memories")
    op.drop_table("messages")
    op.drop_table("threads")
    op.drop_table("group_memberships")
    op.drop_table("groups")
    op.drop_table("identity_accounts")
    op.drop_table("users")
    postgresql.ENUM(name="group_role").drop(op.get_bind(), checkfirst=True)
