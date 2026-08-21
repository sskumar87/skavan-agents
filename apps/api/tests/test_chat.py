from fastapi.testclient import TestClient

from app.main import app, get_hermes_adapter


class FakeHermesAdapter:
    async def health(self) -> bool:
        return True

    async def complete(self, messages: list[dict[str, str]]) -> str:
        assert messages == [{"role": "user", "content": "Hello Hermes"}]
        return "Hello from Hermes"


def test_chat_uses_backend_hermes_adapter() -> None:
    app.dependency_overrides[get_hermes_adapter] = lambda: FakeHermesAdapter()
    try:
        response = TestClient(app).post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "Hello Hermes"}]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "message": {"role": "assistant", "content": "Hello from Hermes"}
    }


def test_hermes_health_uses_backend_adapter() -> None:
    app.dependency_overrides[get_hermes_adapter] = lambda: FakeHermesAdapter()
    try:
        response = TestClient(app).get("/api/hermes/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
