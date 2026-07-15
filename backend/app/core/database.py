from typing import AsyncGenerator

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import declarative_base

from app.core.config import settings


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


# Determine active database based on APP_ENV
db_url = settings.DATABASE_URL
if settings.APP_ENV in ("test", "testing"):
    db_url = settings.TEST_DATABASE_URL

# SQLAlchemy async ORM engine using asyncpg
engine = create_async_engine(db_url, future=True, echo=settings.APP_DEBUG, pool_pre_ping=True)

# Async sessionmaker
async_session_maker = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining an async database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
