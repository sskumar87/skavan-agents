from __future__ import annotations

import os
from dataclasses import dataclass
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

    async def health(self) -> bool:
        try:
            async with httpx2.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health", headers=self.headers)
            return response.status_code == 200
        except (httpx2.HTTPError, HermesError):
            return False

    async def complete(self, messages: list[dict[str, str]]) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        try:
            async with httpx2.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=self.headers,
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
