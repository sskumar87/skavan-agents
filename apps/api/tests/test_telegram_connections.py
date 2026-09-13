from fastapi.testclient import TestClient

import app.main as main
USER_ID = "d34ab70c-4cec-4361-86b2-e3b8c97241ec"


async def fake_session():
    yield object()


class FakePairingClient:
    def __init__(self) -> None:
        self.revoked: list[tuple[str, str]] = []

    async def approve(self, code: str, *, profile: str):
        assert code == "A2BC4D6E"
        return {"external_subject": "123456789", "username": "skavan_tester"}

    async def revoke(self, external_subject: str, *, profile: str):
        self.revoked.append((external_subject, profile))


async def allow_profile(session, user_id, profile):
    return None


async def deny_profile(session, user_id, profile):
    raise main.HTTPException(status_code=403, detail="Profile access denied")


async def fake_link(session, user_id, **values):
    return {"provider": "telegram", **values}


async def fake_list(session, user_id):
    return [{
        "provider": "telegram", "external_subject": "123456789",
        "username": "skavan_tester", "profile": "work", "linked_at": None,
    }]


async def fake_unlink(session, user_id, *, profile):
    return "123456789"


def test_link_requires_profile_access(monkeypatch) -> None:
    main.app.dependency_overrides[main.get_database_session] = fake_session
    main.app.dependency_overrides[main.get_telegram_pairing_client] = FakePairingClient
    monkeypatch.setattr(main, "require_profile_access", deny_profile)
    try:
        response = TestClient(main.app).post(
            "/api/connections/telegram",
            headers={"X-Skavan-User-Id": USER_ID},
            json={"profile": "work", "code": "A2BC4D6E"},
        )
        assert response.status_code == 403
    finally:
        main.app.dependency_overrides.clear()


def test_link_approves_hermes_code_and_records_identity(monkeypatch) -> None:
    main.app.dependency_overrides[main.get_database_session] = fake_session
    main.app.dependency_overrides[main.get_telegram_pairing_client] = FakePairingClient
    monkeypatch.setattr(main, "require_profile_access", allow_profile)
    monkeypatch.setattr(main, "link_telegram_identity", fake_link)
    try:
        response = TestClient(main.app).post(
            "/api/connections/telegram",
            headers={"X-Skavan-User-Id": USER_ID},
            json={"profile": "work", "code": "A2BC4D6E"},
        )
        assert response.status_code == 200
        assert response.json() == {
            "provider": "telegram", "external_subject": "123456789",
            "username": "skavan_tester", "profile": "work",
        }
    finally:
        main.app.dependency_overrides.clear()


def test_invalid_pairing_code_shape_is_rejected() -> None:
    main.app.dependency_overrides[main.get_database_session] = fake_session
    main.app.dependency_overrides[main.get_telegram_pairing_client] = FakePairingClient
    try:
        response = TestClient(main.app).post(
            "/api/connections/telegram",
            headers={"X-Skavan-User-Id": USER_ID},
            json={"profile": "work", "code": "too-short"},
        )
        assert response.status_code == 422
    finally:
        main.app.dependency_overrides.clear()


def test_disconnect_revokes_before_removing_database_link(monkeypatch) -> None:
    pairing = FakePairingClient()
    main.app.dependency_overrides[main.get_database_session] = fake_session
    main.app.dependency_overrides[main.get_telegram_pairing_client] = lambda: pairing
    monkeypatch.setattr(main, "list_telegram_connections", fake_list)
    monkeypatch.setattr(main, "unlink_telegram_identity", fake_unlink)
    try:
        response = TestClient(main.app).delete(
            "/api/connections/telegram/work",
            headers={"X-Skavan-User-Id": USER_ID},
        )
        assert response.status_code == 204
        assert pairing.revoked == [("123456789", "work")]
    finally:
        main.app.dependency_overrides.clear()
