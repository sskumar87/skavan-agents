from datetime import datetime, timezone
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import DateTime, Enum, Integer, String, Text, column, func, select, table, update
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID, insert
from sqlalchemy.ext.asyncio import AsyncSession


PROFILE_KEYS = {"personal", "work"}

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
users = table(
    "users",
    column("id", PG_UUID(as_uuid=True)), column("display_name", String(200)),
)


def personal_context_ids(user_id: UUID) -> tuple[UUID, UUID, UUID]:
    group_id = uuid5(NAMESPACE_URL, f"skavan:user:{user_id}:personal-group")
    membership_id = uuid5(NAMESPACE_URL, f"skavan:user:{user_id}:personal-membership")
    thread_id = uuid5(NAMESPACE_URL, f"skavan:user:{user_id}:personal-thread")
    return group_id, membership_id, thread_id


def profile_context_ids(profile: str) -> tuple[UUID, UUID]:
    if profile not in PROFILE_KEYS:
        raise ValueError("Unknown profile")
    group_id = uuid5(NAMESPACE_URL, f"skavan:profile:{profile}:workspace")
    thread_id = uuid5(NAMESPACE_URL, f"skavan:profile:{profile}:general-thread")
    return group_id, thread_id


async def ensure_profile_context(session: AsyncSession, user_id: UUID, profile: str) -> UUID:
    group_id, thread_id = profile_context_ids(profile)
    now = datetime.now(timezone.utc)
    display_name = profile.title()
    await session.execute(
        insert(groups).values(
            id=group_id, name=display_name,
            description=f"Shared {display_name} Hermes profile workspace",
            created_by=user_id,
            settings={"kind": "hermes_profile", "profile": profile},
            created_at=now, updated_at=now,
        ).on_conflict_do_nothing(index_elements=[groups.c.id])
    )
    await session.execute(
        insert(threads).values(
            id=thread_id, group_id=group_id, title="General", created_by=user_id,
            archived_at=None, created_at=now, updated_at=now,
        ).on_conflict_do_nothing(index_elements=[threads.c.id])
    )
    await session.commit()
    return thread_id


async def list_profile_threads(session: AsyncSession, profile: str) -> list[dict[str, Any]]:
    group_id, _ = profile_context_ids(profile)
    rows = (
        await session.execute(
            select(
                threads.c.id,
                threads.c.title,
                func.coalesce(func.max(messages.c.created_at), threads.c.created_at).label("last_active"),
            )
            .select_from(threads.outerjoin(messages, messages.c.thread_id == threads.c.id))
            .where(threads.c.group_id == group_id, threads.c.archived_at.is_(None))
            .group_by(threads.c.id, threads.c.title, threads.c.created_at)
            .order_by(func.coalesce(func.max(messages.c.created_at), threads.c.created_at).desc())
        )
    ).all()
    return [{"id": str(row.id), "title": row.title, "last_active": row.last_active} for row in rows]


async def create_profile_thread(
    session: AsyncSession, user_id: UUID, profile: str,
) -> dict[str, str]:
    group_id, _ = profile_context_ids(profile)
    thread_id = uuid4()
    now = datetime.now(timezone.utc)
    await session.execute(
        insert(threads).values(
            id=thread_id, group_id=group_id, title="New chat", created_by=user_id,
            archived_at=None, created_at=now, updated_at=now,
        )
    )
    await session.commit()
    return {"id": str(thread_id), "title": "New chat", "last_active": now}


async def rename_profile_thread(
    session: AsyncSession, profile: str, thread_id: UUID, title: str,
) -> dict[str, str]:
    group_id, _ = profile_context_ids(profile)
    row = (
        await session.execute(
            update(threads)
            .where(
                threads.c.id == thread_id,
                threads.c.group_id == group_id,
                threads.c.archived_at.is_(None),
            )
            .values(title=title, updated_at=datetime.now(timezone.utc))
            .returning(threads.c.id, threads.c.title)
        )
    ).one_or_none()
    if row is None:
        raise ValueError("Thread not found")
    await session.commit()
    return {"id": str(row.id), "title": row.title}


async def archive_profile_thread(session: AsyncSession, profile: str, thread_id: UUID) -> None:
    group_id, _ = profile_context_ids(profile)
    now = datetime.now(timezone.utc)
    archived_id = (
        await session.execute(
            update(threads)
            .where(
                threads.c.id == thread_id,
                threads.c.group_id == group_id,
                threads.c.archived_at.is_(None),
            )
            .values(archived_at=now, updated_at=now)
            .returning(threads.c.id)
        )
    ).scalar_one_or_none()
    if archived_id is None:
        raise ValueError("Thread not found")
    await session.commit()


async def require_profile_thread(session: AsyncSession, profile: str, thread_id: UUID) -> UUID:
    group_id, _ = profile_context_ids(profile)
    found = (
        await session.execute(
            select(threads.c.id).where(
                threads.c.id == thread_id,
                threads.c.group_id == group_id,
                threads.c.archived_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if found is None:
        raise ValueError("Thread not found")
    return found


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


async def list_personal_threads(session: AsyncSession, user_id: UUID) -> list[dict[str, str]]:
    group_id, _, _ = personal_context_ids(user_id)
    rows = (
        await session.execute(
            select(threads.c.id, threads.c.title)
            .where(threads.c.group_id == group_id, threads.c.archived_at.is_(None))
            .order_by(threads.c.created_at.desc())
        )
    ).all()
    return [{"id": str(row.id), "title": row.title} for row in rows]


async def create_personal_thread(session: AsyncSession, user_id: UUID) -> dict[str, str]:
    group_id, _, _ = personal_context_ids(user_id)
    thread_id = uuid4()
    now = datetime.now(timezone.utc)
    await session.execute(
        insert(threads).values(
            id=thread_id, group_id=group_id, title="New chat", created_by=user_id,
            archived_at=None, created_at=now, updated_at=now,
        )
    )
    await session.commit()
    return {"id": str(thread_id), "title": "New chat"}


async def require_personal_thread(session: AsyncSession, user_id: UUID, thread_id: UUID) -> UUID:
    group_id, _, _ = personal_context_ids(user_id)
    found = (
        await session.execute(
            select(threads.c.id).where(
                threads.c.id == thread_id,
                threads.c.group_id == group_id,
                threads.c.archived_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if found is None:
        raise ValueError("Thread not found")
    return found


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
                messages.c.sequence_number, messages.c.author_user_id,
                users.c.display_name.label("author_name"),
            )
            .select_from(messages.outerjoin(users, users.c.id == messages.c.author_user_id))
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
            "author_user_id": str(row.author_user_id) if row.author_user_id else None,
            "author_name": row.author_name,
        }
        for row in reversed(rows)
    ]
