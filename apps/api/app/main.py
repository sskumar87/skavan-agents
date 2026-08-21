import json
from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_database_session
from app.hermes import HermesAdapter, HermesError
from app.identity import OidcTokenVerifier, synchronize_user


app = FastAPI(title="Skavan Agents API", version="0.1.0")


class PlatformUser(BaseModel):
    id: str
    display_name: str
    email: str | None
    preferences: dict[str, object]


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
    hermes: HermesAdapter = Depends(get_hermes_adapter),
) -> StreamingResponse:
    messages = [message.model_dump() for message in request.messages]

    async def events() -> AsyncIterator[str]:
        try:
            async for content in hermes.stream(messages):
                yield format_sse("token", {"content": content})
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
