import asyncio

import pytest

from app.coordination import (
    InProcessSessionTurnCoordinator,
    SessionBusyError,
    SessionQueueTimeoutError,
)


def test_different_sessions_can_run_concurrently() -> None:
    coordinator = InProcessSessionTurnCoordinator()

    async def run() -> list[bool]:
        entered: list[bool] = []
        async with coordinator.turn("personal:first") as queued_first:
            async with coordinator.turn("personal:second") as queued_second:
                entered.extend([queued_first, queued_second])
        return entered

    assert asyncio.run(run()) == [False, False]


def test_same_session_serializes_one_pending_turn() -> None:
    coordinator = InProcessSessionTurnCoordinator(queue_timeout_seconds=1)

    async def run() -> list[str]:
        first_entered = asyncio.Event()
        release_first = asyncio.Event()
        order: list[str] = []

        async def first():
            async with coordinator.turn("work:shared") as queued:
                assert not queued
                order.append("first")
                first_entered.set()
                await release_first.wait()

        async def second():
            await first_entered.wait()
            async with coordinator.turn("work:shared") as queued:
                assert queued
                order.append("second")

        first_task = asyncio.create_task(first())
        second_task = asyncio.create_task(second())
        await first_entered.wait()
        await asyncio.sleep(0)
        release_first.set()
        await asyncio.gather(first_task, second_task)
        return order

    assert asyncio.run(run()) == ["first", "second"]


def test_same_session_rejects_more_than_one_pending_turn() -> None:
    coordinator = InProcessSessionTurnCoordinator(queue_timeout_seconds=1)

    async def run() -> None:
        first_entered = asyncio.Event()
        release_first = asyncio.Event()

        async def first():
            async with coordinator.turn("work:shared"):
                first_entered.set()
                await release_first.wait()

        async def second():
            await first_entered.wait()
            async with coordinator.turn("work:shared"):
                return None

        first_task = asyncio.create_task(first())
        second_task = asyncio.create_task(second())
        await first_entered.wait()
        await asyncio.sleep(0)
        with pytest.raises(SessionBusyError):
            async with coordinator.turn("work:shared"):
                pass
        release_first.set()
        await asyncio.gather(first_task, second_task)

    asyncio.run(run())


def test_queued_turn_times_out() -> None:
    coordinator = InProcessSessionTurnCoordinator(queue_timeout_seconds=0.01)

    async def run() -> None:
        async with coordinator.turn("personal:shared"):
            with pytest.raises(SessionQueueTimeoutError):
                async with coordinator.turn("personal:shared"):
                    pass

    asyncio.run(run())

