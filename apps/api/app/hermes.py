from __future__ import annotations

import json
import os
from dataclasses import dataclass
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import quote

import httpx2


class HermesError(RuntimeError):
    """A user-safe Hermes integration failure."""


@dataclass(frozen=True)
class HermesAdapter:
    base_url: str
    api_key: str
    model: str = "hermes-agent"
    work_api_key: str = ""

    @classmethod
    def from_environment(cls) -> "HermesAdapter":
        return cls(
            base_url=os.getenv("HERMES_API_BASE_URL", "http://hermes:8642").rstrip("/"),
            api_key=os.getenv("HERMES_API_SERVER_KEY", ""),
            model=os.getenv("HERMES_MODEL", "hermes-agent"),
            work_api_key=os.getenv("HERMES_WORK_API_SERVER_KEY", ""),
        )

    @property
    def headers(self) -> dict[str, str]:
        if len(self.api_key) < 16:
            raise HermesError("Hermes is not configured.")
        return {"Authorization": f"Bearer {self.api_key}"}

    def request_headers(
        self, session_key: str | None = None, profile: str | None = None,
    ) -> dict[str, str]:
        api_key = {
            # Personal is the product name for Hermes' default profile.
            "personal": self.api_key,
            "work": self.work_api_key,
        }.get(profile, self.api_key)
        if len(api_key) < 16:
            raise HermesError("Hermes profile is not configured.")
        headers = {"Authorization": f"Bearer {api_key}"}
        if session_key:
            headers["X-Hermes-Session-Key"] = session_key
        return headers

    def endpoint(self, path: str, profile: str | None = None) -> str:
        # Hermes exposes the default profile without a /p/<name> prefix.
        runtime_profile = None if profile == "personal" else profile
        prefix = f"/p/{quote(runtime_profile, safe='')}" if runtime_profile else ""
        return f"{self.base_url}{prefix}{path}"

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
        profile: str | None = None,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        try:
            async with httpx2.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    self.endpoint("/v1/chat/completions", profile),
                    headers=self.request_headers(session_key, profile),
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
        profile: str,
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
                    self.endpoint("/v1/chat/completions", profile),
                    headers=self.request_headers(session_key, profile),
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

    async def list_sessions(self, *, profile: str) -> list[dict[str, Any]]:
        try:
            async with httpx2.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    self.endpoint("/api/sessions", profile),
                    headers=self.request_headers(profile=profile),
                    params={"limit": 200, "include_children": "true"},
                )
            response.raise_for_status()
            data: Any = response.json().get("data", [])
            if not isinstance(data, list):
                raise TypeError("Hermes returned an invalid session list")
            return [item for item in data if isinstance(item, dict)]
        except httpx2.HTTPStatusError as exc:
            raise HermesError("Hermes rejected the session request.") from exc
        except (httpx2.HTTPError, AttributeError, TypeError, ValueError) as exc:
            raise HermesError("Hermes sessions are currently unavailable.") from exc

    async def create_session(
        self, session_id: str, *, profile: str, source: str = "skavan",
    ) -> str:
        try:
            async with httpx2.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    self.endpoint("/api/sessions", profile),
                    headers=self.request_headers(profile=profile),
                    json={"id": session_id, "source": source},
                )
            if response.status_code == 409:
                return session_id
            response.raise_for_status()
            data: Any = response.json().get("session", {})
            created_id = data.get("id") if isinstance(data, dict) else None
            if created_id != session_id:
                raise TypeError("Hermes returned an invalid session")
            return created_id
        except httpx2.HTTPStatusError as exc:
            raise HermesError("Hermes rejected the session creation request.") from exc
        except (httpx2.HTTPError, AttributeError, TypeError, ValueError) as exc:
            raise HermesError("Hermes sessions are currently unavailable.") from exc

    async def rename_session(
        self, session_id: str, title: str, *, profile: str,
    ) -> dict[str, Any]:
        """Apply Hermes' native session title mutation used by `/title`."""
        encoded_id = quote(session_id, safe="")
        try:
            async with httpx2.AsyncClient(timeout=15.0) as client:
                response = await client.patch(
                    self.endpoint(f"/api/sessions/{encoded_id}", profile),
                    headers=self.request_headers(profile=profile),
                    json={"title": title},
                )
            response.raise_for_status()
            data: Any = response.json().get("session", {})
            if not isinstance(data, dict) or data.get("id") != session_id:
                raise TypeError("Hermes returned an invalid session")
            return data
        except httpx2.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise HermesError("Hermes session was not found.") from exc
            raise HermesError("Hermes rejected the session title.") from exc
        except (httpx2.HTTPError, AttributeError, TypeError, ValueError) as exc:
            raise HermesError("Hermes sessions are currently unavailable.") from exc

    async def session_messages(
        self, session_id: str, *, profile: str,
    ) -> list[dict[str, Any]]:
        encoded_id = quote(session_id, safe="")
        try:
            async with httpx2.AsyncClient(timeout=15.0) as client:
                messages: list[dict[str, Any]] = []
                offset = 0
                page_size = 500
                while True:
                    response = await client.get(
                        self.endpoint(f"/api/sessions/{encoded_id}/messages", profile),
                        headers=self.request_headers(profile=profile),
                        params={"limit": page_size, "offset": offset, "order": "oldest"},
                    )
                    response.raise_for_status()
                    data: Any = response.json().get("data", [])
                    if not isinstance(data, list):
                        raise TypeError("Hermes returned invalid session messages")
                    page = [item for item in data if isinstance(item, dict)]
                    messages.extend(page)
                    if len(data) < page_size:
                        return messages
                    offset += len(data)
                    if offset >= 10_000:
                        raise TypeError("Hermes session history exceeds the supported limit")
        except httpx2.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise HermesError("Hermes session was not found.") from exc
            raise HermesError("Hermes rejected the session request.") from exc
        except (httpx2.HTTPError, AttributeError, TypeError, ValueError) as exc:
            raise HermesError("Hermes sessions are currently unavailable.") from exc

    async def stream_session(
        self,
        session_id: str,
        message: str,
        *,
        session_key: str,
        profile: str,
    ) -> AsyncIterator[str]:
        encoded_id = quote(session_id, safe="")
        received_content = False
        event_name: str | None = None
        try:
            async with httpx2.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    self.endpoint(f"/api/sessions/{encoded_id}/chat/stream", profile),
                    headers=self.request_headers(session_key, profile),
                    json={"message": message},
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
                        payload: Any = json.loads(line[5:].strip())
                        if event_name == "error":
                            detail = payload.get("message") if isinstance(payload, dict) else None
                            raise HermesError(detail if isinstance(detail, str) else "Hermes session failed.")
                        if event_name == "assistant.completed" and not received_content and isinstance(payload, dict):
                            content = payload.get("content")
                            if isinstance(content, str) and content:
                                received_content = True
                                yield content
                            continue
                        if event_name != "assistant.delta" or not isinstance(payload, dict):
                            continue
                        content = payload.get("delta")
                        if isinstance(content, str) and content:
                            received_content = True
                            yield content
            if not received_content:
                raise HermesError("Hermes returned an empty response.")
        except httpx2.TimeoutException as exc:
            raise HermesError("Hermes timed out while processing the session.") from exc
        except httpx2.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise HermesError("Hermes session was not found.") from exc
            raise HermesError("Hermes rejected the session request.") from exc
        except HermesError:
            raise
        except (httpx2.HTTPError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise HermesError("Hermes sessions are currently unavailable.") from exc
