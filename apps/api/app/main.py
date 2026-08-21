import json
from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Literal
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversations import append_message, ensure_personal_thread, load_messages
from app.database import get_database_session, get_session_factory
from app.hermes import HermesAdapter, HermesError
from app.identity import (
    OidcTokenVerifier,
    get_platform_user,
    set_user_theme,
    synchronize_user,
)


app = FastAPI(title="Skavan Agents API", version="0.1.0")


class PlatformUser(BaseModel):
    id: str
    display_name: str
    email: str | None
    preferences: dict[str, object]


ThemeName = Literal[
    "neon-grid", "violet-pulse", "amber-terminal", "daylight-circuit"
]


class ThemePreferenceUpdate(BaseModel):
    theme: ThemeName


@lru_cache
def get_token_verifier() -> OidcTokenVerifier:
    return OidcTokenVerifier()


@app.post("/api/auth/sync", response_model=PlatformUser, tags=["auth"])
async def sync_authenticated_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_database_session),
    verifier: OidcTokenVerifier = Depends(get_token_verifier),
) -> PlatformUser:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Bearer identity token required")
    identity = await verifier.verify(token)
    return PlatformUser.model_validate(await synchronize_user(session, identity))


@app.get("/healthz", tags=["system"])
async def health_check() -> dict[str, str]:
    """Minimal readiness endpoint; application slices add routes here."""
    return {"status": "ok"}


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=20_000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=50)


class ChatResponse(BaseModel):
    message: ChatMessage


class StoredChatMessage(ChatMessage):
    id: str
    created_at: str


def require_platform_user_id(value: str | None) -> UUID:
    if not value:
        raise HTTPException(status_code=401, detail="Authenticated platform user required")
    try:
        return UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid platform user") from exc


@app.get("/api/users/me", response_model=PlatformUser, tags=["users"])
async def current_platform_user(
    x_skavan_user_id: str | None = Header(default=None),
    session: AsyncSession = Depends(get_database_session),
) -> PlatformUser:
    user_id = require_platform_user_id(x_skavan_user_id)
    user = await get_platform_user(session, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Platform user not found")
    return PlatformUser.model_validate(user)


@app.patch("/api/users/me/preferences/theme", response_model=PlatformUser, tags=["users"])
async def update_theme_preference(
    request: ThemePreferenceUpdate,
    x_skavan_user_id: str | None = Header(default=None),
    session: AsyncSession = Depends(get_database_session),
) -> PlatformUser:
    user_id = require_platform_user_id(x_skavan_user_id)
    user = await set_user_theme(session, user_id, request.theme)
    if user is None:
        raise HTTPException(status_code=404, detail="Platform user not found")
    return PlatformUser.model_validate(user)


@app.get("/api/chat/history", response_model=list[StoredChatMessage], tags=["chat"])
async def chat_history(
    x_skavan_user_id: str | None = Header(default=None),
) -> list[StoredChatMessage]:
    user_id = require_platform_user_id(x_skavan_user_id)
    async with get_session_factory()() as session:
        thread_id = await ensure_personal_thread(session, user_id)
        stored = await load_messages(session, thread_id)
    return [
        StoredChatMessage(
            id=item["id"], role=item["role"], content=item["content"],
            created_at=item["created_at"].isoformat(),
        )
        for item in stored
    ]


def get_hermes_adapter() -> HermesAdapter:
    return HermesAdapter.from_environment()


@app.get("/api/hermes/health", tags=["hermes"])
async def hermes_health(
    hermes: HermesAdapter = Depends(get_hermes_adapter),
) -> dict[str, str]:
    return {"status": "ok" if await hermes.health() else "unavailable"}


@app.post("/api/chat", response_model=ChatResponse, tags=["chat"])
async def chat(
    request: ChatRequest,
    hermes: HermesAdapter = Depends(get_hermes_adapter),
) -> ChatResponse:
    try:
        content = await hermes.complete(
            [message.model_dump() for message in request.messages]
        )
    except HermesError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ChatResponse(message=ChatMessage(role="assistant", content=content))


def format_sse(event: str, data: dict[str, str]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


@app.post("/api/chat/stream", tags=["chat"])
async def stream_chat(
    request: ChatRequest,
    x_skavan_user_id: str | None = Header(default=None),
    hermes: HermesAdapter = Depends(get_hermes_adapter),
) -> StreamingResponse:
    user_id = require_platform_user_id(x_skavan_user_id)
    latest = request.messages[-1]
    if latest.role != "user":
        raise HTTPException(status_code=400, detail="The latest message must be from the user")
    async with get_session_factory()() as session:
        thread_id = await ensure_personal_thread(session, user_id)
        await append_message(
            session, thread_id=thread_id, author_kind="USER",
            author_user_id=user_id, content=latest.content,
        )
        stored = await load_messages(session, thread_id, limit=50)
    hermes_messages = [
        {"role": item["role"], "content": item["content"]} for item in stored
    ]

    async def events() -> AsyncIterator[str]:
        assistant_content: list[str] = []
        try:
            async for content in hermes.stream(hermes_messages):
                assistant_content.append(content)
                yield format_sse("token", {"content": content})
            if assistant_content:
                async with get_session_factory()() as session:
                    await append_message(
                        session, thread_id=thread_id, author_kind="AGENT",
                        content="".join(assistant_content),
                    )
            yield format_sse("done", {})
        except HermesError as exc:
            yield format_sse("error", {"message": str(exc)})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )
