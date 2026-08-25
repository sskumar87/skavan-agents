import asyncio
import json
from contextlib import suppress
from collections.abc import AsyncIterator
from datetime import datetime
from functools import lru_cache
from typing import Literal
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversations import (
    archive_profile_thread,
    append_message,
    create_profile_thread,
    ensure_profile_context,
    list_profile_threads,
    load_messages,
    rename_profile_thread,
    require_profile_thread,
)
from app.database import get_database_session, get_session_factory
from app.hermes import HermesAdapter, HermesError
from app.identity import (
    OidcTokenVerifier,
    ZitadelProvisioningError,
    ZitadelRoleProvisioner,
    get_external_subject,
    get_platform_user,
    get_user_profiles,
    set_user_profile_preference,
    set_user_theme,
    synchronize_user,
)


app = FastAPI(title="Skavan Agents API", version="0.1.0")


async def stream_with_heartbeat(
    source: AsyncIterator[str], interval_seconds: float = 15.0,
) -> AsyncIterator[str | None]:
    """Keep public SSE connections active while Hermes is running tools."""
    iterator = source.__aiter__()
    pending = asyncio.create_task(anext(iterator))
    try:
        while True:
            done, _ = await asyncio.wait({pending}, timeout=interval_seconds)
            if not done:
                yield None
                continue
            try:
                yield pending.result()
            except StopAsyncIteration:
                break
            pending = asyncio.create_task(anext(iterator))
    finally:
        if not pending.done():
            pending.cancel()
            with suppress(asyncio.CancelledError):
                await pending


class PlatformUser(BaseModel):
    id: str
    display_name: str
    given_name: str | None = None
    family_name: str | None = None
    email: str | None
    preferences: dict[str, object]


ThemeName = Literal[
    "neon-grid", "violet-pulse", "amber-terminal", "daylight-circuit"
]


class ThemePreferenceUpdate(BaseModel):
    theme: ThemeName


class ProfilePreferenceUpdate(BaseModel):
    profile: Literal["personal", "work"]


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
    thread_id: UUID | None = None
    profile: Literal["personal", "work"] = "personal"


class ChatResponse(BaseModel):
    message: ChatMessage


class StoredChatMessage(BaseModel):
    id: str
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)
    created_at: str
    is_current_user: bool
    author_name: str | None = None


class ChatThread(BaseModel):
    id: str
    title: str
    last_active: datetime | None = None


class ChatThreadCreate(BaseModel):
    profile: Literal["personal", "work"]


class ChatThreadUpdate(BaseModel):
    profile: Literal["personal", "work"]
    title: str = Field(min_length=1, max_length=300)


class ChatProfile(BaseModel):
    key: Literal["personal", "work"]
    label: str


class HermesSessionSummary(BaseModel):
    id: str
    title: str
    preview: str | None = None
    message_count: int = 0
    last_active: float | None = None
    source: Literal["hermes"] = "hermes"


class HermesSessionChatRequest(BaseModel):
    profile: Literal["personal", "work"]
    message: str = Field(min_length=1, max_length=20_000)


class RegistrationProfilesRequest(BaseModel):
    include_work: bool = False


class RegistrationProfilesResponse(BaseModel):
    roles: list[str]
    refresh_login: bool = True


def require_platform_user_id(value: str | None) -> UUID:
    if not value:
        raise HTTPException(status_code=401, detail="Authenticated platform user required")
    try:
        return UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid platform user") from exc


def get_role_provisioner() -> ZitadelRoleProvisioner:
    return ZitadelRoleProvisioner.from_environment()


@app.post(
    "/api/auth/registration-profiles",
    response_model=RegistrationProfilesResponse,
    tags=["auth"],
)
async def assign_registration_profiles(
    request: RegistrationProfilesRequest,
    x_skavan_user_id: str | None = Header(default=None),
    session: AsyncSession = Depends(get_database_session),
    provisioner: ZitadelRoleProvisioner = Depends(get_role_provisioner),
) -> RegistrationProfilesResponse:
    user_id = require_platform_user_id(x_skavan_user_id)
    subject = await get_external_subject(session, user_id)
    if subject is None:
        raise HTTPException(status_code=404, detail="Identity account not found")
    try:
        await provisioner.assign_registration_roles(subject, request.include_work)
    except ZitadelProvisioningError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    roles = ["profile.personal"]
    if request.include_work:
        roles.append("profile.work")
    return RegistrationProfilesResponse(roles=roles)


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


