from typing import Literal

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.hermes import HermesAdapter, HermesError


app = FastAPI(title="Skavan Agents API", version="0.1.0")


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
