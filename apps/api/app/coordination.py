"""Extensible per-conversation turn coordination.

The initial implementation is intentionally process-local because Phase 1 runs
one FastAPI instance.  Callers depend on the coordinator contract, allowing a
shared-filesystem or distributed implementation to replace it without changing
chat endpoints.
"""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator


class SessionBusyError(RuntimeError):
    """The session already has a writer and its single queue slot is occupied."""


class SessionQueueTimeoutError(RuntimeError):
    """The queued turn did not acquire the session writer within the deadline."""


@dataclass
class _SessionState:
    lock: asyncio.Lock
    waiters: int = 0


class InProcessSessionTurnCoordinator:
    """Serialize writers per session with one bounded pending turn."""

    def __init__(self, *, queue_timeout_seconds: float = 30.0, max_waiters: int = 1):
        self.queue_timeout_seconds = queue_timeout_seconds
        self.max_waiters = max_waiters
        self._states: dict[str, _SessionState] = {}
        self._guard = asyncio.Lock()

    async def is_busy(self, key: str) -> bool:
        async with self._guard:
            state = self._states.get(key)
            return bool(state and state.lock.locked())

    @asynccontextmanager
    async def turn(self, key: str) -> AsyncIterator[bool]:
        async with self._guard:
            state = self._states.setdefault(key, _SessionState(lock=asyncio.Lock()))
            queued = state.lock.locked()
            if queued and state.waiters >= self.max_waiters:
                raise SessionBusyError("This chat is busy and already has a queued message.")
            if queued:
                state.waiters += 1

        try:
            try:
                await asyncio.wait_for(
                    state.lock.acquire(), timeout=self.queue_timeout_seconds,
                )
            except TimeoutError as exc:
                raise SessionQueueTimeoutError(
                    "This chat is still busy. Please try again shortly."
                ) from exc
            try:
                yield queued
            finally:
                state.lock.release()
        finally:
            async with self._guard:
                if queued:
                    state.waiters -= 1
                if not state.lock.locked() and state.waiters == 0:
                    self._states.pop(key, None)


session_turn_coordinator = InProcessSessionTurnCoordinator()
