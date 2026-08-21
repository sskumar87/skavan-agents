from collections.abc import AsyncIterator
from datetime import datetime, timezone
from uuid import UUID

from fastapi.testclient import TestClient

from app.hermes import HermesError
import app.main as main
from app.main import app, get_hermes_adapter


USER_ID = "d34ab70c-4cec-4361-86b2-e3b8c97241ec"


class FakeSessionContext:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeSessionFactory:
    def __call__(self):
        return FakeSessionContext()


async def fake_ensure_personal_thread(session, user_id):
    assert user_id == UUID(USER_ID)
    return UUID("f3a79589-1097-4bf4-8b09-893c39946f13")


async def fake_append_message(session, **values):
    return UUID("827cae77-34b9-41ae-92f9-c61ca6de8205")


async def fake_load_messages(session, thread_id, limit=100):
    return [{
        "id": "827cae77-34b9-41ae-92f9-c61ca6de8205",
        "role": "user",
        "content": "Hello Hermes",
        "created_at": datetime.now(timezone.utc),
    }]


def configure_conversation_fakes(monkeypatch) -> None:
    monkeypatch.setattr(main, "get_session_factory", lambda: FakeSessionFactory())
    monkeypatch.setattr(main, "ensure_personal_thread", fake_ensure_personal_thread)
    monkeypatch.setattr(main, "append_message", fake_append_message)
    monkeypatch.setattr(main, "load_messages", fake_load_messages)


class FakeHermesAdapter:
    async def health(self) -> bool:
        return True

    async def complete(self, messages: list[dict[str, str]]) -> str:
        assert messages == [{"role": "user", "content": "Hello Hermes"}]
        return "Hello from Hermes"

    async def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        assert messages == [{"role": "user", "content": "Hello Hermes"}]
        yield "Hello "
        yield "from Hermes"


class FailingHermesAdapter:
    async def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        if False:
            yield ""
        raise HermesError("Hermes is temporarily unavailable.")


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


def test_chat_streams_normalized_sse_events(monkeypatch) -> None:
    configure_conversation_fakes(monkeypatch)
    app.dependency_overrides[get_hermes_adapter] = lambda: FakeHermesAdapter()
    try:
        response = TestClient(app).post(
            "/api/chat/stream",
            json={"messages": [{"role": "user", "content": "Hello Hermes"}]},
            headers={"X-Skavan-User-Id": USER_ID},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text == (
        'event: token\ndata: {"content":"Hello "}\n\n'
        'event: token\ndata: {"content":"from Hermes"}\n\n'
        "event: done\ndata: {}\n\n"
    )


def test_chat_streams_safe_error_event(monkeypatch) -> None:
    configure_conversation_fakes(monkeypatch)
    app.dependency_overrides[get_hermes_adapter] = lambda: FailingHermesAdapter()
    try:
        response = TestClient(app).post(
            "/api/chat/stream",
            json={"messages": [{"role": "user", "content": "Hello Hermes"}]},
            headers={"X-Skavan-User-Id": USER_ID},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.text == (
        'event: error\ndata: {"message":"Hermes is temporarily unavailable."}\n\n'
    )
