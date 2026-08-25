import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from uuid import UUID

from fastapi.testclient import TestClient

from app.hermes import HermesAdapter, HermesError
import app.hermes as hermes_module
import app.main as main
from app.main import app, get_hermes_adapter, stream_with_heartbeat


USER_ID = "d34ab70c-4cec-4361-86b2-e3b8c97241ec"


def test_hermes_session_key_is_sent_as_a_request_header() -> None:
    adapter = HermesAdapter(
        base_url="http://hermes:8642", api_key="a" * 32,
        work_api_key="w" * 32,
    )

    assert adapter.request_headers("skavan:profile:personal", "personal") == {
        "Authorization": f"Bearer {'a' * 32}",
        "X-Hermes-Session-Key": "skavan:profile:personal",
    }
    assert adapter.endpoint("/v1/chat/completions", "personal") == (
        "http://hermes:8642/v1/chat/completions"
    )
    assert adapter.endpoint("/v1/chat/completions", "work") == (
        "http://hermes:8642/p/work/v1/chat/completions"
    )


def test_hermes_session_messages_loads_every_page(monkeypatch) -> None:
    requested_offsets: list[int] = []

    class FakeResponse:
        def __init__(self, data):
            self._data = data

        def raise_for_status(self):
            return None

        def json(self):
            return {"data": self._data}

    class FakeAsyncClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def get(self, _url, *, headers, params):
            assert headers["Authorization"] == f"Bearer {'a' * 32}"
            offset = params["offset"]
            requested_offsets.append(offset)
            if offset == 0:
                return FakeResponse([{"id": index} for index in range(500)])
            return FakeResponse([{"id": 500}, {"id": 501}])

    monkeypatch.setattr(hermes_module.httpx2, "AsyncClient", FakeAsyncClient)
    adapter = HermesAdapter(base_url="http://hermes:8642", api_key="a" * 32)

    messages = asyncio.run(adapter.session_messages("session-1", profile="personal"))

    assert requested_offsets == [0, 500]
    assert len(messages) == 502
    assert messages[-1]["id"] == 501


class FakeSessionContext:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeSessionFactory:
    def __call__(self):
        return FakeSessionContext()


async def fake_ensure_profile_context(session, user_id, profile):
    assert user_id == UUID(USER_ID)
    assert profile == "personal"
    return UUID("f3a79589-1097-4bf4-8b09-893c39946f13")


async def fake_append_message(session, **values):
    return UUID("827cae77-34b9-41ae-92f9-c61ca6de8205")


async def fake_require_profile_thread(session, profile, thread_id):
    assert profile == "personal"
    return thread_id


async def fake_rename_profile_thread(session, profile, thread_id, title):
    assert profile == "personal"
    assert title == "Market research"
    return {"id": str(thread_id), "title": title}


async def fake_archive_profile_thread(session, profile, thread_id):
    assert profile == "personal"
    assert thread_id == UUID("f3a79589-1097-4bf4-8b09-893c39946f13")


async def fake_load_messages(session, thread_id, limit=100):
    return [{
        "id": "827cae77-34b9-41ae-92f9-c61ca6de8205",
        "role": "user",
        "content": "Hello Hermes",
        "created_at": datetime.now(timezone.utc),
        "author_user_id": USER_ID,
        "author_name": "Skavan",
    }]


async def fake_get_user_profiles(session, user_id):
    assert user_id == UUID(USER_ID)
    return ["personal", "work"]


def configure_conversation_fakes(monkeypatch) -> None:
    monkeypatch.setattr(main, "get_session_factory", lambda: FakeSessionFactory())
    monkeypatch.setattr(main, "ensure_profile_context", fake_ensure_profile_context)
    monkeypatch.setattr(main, "append_message", fake_append_message)
    monkeypatch.setattr(main, "load_messages", fake_load_messages)
    monkeypatch.setattr(main, "require_profile_thread", fake_require_profile_thread)
    monkeypatch.setattr(main, "rename_profile_thread", fake_rename_profile_thread)
    monkeypatch.setattr(main, "archive_profile_thread", fake_archive_profile_thread)
    monkeypatch.setattr(main, "get_user_profiles", fake_get_user_profiles)


class FakeHermesAdapter:
    async def health(self) -> bool:
        return True

    async def complete(
        self, messages: list[dict[str, str]], *, session_key: str | None = None,
        profile: str | None = None,
    ) -> str:
        assert messages == [{"role": "user", "content": "Hello Hermes"}]
        assert session_key == "skavan:profile:personal"
        assert profile == "personal"
        return "Hello from Hermes"

    async def stream(
        self, messages: list[dict[str, str]], *, session_key: str, profile: str,
    ) -> AsyncIterator[str]:
        assert messages == [{"role": "user", "content": "Hello Hermes"}]
        assert session_key == "skavan:profile:personal"
        assert profile == "personal"
        yield "Hello "
        yield "from Hermes"

    async def list_sessions(self, *, profile: str):
        assert profile == "personal"
        return [{
            "id": "terminal-session-1", "title": "Terminal investigation",
            "preview": "Inspect the service", "message_count": 2,
            "last_active": 123.5, "end_reason": "tui_shutdown",
        }, {
            "id": "api-execution-1", "title": "Inspect the service now",
            "preview": "Inspect the service now", "message_count": 2,
            "last_active": 124.5, "end_reason": None,
        }]

    async def session_messages(self, session_id: str, *, profile: str):
        assert session_id == "terminal-session-1"
        assert profile == "personal"
        return [
            {"id": 1, "role": "user", "content": "Inspect it", "timestamp": 1.0},
            {"id": 2, "role": "assistant", "content": "It is healthy", "timestamp": 2.0},
        ]

    async def stream_session(
        self, session_id: str, message: str, *, session_key: str, profile: str,
    ) -> AsyncIterator[str]:
        assert session_id == "terminal-session-1"
        assert message == "Continue"
        assert session_key == "skavan:profile:personal"
        assert profile == "personal"
        yield "Continued"


