from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from .config import settings

# Create async engine
if settings.database_url.startswith("sqlite"):
    database_url = settings.database_url.replace("sqlite://", "sqlite+aiosqlite://")
elif settings.database_url.startswith("postgresql"):
    database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
else:
    database_url = settings.database_url

engine = create_async_engine(database_url, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()