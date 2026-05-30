from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from supabase import create_client, Client
from app.config import get_settings
import asyncpg

settings = get_settings()

# ── Parse DB URL for asyncpg (strip the +asyncpg dialect) ──
_raw_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")


async def _create_connection():
    """Create an asyncpg connection with statement_cache_size=0 for pgbouncer."""
    return await asyncpg.connect(_raw_url, statement_cache_size=0)


# ── SQLAlchemy Async Engine (for direct DB operations) ──
# Use NullPool + async_creator: ensures every connection has
# statement_cache_size=0 BEFORE any queries run (including
# SQLAlchemy's internal `select pg_catalog.version()`).
engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    poolclass=NullPool,
    async_creator=_create_connection,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ── Supabase Client (service role for admin operations) ──
def get_supabase_admin() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_supabase_client() -> Client:
    return create_client(settings.supabase_url, settings.resolved_anon_key)
