from fastapi.testclient import TestClient

import app.main as main


USER_ID = "d34ab70c-4cec-4361-86b2-e3b8c97241ec"


async def fake_session():
    yield object()


async def fake_get_platform_user(session, user_id):
    return {
        "id": str(user_id),
        "display_name": "Theme Tester",
        "email": "theme@example.test",
        "preferences": {"theme": "violet-pulse"},
    }


async def fake_set_user_theme(session, user_id, theme):
    user = await fake_get_platform_user(session, user_id)
    user["preferences"] = {"theme": theme}
    return user


def test_current_user_returns_saved_preferences(monkeypatch) -> None:
    main.app.dependency_overrides[main.get_database_session] = fake_session
    monkeypatch.setattr(main, "get_platform_user", fake_get_platform_user)
    try:
        response = TestClient(main.app).get(
            "/api/users/me", headers={"X-Skavan-User-Id": USER_ID}
        )
        assert response.status_code == 200
        assert response.json()["preferences"] == {"theme": "violet-pulse"}
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