@app.patch("/api/users/me/preferences/profile", response_model=PlatformUser, tags=["users"])
async def update_profile_preference(
    request: ProfilePreferenceUpdate,
    x_skavan_user_id: str | None = Header(default=None),
    session: AsyncSession = Depends(get_database_session),
) -> PlatformUser:
    user_id = require_platform_user_id(x_skavan_user_id)
    try:
        user = await set_user_profile_preference(session, user_id, request.profile)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if user is None:
        raise HTTPException(status_code=404, detail="Platform user not found")
    return PlatformUser.model_validate(user)


async def require_profile_access(
    session: AsyncSession, user_id: UUID, profile: str,
) -> None:
    if profile not in await get_user_profiles(session, user_id):
        raise HTTPException(status_code=403, detail="Profile access denied")


@app.get("/api/chat/profiles", response_model=list[ChatProfile], tags=["chat"])
async def chat_profiles(
    x_skavan_user_id: str | None = Header(default=None),
) -> list[ChatProfile]:
    user_id = require_platform_user_id(x_skavan_user_id)
    async with get_session_factory()() as session:
        profiles = await get_user_profiles(session, user_id)
    return [ChatProfile(key=key, label=key.title()) for key in profiles]


@app.get("/api/chat/threads", response_model=list[ChatThread], response_model_exclude_none=True, tags=["chat"])
async def chat_threads(
    profile: Literal["personal", "work"] = "personal",
    x_skavan_user_id: str | None = Header(default=None),
) -> list[ChatThread]:
    user_id = require_platform_user_id(x_skavan_user_id)
    async with get_session_factory()() as session:
        await require_profile_access(session, user_id, profile)
        await ensure_profile_context(session, user_id, profile)
        stored = await list_profile_threads(session, profile)
    return [ChatThread.model_validate(item) for item in stored]


@app.post("/api/chat/threads", response_model=ChatThread, response_model_exclude_none=True, tags=["chat"])
async def new_chat_thread(
    request: ChatThreadCreate,
    x_skavan_user_id: str | None = Header(default=None),
) -> ChatThread:
    user_id = require_platform_user_id(x_skavan_user_id)
    async with get_session_factory()() as session:
        await require_profile_access(session, user_id, request.profile)
        await ensure_profile_context(session, user_id, request.profile)
        stored = await create_profile_thread(session, user_id, request.profile)
    return ChatThread.model_validate(stored)


@app.patch("/api/chat/threads/{thread_id}", response_model=ChatThread, response_model_exclude_none=True, tags=["chat"])
async def rename_chat_thread(
    thread_id: UUID,
    request: ChatThreadUpdate,
    x_skavan_user_id: str | None = Header(default=None),
) -> ChatThread:
    user_id = require_platform_user_id(x_skavan_user_id)
    title = request.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Chat title cannot be empty")
    async with get_session_factory()() as session:
        await require_profile_access(session, user_id, request.profile)
        try:
            stored = await rename_profile_thread(session, request.profile, thread_id, title)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Thread not found") from exc
    return ChatThread.model_validate(stored)


