"""
Async SQLAlchemy engine for the Postgres audit trail and feedback loop.

Falls back gracefully when Postgres is unreachable — callers should
treat every DB write as fire-and-forget, never blocking the pipeline.
"""
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def _async_url(url: str) -> str:
    """Convert a sync postgres:// URL to the asyncpg dialect."""
    for prefix, replacement in (
        ("postgresql+psycopg2://", "postgresql+asyncpg://"),
        ("postgresql://", "postgresql+asyncpg://"),
    ):
        if url.startswith(prefix):
            return url.replace(prefix, replacement, 1)
    # sqlite URLs for testing: ensure aiosqlite dialect
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return url


_engine = None
_session_factory: async_sessionmaker | None = None


def init_db(url: str | None = None) -> None:
    """Initialise the engine. Call once at startup (or in tests with a custom URL)."""
    global _engine, _session_factory
    from config import settings

    db_url = _async_url(url or settings.postgres_url)

    connect_args = {}
    if "sqlite" in db_url:
        connect_args = {"check_same_thread": False}

    _engine = create_async_engine(
        db_url,
        echo=False,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    _session_factory = async_sessionmaker(
        _engine, expire_on_commit=False, class_=AsyncSession
    )


def get_session_factory() -> async_sessionmaker:
    if _session_factory is None:
        init_db()
    return _session_factory


async def create_all_tables() -> None:
    """Create tables directly (dev / test path). Production uses Alembic."""
    from models.audit_model import AuditLog, VerifiedInteraction  # noqa: F401 — registers models

    factory = get_session_factory()
    async with factory.kw["bind"].begin() as conn:  # type: ignore[index]
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """FastAPI dependency: yield a session, auto-commit/rollback."""
    factory = get_session_factory()
    async with factory() as session:
        yield session
