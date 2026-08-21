import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse
from uuid import UUID as PythonUUID, uuid4

import jwt
from fastapi import HTTPException
from jwt import PyJWKClient
from sqlalchemy import DateTime, String, column, delete, select, table, update
from sqlalchemy.dialects.postgresql import JSONB, UUID, insert
from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)
ALLOWED_ID_TOKEN_ALGORITHMS = {
    "RS256", "RS384", "RS512", "ES256", "ES384", "ES512", "EdDSA"
}

users = table(
    "users",
    column("id", UUID(as_uuid=True)),
    column("display_name", String(200)),
    column("email", String(320)),
    column("preferences", JSONB),
    column("created_at", DateTime(timezone=True)),
    column("updated_at", DateTime(timezone=True)),
)
identity_accounts = table(
    "identity_accounts",
    column("id", UUID(as_uuid=True)),
    column("user_id", UUID(as_uuid=True)),
    column("issuer", String(500)),
    column("subject", String(500)),
    column("email_at_link", String(320)),
    column("claims", JSONB),
    column("created_at", DateTime(timezone=True)),
)


@dataclass(frozen=True)
class VerifiedIdentity:
    issuer: str
    subject: str
    display_name: str
    email: str | None
    claims: dict[str, Any]
    given_name: str | None = None
    family_name: str | None = None


class OidcTokenVerifier:
    def __init__(self) -> None:
        self.issuer = os.getenv("OIDC_ISSUER_URL", "").rstrip("/")
        self.client_id = os.getenv("OIDC_CLIENT_ID", "")
        if not self.issuer or not self.client_id:
            raise RuntimeError("OIDC_ISSUER_URL and OIDC_CLIENT_ID are required")
        jwks_url = os.getenv("OIDC_JWKS_URL", f"{self.issuer}/oauth/v2/keys")
        jwks_headers: dict[str, str] = {}
        if urlparse(jwks_url).netloc != urlparse(self.issuer).netloc:
            jwks_headers = {
                "Host": urlparse(self.issuer).netloc,
                "X-Forwarded-Host": urlparse(self.issuer).netloc,
                "X-Forwarded-Proto": urlparse(self.issuer).scheme,
            }
        self.jwks = PyJWKClient(
            jwks_url,
            cache_keys=True,
            headers=jwks_headers,
        )

    async def verify(self, token: str) -> VerifiedIdentity:
        try:
            algorithm = jwt.get_unverified_header(token).get("alg")
            if algorithm not in ALLOWED_ID_TOKEN_ALGORITHMS:
                raise jwt.InvalidAlgorithmError("Unsupported ID token algorithm")
            signing_key = await asyncio.to_thread(self.jwks.get_signing_key_from_jwt, token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=[algorithm],
                audience=self.client_id,
                issuer=self.issuer,
                leeway=30,
            )
        except jwt.PyJWTError as exc:
            logger.warning(
                "OIDC ID token rejected (%s): %s", type(exc).__name__, exc
            )
            raise HTTPException(status_code=401, detail="Invalid identity token") from exc

        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject:
            raise HTTPException(status_code=401, detail="Identity token has no subject")
        email = claims.get("email") if isinstance(claims.get("email"), str) else None
        given_name = claims.get("given_name") if isinstance(claims.get("given_name"), str) else None
        family_name = claims.get("family_name") if isinstance(claims.get("family_name"), str) else None
        structured_name = " ".join(
            value.strip() for value in (given_name, family_name) if value and value.strip()
        ) or None
        display_name = next(
            (value for value in (claims.get("name"), structured_name, claims.get("preferred_username"), email)
             if isinstance(value, str) and value.strip()),
            "Skavan user",
        )
        return VerifiedIdentity(
            self.issuer, subject, display_name, email, claims, given_name, family_name
        )


async def synchronize_user(session: AsyncSession, identity: VerifiedIdentity) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    candidate_id = uuid4()
    await session.execute(
        insert(users).values(
            id=candidate_id, display_name=identity.display_name, email=identity.email,
            preferences={}, created_at=now, updated_at=now,
        )
    )
    linked_user_id = (
        await session.execute(
            insert(identity_accounts)
            .values(
                id=uuid4(), user_id=candidate_id, issuer=identity.issuer,
                subject=identity.subject, email_at_link=identity.email,
                claims=identity.claims, created_at=now,
            )
            .on_conflict_do_update(
                constraint="uq_identity_accounts_issuer_subject",
                set_={"email_at_link": identity.email, "claims": identity.claims},
            )
            .returning(identity_accounts.c.user_id)
        )
    ).scalar_one()
    if linked_user_id != candidate_id:
        await session.execute(delete(users).where(users.c.id == candidate_id))
    await session.execute(
        update(users).where(users.c.id == linked_user_id).values(
            display_name=identity.display_name, email=identity.email, updated_at=now,
        )
    )
    await session.commit()
    result = (
        await session.execute(
            select(users.c.id, users.c.display_name, users.c.email, users.c.preferences)
            .where(users.c.id == linked_user_id)
        )
    ).one()
    return {
        "id": str(result.id), "display_name": result.display_name,
        "given_name": identity.given_name or result.display_name.split(maxsplit=1)[0],
        "family_name": identity.family_name,
        "email": result.email, "preferences": result.preferences,
    }


async def get_platform_user(session: AsyncSession, user_id: PythonUUID) -> dict[str, Any] | None:
    result = (
        await session.execute(
            select(users.c.id, users.c.display_name, users.c.email, users.c.preferences)
            .where(users.c.id == user_id)
        )
    ).one_or_none()
    if result is None:
        return None
    return {
        "id": str(result.id), "display_name": result.display_name,
        "given_name": result.display_name.split(maxsplit=1)[0], "family_name": None,
        "email": result.email, "preferences": result.preferences,
    }


async def set_user_theme(
    session: AsyncSession, user_id: PythonUUID, theme: str,
) -> dict[str, Any] | None:
    current = (
        await session.execute(
            select(users.c.preferences).where(users.c.id == user_id).with_for_update()
        )
    ).scalar_one_or_none()
    if current is None:
        return None
    preferences = {**current, "theme": theme}
    await session.execute(
        update(users).where(users.c.id == user_id).values(
            preferences=preferences, updated_at=datetime.now(timezone.utc),
        )
    )
    await session.commit()
    return await get_platform_user(session, user_id)
