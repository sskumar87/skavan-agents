from __future__ import annotations

import json
import os
from dataclasses import dataclass
from collections.abc import AsyncIterator
from typing import Any

import httpx2


class HermesError(RuntimeError):
    """A user-safe Hermes integration failure."""


@dataclass(frozen=True)
class HermesAdapter:
    base_url: str
    api_key: str
    model: str = "hermes-agent"

    @classmethod
    def from_environment(cls) -> "HermesAdapter":
        return cls(
            base_url=os.getenv("HERMES_API_BASE_URL", "http://hermes:8642").rstrip("/"),
            api_key=os.getenv("HERMES_API_SERVER_KEY", ""),
            model=os.getenv("HERMES_MODEL", "hermes-agent"),
        )

    @property
    def headers(self) -> dict[str, str]:
        if len(self.api_key) < 16:
            raise HermesError("Hermes is not configured.")
        return {"Authorization": f"Bearer {self.api_key}"}

    def request_headers(self, session_key: str | None = None) -> dict[str, str]:
        headers = self.headers
        if session_key:
            headers["X-Hermes-Session-Key"] = session_key
        return headers

    async def health(self) -> bool:
        try:
            async with httpx2.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health", headers=self.headers)
            return response.status_code == 200
        except (httpx2.HTTPError, HermesError):
            return False

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        session_key: str | None = None,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        try:
            async with httpx2.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=self.request_headers(session_key),
                    json=payload,
                )
            response.raise_for_status()
            data: Any = response.json()
            content = data["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise HermesError("Hermes returned an empty response.")
            return content
        except httpx2.TimeoutException as exc:
            raise HermesError("Hermes timed out while processing the message.") from exc
        except httpx2.HTTPStatusError as exc:
            raise HermesError("Hermes rejected the request.") from exc
        except (httpx2.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise HermesError("Hermes is currently unavailable.") from exc

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        session_key: str,
    ) -> AsyncIterator[str]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        received_content = False
        event_name: str | None = None
        try:
            async with httpx2.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/v1/chat/completions",
                    headers=self.request_headers(session_key),
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("event:"):
                            event_name = line[6:].strip()
                            continue
                        if not line:
                            event_name = None
                            continue
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        if event_name:
                            continue
                        chunk: Any = json.loads(data)
                        content = chunk["choices"][0]["delta"].get("content")
                        if isinstance(content, str) and content:
                            received_content = True
                            yield content
            if not received_content:
                raise HermesError("Hermes returned an empty response.")
        except httpx2.TimeoutException as exc:
            raise HermesError("Hermes timed out while processing the message.") from exc
        except httpx2.HTTPStatusError as exc:
            raise HermesError("Hermes rejected the request.") from exc
        except HermesError:
            raise
        except (httpx2.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise HermesError("Hermes is currently unavailable.") from exc
