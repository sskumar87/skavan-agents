from fastapi.testclient import TestClient

import app.main as main
from app.identity import PROFILE_ROLE_CLAIM, VerifiedIdentity, profiles_from_claims


def test_profile_roles_are_derived_only_from_zitadel_claims() -> None:
    assert profiles_from_claims({
        PROFILE_ROLE_CLAIM: {
            "profile.work": {"example-org": "Example"},
            "unrelated.admin": {"example-org": "Example"},
            "profile.personal": {"example-org": "Example"},
        }
    }) == ["personal", "work"]
    assert profiles_from_claims({}) == []


class FakeVerifier:
    async def verify(self, token: str) -> VerifiedIdentity:
        assert token == "valid-token"
        return VerifiedIdentity(
            issuer="https://auth.example.test",
            subject="immutable-subject",
            display_name="Test User",
            email="user@example.test",
            claims={"sub": "immutable-subject"},
            given_name="Test",
            family_name="User",
        )


async def fake_session():
    yield object()


async def fake_synchronize_user(session, identity):
    assert identity.subject == "immutable-subject"
    return {
        "id": "d34ab70c-4cec-4361-86b2-e3b8c97241ec",
        "display_name": identity.display_name,
        "given_name": identity.given_name,
        "family_name": identity.family_name,
        "email": identity.email,
        "preferences": {},
    }


def test_sync_requires_bearer_token(monkeypatch) -> None:
    main.app.dependency_overrides[main.get_database_session] = fake_session
    main.app.dependency_overrides[main.get_token_verifier] = lambda: FakeVerifier()
    monkeypatch.setattr(main, "synchronize_user", fake_synchronize_user)
    try:
        response = TestClient(main.app).post("/api/auth/sync")
        assert response.status_code == 401
    finally:
        main.app.dependency_overrides.clear()


class FakeProvisioner:
    def __init__(self) -> None:
        self.assignment: tuple[str, bool] | None = None

    async def assign_registration_roles(self, subject: str, include_work: bool) -> None:
        self.assignment = (subject, include_work)


def test_registration_profiles_assigns_only_fixed_zitadel_roles(monkeypatch) -> None:
    provisioner = FakeProvisioner()

    async def fake_subject(session, user_id):
        return "immutable-subject"

    main.app.dependency_overrides[main.get_database_session] = fake_session
    main.app.dependency_overrides[main.get_role_provisioner] = lambda: provisioner
    monkeypatch.setattr(main, "get_external_subject", fake_subject)
    try:
        response = TestClient(main.app).post(
            "/api/auth/registration-profiles",
            json={"include_work": True},
            headers={"X-Skavan-User-Id": "d34ab70c-4cec-4361-86b2-e3b8c97241ec"},
        )
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "roles": ["profile.personal", "profile.work"],
        "refresh_login": True,
    }
    assert provisioner.assignment == ("immutable-subject", True)


def test_sync_returns_canonical_platform_user(monkeypatch) -> None:
    main.app.dependency_overrides[main.get_database_session] = fake_session
    main.app.dependency_overrides[main.get_token_verifier] = lambda: FakeVerifier()
    monkeypatch.setattr(main, "synchronize_user", fake_synchronize_user)
    try:
        response = TestClient(main.app).post(
            "/api/auth/sync", headers={"Authorization": "Bearer valid-token"}
        )
        assert response.status_code == 200
        assert response.json()["id"] == "d34ab70c-4cec-4361-86b2-e3b8c97241ec"
        assert response.json()["given_name"] == "Test"
    finally:
        main.app.dependency_overrides.clear()
