"""Release-blocking acceptance coverage for the two-profile product model."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi.testclient import TestClient

import app.main as main


PERSONAL_USER = "11111111-1111-4111-8111-111111111111"
WORK_USER = "22222222-2222-4222-8222-222222222222"
BOTH_USER = "33333333-3333-4333-8333-333333333333"
REVOKED_USER = "44444444-4444-4444-8444-444444444444"
NO_PROFILE_USER = "55555555-5555-4555-8555-555555555555"
THREAD_ID = "66666666-6666-4666-8666-666666666666"


PROFILE_ACCESS = {
    UUID(PERSONAL_USER): ["personal"],
    UUID(WORK_USER): ["work"],
    UUID(BOTH_USER): ["personal", "work"],
    # This user previously preferred Work, but an administrator revoked it.
    UUID(REVOKED_USER): ["personal"],
    UUID(NO_PROFILE_USER): [],
}


class FakeSessionContext:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeSessionFactory:
    def __call__(self):
        return FakeSessionContext()


class FakeHermes:
    async def list_sessions(self, *, profile: str):
        return []


async def fake_get_user_profiles(session, user_id):
    return PROFILE_ACCESS[user_id]


async def fake_ensure_profile_context(session, user_id, profile):
    return UUID(THREAD_ID)


async def fake_list_profile_threads(session, profile):
    return [{
        "id": THREAD_ID,
        "title": f"Shared {profile.title()} chat",
        "last_active": datetime(2026, 8, 26, tzinfo=timezone.utc),
        "session_kind": "unified",
        "hermes_session_id": f"shared-{profile}",
    }]


async def fake_synchronize_profile_thread_titles(session, profile, titles):
    return None


def configure(monkeypatch):
    monkeypatch.setattr(main, "get_session_factory", lambda: FakeSessionFactory())
    monkeypatch.setattr(main, "get_user_profiles", fake_get_user_profiles)
    monkeypatch.setattr(main, "ensure_profile_context", fake_ensure_profile_context)
    monkeypatch.setattr(main, "list_profile_threads", fake_list_profile_threads)
    monkeypatch.setattr(
        main, "synchronize_profile_thread_titles",
        fake_synchronize_profile_thread_titles,
    )
    main.app.dependency_overrides[main.get_hermes_adapter] = FakeHermes


def teardown():
    main.app.dependency_overrides.clear()


def test_personal_only_work_only_both_and_all_revoked_role_sets(monkeypatch) -> None:
    configure(monkeypatch)
    client = TestClient(main.app)
    try:
        expected = {
            PERSONAL_USER: ["personal"],
            WORK_USER: ["work"],
            BOTH_USER: ["personal", "work"],
            REVOKED_USER: ["personal"],
            NO_PROFILE_USER: [],
        }
        for user_id, profiles in expected.items():
            response = client.get(
                "/api/chat/profiles", headers={"X-Skavan-User-Id": user_id},
            )
            assert response.status_code == 200
            assert [item["key"] for item in response.json()] == profiles
    finally:
        teardown()


def test_wrong_profile_is_denied_for_single_profile_users(monkeypatch) -> None:
    configure(monkeypatch)
    client = TestClient(main.app)
    try:
        personal_to_work = client.get(
            "/api/chat/threads?profile=work",
            headers={"X-Skavan-User-Id": PERSONAL_USER},
        )
        work_to_personal = client.get(
            "/api/chat/threads?profile=personal",
            headers={"X-Skavan-User-Id": WORK_USER},
        )
        no_roles = client.get(
            "/api/chat/threads?profile=personal",
            headers={"X-Skavan-User-Id": NO_PROFILE_USER},
        )
        assert personal_to_work.status_code == 403
        assert work_to_personal.status_code == 403
        assert no_roles.status_code == 403
        assert personal_to_work.json()["detail"] == "Profile access denied"
    finally:
        teardown()


def test_two_profile_user_can_open_both_shared_profile_chat_lists(monkeypatch) -> None:
    configure(monkeypatch)
    client = TestClient(main.app)
    try:
        for profile in ("personal", "work"):
            response = client.get(
                f"/api/chat/threads?profile={profile}",
                headers={"X-Skavan-User-Id": BOTH_USER},
            )
            assert response.status_code == 200
            assert response.json()[0]["title"] == f"Shared {profile.title()} chat"
    finally:
        teardown()


def test_two_users_with_same_role_see_the_same_shared_chat(monkeypatch) -> None:
    configure(monkeypatch)
    client = TestClient(main.app)
    try:
        first = client.get(
            "/api/chat/threads?profile=personal",
            headers={"X-Skavan-User-Id": PERSONAL_USER},
        )
        second = client.get(
            "/api/chat/threads?profile=personal",
            headers={"X-Skavan-User-Id": BOTH_USER},
        )
        assert first.status_code == second.status_code == 200
        assert first.json() == second.json()
        assert first.json()[0]["hermes_session_id"] == "shared-personal"
    finally:
        teardown()