class FailingHermesAdapter:
    async def stream(
        self, messages: list[dict[str, str]], *, session_key: str, profile: str,
    ) -> AsyncIterator[str]:
        assert session_key == "skavan:profile:personal"
        assert profile == "personal"
        if False:
            yield ""
        raise HermesError("Hermes is temporarily unavailable.")


class LongHistoryHermesAdapter(FakeHermesAdapter):
    async def session_messages(self, session_id: str, *, profile: str):
        assert session_id == "terminal-session-1"
        assert profile == "personal"
        return [{
            "id": 1, "role": "assistant", "content": "x" * 25_000,
            "timestamp": 1.0,
        }]


def test_stream_heartbeat_keeps_an_idle_agent_connection_open() -> None:
    async def delayed_stream() -> AsyncIterator[str]:
        await asyncio.sleep(0.02)
        yield "Completed"

    async def collect() -> list[str | None]:
        return [
            item async for item in stream_with_heartbeat(
                delayed_stream(), interval_seconds=0.001,
            )
        ]

    events = asyncio.run(collect())
    assert None in events
    assert events[-1] == "Completed"


def test_chat_uses_backend_hermes_adapter(monkeypatch) -> None:
    configure_conversation_fakes(monkeypatch)
    app.dependency_overrides[get_hermes_adapter] = lambda: FakeHermesAdapter()
    try:
        response = TestClient(app).post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "Hello Hermes"}]},
            headers={"X-Skavan-User-Id": USER_ID},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "message": {"role": "assistant", "content": "Hello from Hermes"}
    }


def test_chat_requires_platform_user() -> None:
    response = TestClient(app).post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "Hello Hermes"}]},
    )

    assert response.status_code == 401


def test_hermes_health_uses_backend_adapter() -> None:
    app.dependency_overrides[get_hermes_adapter] = lambda: FakeHermesAdapter()
    try:
        response = TestClient(app).get("/api/hermes/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_history_marks_the_authenticated_author(monkeypatch) -> None:
    configure_conversation_fakes(monkeypatch)
    response = TestClient(app).get(
        "/api/chat/history",
        headers={"X-Skavan-User-Id": USER_ID},
    )

    assert response.status_code == 200
    assert response.json()[0] == {
        "id": "827cae77-34b9-41ae-92f9-c61ca6de8205",
        "role": "user",
        "content": "Hello Hermes",
        "created_at": response.json()[0]["created_at"],
        "is_current_user": True,
        "author_name": "Skavan",
    }


def test_profile_member_can_rename_shared_postgres_chat(monkeypatch) -> None:
    configure_conversation_fakes(monkeypatch)
    response = TestClient(app).patch(
        "/api/chat/threads/f3a79589-1097-4bf4-8b09-893c39946f13",
        json={"profile": "personal", "title": "  Market research  "},
        headers={"X-Skavan-User-Id": USER_ID},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "f3a79589-1097-4bf4-8b09-893c39946f13",
        "title": "Market research",
    }


def test_profile_member_can_archive_shared_postgres_chat(monkeypatch) -> None:
    configure_conversation_fakes(monkeypatch)
    response = TestClient(app).delete(
        "/api/chat/threads/f3a79589-1097-4bf4-8b09-893c39946f13?profile=personal",
        headers={"X-Skavan-User-Id": USER_ID},
    )

    assert response.status_code == 204
    assert response.content == b""


def test_profile_member_can_list_and_read_hermes_sessions(monkeypatch) -> None:
    configure_conversation_fakes(monkeypatch)
    app.dependency_overrides[get_hermes_adapter] = lambda: FakeHermesAdapter()
    try:
        sessions = TestClient(app).get(
            "/api/hermes/sessions?profile=personal",
            headers={"X-Skavan-User-Id": USER_ID},
        )
        messages = TestClient(app).get(
            "/api/hermes/sessions/terminal-session-1/messages?profile=personal",
            headers={"X-Skavan-User-Id": USER_ID},
        )
    finally:
        app.dependency_overrides.clear()

    assert sessions.status_code == 200
    assert len(sessions.json()) == 1
    assert sessions.json()[0]["title"] == "Terminal investigation"
    assert sessions.json()[0]["source"] == "hermes"
    assert messages.status_code == 200
    assert [item["content"] for item in messages.json()] == ["Inspect it", "It is healthy"]
    assert messages.json()[0]["author_name"] == "Terminal user"


def test_hermes_session_history_allows_existing_long_messages(monkeypatch) -> None:
    configure_conversation_fakes(monkeypatch)
    app.dependency_overrides[get_hermes_adapter] = lambda: LongHistoryHermesAdapter()
    try:
        response = TestClient(app).get(
            "/api/hermes/sessions/terminal-session-1/messages?profile=personal",
            headers={"X-Skavan-User-Id": USER_ID},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert len(response.json()[0]["content"]) == 25_000


def test_profile_member_can_continue_hermes_session(monkeypatch) -> None:
    configure_conversation_fakes(monkeypatch)
    app.dependency_overrides[get_hermes_adapter] = lambda: FakeHermesAdapter()
    try:
        response = TestClient(app).post(
            "/api/hermes/sessions/terminal-session-1/chat/stream",
            json={"profile": "personal", "message": "Continue"},
            headers={"X-Skavan-User-Id": USER_ID},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.text == (
        'event: token\ndata: {"content":"Continued"}\n\n'
        "event: done\ndata: {}\n\n"
    )


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
