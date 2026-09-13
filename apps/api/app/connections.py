from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, DateTime, MetaData, String, Table, and_, delete, func, insert, select, update
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession


metadata = MetaData()

channel_identities = Table(
    "channel_identities",
    metadata,
    Column("id", PG_UUID(as_uuid=True), primary_key=True),
    Column("user_id", PG_UUID(as_uuid=True), nullable=False),
    Column("provider", String(50), nullable=False),
    Column("external_subject", String(500), nullable=False),
    Column("linked_at", DateTime(timezone=True), nullable=False),
    Column("last_seen_at", DateTime(timezone=True)),
    Column("metadata", JSON, nullable=False),
)

channel_identity_profiles = Table(
    "channel_identity_profiles",
    metadata,
    Column("id", PG_UUID(as_uuid=True), primary_key=True),
    Column(
        "channel_identity_id", PG_UUID(as_uuid=True),
        nullable=False,
    ),
    Column("profile_key", String(32), nullable=False),
    Column("linked_at", DateTime(timezone=True), nullable=False),
    Column("last_verified_at", DateTime(timezone=True), nullable=False),
)


async def link_telegram_identity(
    session: AsyncSession, user_id: UUID, *, external_subject: str,
    username: str, profile: str,
) -> dict[str, Any]:
    existing = (
        await session.execute(
            select(channel_identities).where(
                and_(
                    channel_identities.c.provider == "telegram",
                    channel_identities.c.external_subject == external_subject,
                )
            )
        )
    ).mappings().first()
    now = func.now()
    if existing and existing["user_id"] != user_id:
        raise ValueError("This Telegram account is linked to another Skavan user")
    if existing:
        identity_id = existing["id"]
        await session.execute(
            update(channel_identities)
            .where(channel_identities.c.id == identity_id)
            .values(metadata={"username": username}, last_seen_at=now)
        )
    else:
        identity_id = uuid4()
        await session.execute(
            insert(channel_identities).values(
                id=identity_id, user_id=user_id, provider="telegram",
                external_subject=external_subject, linked_at=now,
                last_seen_at=now, metadata={"username": username},
            )
        )
    binding = (
        await session.execute(
            select(channel_identity_profiles.c.id).where(
                and_(
                    channel_identity_profiles.c.channel_identity_id == identity_id,
                    channel_identity_profiles.c.profile_key == profile,
                )
            )
        )
    ).scalar_one_or_none()
    if binding:
        await session.execute(
            update(channel_identity_profiles)
            .where(channel_identity_profiles.c.id == binding)
            .values(last_verified_at=now)
        )
    else:
        await session.execute(
            insert(channel_identity_profiles).values(
                id=uuid4(), channel_identity_id=identity_id, profile_key=profile,
                linked_at=now, last_verified_at=now,
            )
        )
    await session.commit()
    return {
        "provider": "telegram", "external_subject": external_subject,
        "username": username or None, "profile": profile,
    }


async def list_telegram_connections(session: AsyncSession, user_id: UUID) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            select(
                channel_identities.c.external_subject,
                channel_identities.c.metadata,
                channel_identity_profiles.c.profile_key,
                channel_identity_profiles.c.linked_at,
            )
            .join(
                channel_identity_profiles,
                channel_identity_profiles.c.channel_identity_id == channel_identities.c.id,
            )
            .where(
                and_(
                    channel_identities.c.user_id == user_id,
                    channel_identities.c.provider == "telegram",
                )
            )
            .order_by(channel_identity_profiles.c.profile_key)
        )
    ).mappings().all()
    return [
        {
            "provider": "telegram",
            "external_subject": row["external_subject"],
            "username": (row["metadata"] or {}).get("username") or None,
            "profile": row["profile_key"],
            "linked_at": row["linked_at"],
        }
        for row in rows
    ]


async def unlink_telegram_identity(
    session: AsyncSession, user_id: UUID, *, profile: str,
) -> str | None:
    row = (
        await session.execute(
            select(channel_identities.c.id, channel_identities.c.external_subject)
            .join(
                channel_identity_profiles,
                channel_identity_profiles.c.channel_identity_id == channel_identities.c.id,
            )
            .where(
                and_(
                    channel_identities.c.user_id == user_id,
                    channel_identities.c.provider == "telegram",
                    channel_identity_profiles.c.profile_key == profile,
                )
            )
        )
    ).mappings().first()
    if not row:
        return None
    await session.execute(
        delete(channel_identity_profiles).where(
            and_(
                channel_identity_profiles.c.channel_identity_id == row["id"],
                channel_identity_profiles.c.profile_key == profile,
            )
        )
    )
    remaining = (
        await session.execute(
            select(func.count()).select_from(channel_identity_profiles).where(
                channel_identity_profiles.c.channel_identity_id == row["id"]
            )
        )
    ).scalar_one()
    if remaining == 0:
        await session.execute(delete(channel_identities).where(channel_identities.c.id == row["id"]))
    await session.commit()
    return row["external_subject"]
