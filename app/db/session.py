from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

from app.db.base import Base

from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL
# Stealth fix: Ensure asyncpg driver is used even if user provides standard postgres:// URL
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Enable pooling and disable echo for production stability
IS_PROD = os.getenv("RENDER") is not None
engine = create_async_engine(
    DATABASE_URL, 
    echo=not IS_PROD,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

from sqlalchemy import text

async def check_db_connection() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"DATABASE CONNECTION ERROR: {e}")
        return False

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
