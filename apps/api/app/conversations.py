from datetime import datetime, timezone
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import DateTime, Enum, Integer, String, Text, column, func, select, table
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID, insert
from sqlalchemy.ext.asyncio import AsyncSession


group_role = Enum("OWNER", "ADMIN", "MEMBER", "VIEWER", name="group_role")
groups = table(
    "groups",
    column("id", PG_UUID(as_uuid=True)), column("name", String(200)),
    column("description", Text), column("created_by", PG_UUID(as_uuid=True)),
    column("settings", JSONB), column("created_at", DateTime(timezone=True)),
    column("updated_at", DateTime(timezone=True)),
)
memberships = table(
    "group_memberships",
    column("id", PG_UUID(as_uuid=True)), column("group_id", PG_UUID(as_uuid=True)),
    column("user_id", PG_UUID(as_uuid=True)), column("role", group_role),
    column("created_at", DateTime(timezone=True)), column("updated_at", DateTime(timezone=True)),
)
threads = table(
    "threads",
    column("id", PG_UUID(as_uuid=True)), column("group_id", PG_UUID(as_uuid=True)),
    column("title", String(300)), column("created_by", PG_UUID(as_uuid=True)),
    column("archived_at", DateTime(timezone=True)),
    column("created_at", DateTime(timezone=True)), column("updated_at", DateTime(timezone=True)),
)
messages = table(
    "messages",
    column("id", PG_UUID(as_uuid=True)), column("thread_id", PG_UUID(as_uuid=True)),
    column("sequence_number", Integer), column("author_user_id", PG_UUID(as_uuid=True)),
    column("author_kind", String(32)), column("content", Text), column("metadata", JSONB),
    column("created_at", DateTime(timezone=True)),
)


def personal_context_ids(user_id: UUID) -> tuple[UUID, UUID, UUID]:
    group_id = uuid5(NAMESPACE_URL, f"skavan:user:{user_id}:personal-group")
    membership_id = uuid5(NAMESPACE_URL, f"skavan:user:{user_id}:personal-membership")
    thread_id = uuid5(NAMESPACE_URL, f"skavan:user:{user_id}:personal-thread")
    return group_id, membership_id, thread_id


async def ensure_personal_thread(session: AsyncSession, user_id: UUID) -> UUID:
    group_id, membership_id, thread_id = personal_context_ids(user_id)
    now = datetime.now(timezone.utc)
    await session.execute(
        insert(groups).values(
            id=group_id, name="Personal", description="Private personal workspace",
            created_by=user_id, settings={"kind": "personal"}, created_at=now, updated_at=now,
        ).on_conflict_do_nothing(index_elements=[groups.c.id])
    )
    await session.execute(
        insert(memberships).values(
            id=membership_id, group_id=group_id, user_id=user_id, role="OWNER",
            created_at=now, updated_at=now,
        ).on_conflict_do_nothing(index_elements=[memberships.c.id])
    )
    await session.execute(
        insert(threads).values(
            id=thread_id, group_id=group_id, title="General", created_by=user_id,
            archived_at=None, created_at=now, updated_at=now,
        ).on_conflict_do_nothing(index_elements=[threads.c.id])
    )
    await session.commit()
    return thread_id


async def append_message(
    session: AsyncSession,
    *,
    thread_id: UUID,
    author_kind: str,
    content: str,
    author_user_id: UUID | None = None,
) -> UUID:
    await session.execute(select(threads.c.id).where(threads.c.id == thread_id).with_for_update())
    next_sequence = (
        await session.execute(
            select(func.coalesce(func.max(messages.c.sequence_number), 0) + 1)
            .where(messages.c.thread_id == thread_id)
        )
    ).scalar_one()
    message_id = uuid4()
    await session.execute(
        insert(messages).values(
            id=message_id, thread_id=thread_id, sequence_number=next_sequence,
            author_user_id=author_user_id, author_kind=author_kind, content=content,
            metadata={}, created_at=datetime.now(timezone.utc),
        )
    )
    await session.commit()
    return message_id


async def load_messages(session: AsyncSession, thread_id: UUID, limit: int = 100) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            select(
                messages.c.id, messages.c.author_kind, messages.c.content, messages.c.created_at,
                messages.c.sequence_number,
            )
            .where(messages.c.thread_id == thread_id)
            .order_by(messages.c.sequence_number.desc())
            .limit(limit)
        )
    ).all()
    return [
        {
            "id": str(row.id),
            "role": "user" if row.author_kind == "USER" else "assistant",
            "content": row.content,
            "created_at": row.created_at,
        }
        for row in reversed(rows)
    ]
