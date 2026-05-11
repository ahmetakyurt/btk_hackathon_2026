from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

_settings = get_settings()

# Supabase transaction pooler (pgbouncer, port 6543) does not support
# server-side prepared statements — disable asyncpg's statement cache.
_connect_args: dict = {}
if "asyncpg" in _settings.database_url:
    _connect_args = {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "timeout": 10,  # fail fast if Supabase is unreachable (avoids 502 hanging)
    }

engine = create_async_engine(
    _settings.database_url,
    echo=False,
    future=True,
    connect_args=_connect_args,
    pool_pre_ping=True,
    pool_timeout=10,
)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
