from fastapi.testclient import TestClient

import app.main as main


USER_ID = "d34ab70c-4cec-4361-86b2-e3b8c97241ec"


async def fake_session():
    yield object()


async def fake_get_platform_user(session, user_id):
    return {
        "id": str(user_id),
        "display_name": "Theme Tester",
        "given_name": "Theme",
        "family_name": "Tester",
        "email": "theme@example.test",
        "preferences": {
            "theme": "violet-pulse",
            "profile_roles": ["personal", "work"],
            "preferred_profile": "work",
        },
    }


async def fake_set_user_theme(session, user_id, theme):
    user = await fake_get_platform_user(session, user_id)
    user["preferences"] = {"theme": theme}
    return user


async def fake_set_user_profile_preference(session, user_id, profile):
    user = await fake_get_platform_user(session, user_id)
    if profile not in user["preferences"]["profile_roles"]:
        raise ValueError("Profile access denied")
    user["preferences"]["preferred_profile"] = profile
    return user


async def fake_reject_profile_preference(session, user_id, profile):
    raise ValueError("Profile access denied")


def test_current_user_returns_saved_preferences(monkeypatch) -> None:
    main.app.dependency_overrides[main.get_database_session] = fake_session
    monkeypatch.setattr(main, "get_platform_user", fake_get_platform_user)
    try:
        response = TestClient(main.app).get(
            "/api/users/me", headers={"X-Skavan-User-Id": USER_ID}
        )
        assert response.status_code == 200
        assert response.json()["preferences"]["theme"] == "violet-pulse"
        assert response.json()["preferences"]["preferred_profile"] == "work"
    finally:
        main.app.dependency_overrides.clear()


def test_profile_preference_is_saved_for_an_assigned_profile(monkeypatch) -> None:
    main.app.dependency_overrides[main.get_database_session] = fake_session
    monkeypatch.setattr(
        main, "set_user_profile_preference", fake_set_user_profile_preference,
    )
    try:
        response = TestClient(main.app).patch(
            "/api/users/me/preferences/profile",
            headers={"X-Skavan-User-Id": USER_ID},
            json={"profile": "personal"},
        )
        assert response.status_code == 200
        assert response.json()["preferences"]["preferred_profile"] == "personal"
    finally:
        main.app.dependency_overrides.clear()


def test_profile_preference_rejects_an_unassigned_profile(monkeypatch) -> None:
    main.app.dependency_overrides[main.get_database_session] = fake_session
    monkeypatch.setattr(
        main, "set_user_profile_preference", fake_reject_profile_preference,
    )
    try:
        response = TestClient(main.app).patch(
            "/api/users/me/preferences/profile",
            headers={"X-Skavan-User-Id": USER_ID},
            json={"profile": "work"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Profile access denied"
    finally:
        main.app.dependency_overrides.clear()


def test_theme_update_accepts_only_locked_themes(monkeypatch) -> None:
    main.app.dependency_overrides[main.get_database_session] = fake_session
    monkeypatch.setattr(main, "set_user_theme", fake_set_user_theme)
    try:
        accepted = TestClient(main.app).patch(
            "/api/users/me/preferences/theme",
            headers={"X-Skavan-User-Id": USER_ID},
            json={"theme": "daylight-circuit"},
        )
        rejected = TestClient(main.app).patch(
            "/api/users/me/preferences/theme",
            headers={"X-Skavan-User-Id": USER_ID},
            json={"theme": "unapproved-theme"},
        )
        assert accepted.status_code == 200
        assert accepted.json()["preferences"] == {"theme": "daylight-circuit"}
        assert rejected.status_code == 422
    finally:
        main.app.dependency_overrides.clear()
