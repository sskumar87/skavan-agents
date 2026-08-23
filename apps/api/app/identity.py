import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse
from uuid import UUID as PythonUUID, uuid4

import jwt
import httpx2
from fastapi import HTTPException
from jwt import PyJWKClient
from sqlalchemy import DateTime, String, column, delete, select, table, update
from sqlalchemy.dialects.postgresql import JSONB, UUID, insert
from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)
PROFILE_ROLE_CLAIM = "urn:zitadel:iam:org:project:roles"
PROFILE_ROLE_MAP = {"profile.personal": "personal", "profile.work": "work"}
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


class ZitadelProvisioningError(RuntimeError):
    pass


@dataclass(frozen=True)
class ZitadelRoleProvisioner:
    base_url: str
    public_issuer: str
    token: str
    project_id: str
    organization_id: str

    @classmethod
    def from_environment(cls) -> "ZitadelRoleProvisioner":
        issuer = os.getenv("OIDC_ISSUER_URL", "").rstrip("/")
        return cls(
            base_url=os.getenv("ZITADEL_MANAGEMENT_BASE_URL", issuer).rstrip("/"),
            public_issuer=issuer,
            token=os.getenv("ZITADEL_ROLE_PROVISIONER_TOKEN", ""),
            project_id=os.getenv("ZITADEL_PROJECT_ID", ""),
            organization_id=os.getenv("ZITADEL_ORGANIZATION_ID", ""),
        )

    def _headers(self) -> dict[str, str]:
        if not all((self.base_url, self.public_issuer, self.token, self.project_id, self.organization_id)):
            raise ZitadelProvisioningError("ZITADEL role provisioning is not configured")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Connect-Protocol-Version": "1",
        }
        if urlparse(self.base_url).netloc != urlparse(self.public_issuer).netloc:
            headers.update({
                "Host": urlparse(self.public_issuer).netloc,
                "X-Forwarded-Host": urlparse(self.public_issuer).netloc,
                "X-Forwarded-Proto": urlparse(self.public_issuer).scheme,
            })
        return headers

    async def assign_registration_roles(self, subject: str, include_work: bool) -> None:
        role_keys = ["profile.personal"]
        if include_work:
            role_keys.append("profile.work")
        try:
            async with httpx2.AsyncClient(timeout=8.0, follow_redirects=False) as client:
                existing_response = await client.post(
                    f"{self.base_url}/zitadel.authorization.v2.AuthorizationService/ListAuthorizations",
                    headers=self._headers(),
                    json={
                        "pagination": {"limit": 10},
                        "filters": [
                            {"inUserIds": {"ids": [subject]}},
                            {"projectId": {"id": self.project_id}},
                        ],
                    },
                )
                existing_response.raise_for_status()
                authorizations = existing_response.json().get("authorizations", [])
                existing = next((item for item in authorizations
                                 if item.get("user", {}).get("id") == subject
                                 and item.get("project", {}).get("id") == self.project_id), None)
                if existing:
                    retained = [role.get("key") for role in existing.get("roles", [])
                                if isinstance(role.get("key"), str)
                                and not role["key"].startswith("profile.")]
                    response = await client.post(
                        f"{self.base_url}/zitadel.authorization.v2.AuthorizationService/UpdateAuthorization",
                        headers=self._headers(),
                        json={"id": existing["id"], "roleKeys": retained + role_keys},
                    )
                else:
                    response = await client.post(
                        f"{self.base_url}/zitadel.authorization.v2.AuthorizationService/CreateAuthorization",
                        headers=self._headers(),
                        json={
                            "userId": subject,
                            "projectId": self.project_id,
                            "organizationId": self.organization_id,
                            "roleKeys": role_keys,
                        },
                    )
        except httpx2.HTTPError as exc:
            raise ZitadelProvisioningError("ZITADEL role provisioning is unavailable") from exc
        if response.status_code >= 400:
            logger.error("ZITADEL role provisioning failed with HTTP %s", response.status_code)
            raise ZitadelProvisioningError("Unable to assign the selected profiles")


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


def profiles_from_claims(claims: dict[str, Any]) -> list[str]:
    raw_roles = claims.get(PROFILE_ROLE_CLAIM, {})
    role_names = list(raw_roles) if isinstance(raw_roles, dict) else raw_roles
    if not isinstance(role_names, (list, tuple, set)):
        return []
    assigned = {PROFILE_ROLE_MAP[role] for role in role_names if role in PROFILE_ROLE_MAP}
    return [profile for profile in ("personal", "work") if profile in assigned]


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
    current_preferences = (
        await session.execute(
            select(users.c.preferences).where(users.c.id == linked_user_id)
        )
    ).scalar_one()
    preferences = {
        **current_preferences,
        "profile_roles": profiles_from_claims(identity.claims),
    }
    await session.execute(
        update(users).where(users.c.id == linked_user_id).values(
            display_name=identity.display_name, email=identity.email,
            preferences=preferences, updated_at=now,
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


async def set_user_profile_preference(
    session: AsyncSession, user_id: PythonUUID, profile: str,
) -> dict[str, Any] | None:
    current = (
        await session.execute(
            select(users.c.preferences).where(users.c.id == user_id).with_for_update()
        )
    ).scalar_one_or_none()
    if current is None:
        return None
    assigned = current.get("profile_roles")
    if not isinstance(assigned, list) or profile not in assigned:
        raise ValueError("Profile access denied")
    preferences = {**current, "preferred_profile": profile}
    await session.execute(
        update(users).where(users.c.id == user_id).values(
            preferences=preferences, updated_at=datetime.now(timezone.utc),
        )
    )
    await session.commit()
    return await get_platform_user(session, user_id)


async def get_user_profiles(session: AsyncSession, user_id: PythonUUID) -> list[str]:
    preferences = (
        await session.execute(select(users.c.preferences).where(users.c.id == user_id))
    ).scalar_one_or_none()
    if preferences is None:
        return []
    assigned = preferences.get("profile_roles")
    if not isinstance(assigned, list):
        return []
    return [profile for profile in ("personal", "work") if profile in assigned]


async def get_external_subject(session: AsyncSession, user_id: PythonUUID) -> str | None:
    return (
        await session.execute(
            select(identity_accounts.c.subject)
            .where(identity_accounts.c.user_id == user_id)
            .order_by(identity_accounts.c.created_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