@app.delete("/api/chat/threads/{thread_id}", status_code=204, tags=["chat"])
async def delete_chat_thread(
    thread_id: UUID,
    profile: Literal["personal", "work"],
    x_skavan_user_id: str | None = Header(default=None),
) -> Response:
    user_id = require_platform_user_id(x_skavan_user_id)
    async with get_session_factory()() as session:
        await require_profile_access(session, user_id, profile)
        try:
            await archive_profile_thread(session, profile, thread_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Thread not found") from exc
    return Response(status_code=204)


@app.get("/api/chat/history", response_model=list[StoredChatMessage], tags=["chat"])
async def chat_history(
    profile: Literal["personal", "work"] = "personal",
    thread_id: UUID | None = None,
    x_skavan_user_id: str | None = Header(default=None),
) -> list[StoredChatMessage]:
    user_id = require_platform_user_id(x_skavan_user_id)
    async with get_session_factory()() as session:
        await require_profile_access(session, user_id, profile)
        resolved_thread_id = await ensure_profile_context(session, user_id, profile) if thread_id is None else thread_id
        try:
            await require_profile_thread(session, profile, resolved_thread_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Thread not found") from exc
        stored = await load_messages(session, resolved_thread_id)
    return [
        StoredChatMessage(
            id=item["id"], role=item["role"], content=item["content"],
            created_at=item["created_at"].isoformat(),
            is_current_user=item.get("author_user_id") == str(user_id),
            author_name=item.get("author_name"),
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


@app.get(
    "/api/hermes/sessions", response_model=list[HermesSessionSummary], tags=["hermes"],
)
async def hermes_sessions(
    profile: Literal["personal", "work"],
    x_skavan_user_id: str | None = Header(default=None),
    hermes: HermesAdapter = Depends(get_hermes_adapter),
) -> list[HermesSessionSummary]:
    user_id = require_platform_user_id(x_skavan_user_id)
    async with get_session_factory()() as session:
        await require_profile_access(session, user_id, profile)
    try:
        stored = await hermes.list_sessions(profile=profile)
    except HermesError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    result: list[HermesSessionSummary] = []
    for item in stored:
        # Stateless API executions create internal Hermes sessions whose auto-title is
        # the user's prompt. They are implementation artifacts, not sidebar chats.
        # Completed TUI sessions are the native conversations users can resume here.
        if item.get("end_reason") != "tui_shutdown":
            continue
        session_id = item.get("id")
        if not isinstance(session_id, str) or not session_id:
            continue
        raw_title = item.get("title")
        raw_preview = item.get("preview")
        result.append(HermesSessionSummary(
            id=session_id,
            title=raw_title.strip() if isinstance(raw_title, str) and raw_title.strip() else "Hermes session",
            preview=raw_preview if isinstance(raw_preview, str) else None,
            message_count=item.get("message_count") if isinstance(item.get("message_count"), int) else 0,
            last_active=float(item["last_active"]) if isinstance(item.get("last_active"), (int, float)) else None,
        ))
    return result


@app.get(
    "/api/hermes/sessions/{session_id}/messages",
    response_model=list[StoredChatMessage],
    tags=["hermes"],
)
async def hermes_session_messages(
    session_id: str,
    profile: Literal["personal", "work"],
    x_skavan_user_id: str | None = Header(default=None),
    hermes: HermesAdapter = Depends(get_hermes_adapter),
) -> list[StoredChatMessage]:
    user_id = require_platform_user_id(x_skavan_user_id)
    async with get_session_factory()() as session:
        await require_profile_access(session, user_id, profile)
    try:
        stored = await hermes.session_messages(session_id, profile=profile)
    except HermesError as exc:
        status = 404 if "not found" in str(exc).lower() else 503
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    result: list[StoredChatMessage] = []
    for index, item in enumerate(stored):
        role = item.get("role")
        content = item.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str) or not content.strip():
            continue
        raw_id = item.get("id")
        timestamp = item.get("timestamp")
        result.append(StoredChatMessage(
            id=str(raw_id) if raw_id is not None else f"{session_id}:{index}",
            role=role,
            content=content,
            created_at=str(timestamp) if timestamp is not None else "",
            is_current_user=False,
            author_name="Hermes" if role == "assistant" else "Terminal user",
        ))
    return result


@app.post("/api/hermes/sessions/{session_id}/chat/stream", tags=["hermes"])
async def stream_hermes_session_chat(
    session_id: str,
    request: HermesSessionChatRequest,
    x_skavan_user_id: str | None = Header(default=None),
    hermes: HermesAdapter = Depends(get_hermes_adapter),
) -> StreamingResponse:
    user_id = require_platform_user_id(x_skavan_user_id)
    async with get_session_factory()() as session:
        await require_profile_access(session, user_id, request.profile)

    async def events() -> AsyncIterator[str]:
        try:
            source = hermes.stream_session(
                session_id, request.message,
                session_key=f"skavan:profile:{request.profile}", profile=request.profile,
            )
            async for content in stream_with_heartbeat(source):
                if content is None:
                    yield ": keep-alive\n\n"
                    continue
                yield format_sse("token", {"content": content})
            yield format_sse("done", {})
        except HermesError as exc:
            yield format_sse("error", {"message": str(exc)})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


@app.post("/api/chat", response_model=ChatResponse, tags=["chat"])
async def chat(
    request: ChatRequest,
    x_skavan_user_id: str | None = Header(default=None),
    hermes: HermesAdapter = Depends(get_hermes_adapter),
) -> ChatResponse:
    user_id = require_platform_user_id(x_skavan_user_id)
    async with get_session_factory()() as session:
        await require_profile_access(session, user_id, request.profile)
    try:
        content = await hermes.complete(
            [message.model_dump() for message in request.messages],
            session_key=f"skavan:profile:{request.profile}",
            profile=request.profile,
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
        await require_profile_access(session, user_id, request.profile)
        thread_id = await ensure_profile_context(session, user_id, request.profile) if request.thread_id is None else request.thread_id
        try:
            await require_profile_thread(session, request.profile, thread_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Thread not found") from exc
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
            source = hermes.stream(
                hermes_messages,
                session_key=f"skavan:profile:{request.profile}", profile=request.profile,
            )
            async for content in stream_with_heartbeat(source):
                if content is None:
                    yield ": keep-alive\n\n"
                    continue
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
