import os
from typing import Any

import httpx2


class TelegramPairingError(RuntimeError):
    """A safe, user-facing failure from Hermes Telegram pairing."""


class HermesTelegramPairingClient:
    def __init__(
        self, base_url: str, username: str, password: str,
        *, timeout_seconds: float = 15.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_environment(cls) -> "HermesTelegramPairingClient":
        base_url = os.getenv("HERMES_DASHBOARD_INTERNAL_URL", "http://hermes:9119")
        username = os.getenv("HERMES_DASHBOARD_BASIC_AUTH_USERNAME", "")
        password = os.getenv("HERMES_DASHBOARD_BASIC_AUTH_PASSWORD", "")
        if not username or not password:
            raise TelegramPairingError("Telegram pairing is not configured")
        return cls(base_url, username, password)

    @staticmethod
    def runtime_profile(profile: str) -> str | None:
        if profile == "personal":
            return None
        if profile == "work":
            return "work"
        raise TelegramPairingError("Unknown Hermes profile")

    async def approve(self, code: str, *, profile: str) -> dict[str, str]:
        payload: dict[str, Any] = {
            "platform": "telegram",
            "code": code.strip().upper(),
        }
        runtime_profile = self.runtime_profile(profile)
        if runtime_profile:
            payload["profile"] = runtime_profile
        try:
            async with httpx2.AsyncClient(
                auth=(self.username, self.password), timeout=self.timeout_seconds,
            ) as client:
                response = await client.post(
                    f"{self.base_url}/api/pairing/approve", json=payload,
                )
        except httpx2.HTTPError as exc:
            raise TelegramPairingError("Hermes Telegram pairing is unavailable") from exc
        if response.status_code == 404:
            raise TelegramPairingError("Pairing code is invalid or expired")
        if response.status_code == 429:
            raise TelegramPairingError("Too many pairing attempts; try again later")
        if response.status_code >= 400:
            raise TelegramPairingError("Hermes rejected the Telegram pairing request")
        body = response.json()
        user = body.get("user") if isinstance(body, dict) else None
        user_id = str(user.get("user_id") or "").strip() if isinstance(user, dict) else ""
        if not user_id:
            raise TelegramPairingError("Hermes returned an incomplete pairing result")
        return {
            "external_subject": user_id,
            "username": str(user.get("user_name") or "").strip(),
        }

    async def revoke(self, external_subject: str, *, profile: str) -> None:
        payload: dict[str, Any] = {
            "platform": "telegram",
            "user_id": external_subject,
        }
        runtime_profile = self.runtime_profile(profile)
        if runtime_profile:
            payload["profile"] = runtime_profile
        try:
            async with httpx2.AsyncClient(
                auth=(self.username, self.password), timeout=self.timeout_seconds,
            ) as client:
                response = await client.post(
                    f"{self.base_url}/api/pairing/revoke", json=payload,
                )
        except httpx2.HTTPError as exc:
            raise TelegramPairingError("Hermes Telegram pairing is unavailable") from exc
        if response.status_code not in {200, 404}:
            raise TelegramPairingError("Hermes rejected the Telegram unlink request")
