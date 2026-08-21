import os

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine


def _database_url() -> str:
    value = os.getenv("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL is required")
    return value


engine: AsyncEngine | None = None
session_factory: async_sessionmaker | None = None


def _session_factory() -> async_sessionmaker:
    global engine, session_factory
    if session_factory is None:
        engine = create_async_engine(_database_url(), pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return session_factory


async def get_database_session():
    async with _session_factory()() as session:
        yield session
