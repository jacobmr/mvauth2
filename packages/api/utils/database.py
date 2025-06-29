from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from .config import settings
import os

# Create async engine with proper configuration for Supabase
if settings.database_url.startswith("sqlite"):
    database_url = settings.database_url.replace("sqlite://", "sqlite+aiosqlite://")
    engine_kwargs = {"echo": False}
elif settings.database_url.startswith("postgresql"):
    database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    # Add SSL and connection settings for Supabase
    engine_kwargs = {
        "echo": False,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "connect_args": {
            "ssl": "require",
            "server_settings": {
                "application_name": "mvauth2_api",
            }
        }
    }
else:
    database_url = settings.database_url
    engine_kwargs = {"echo": False}

engine = create_async_engine(database_url, **engine_kwargs)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

async def init_db():
    try:
        print(f"Attempting to connect to database: {settings.database_url[:50]}...")
        async with engine.begin() as conn:
            # Test connection first
            result = await conn.execute(text("SELECT 1"))
            print("Database connection successful")
            
            await conn.run_sync(Base.metadata.create_all)
        print("Database tables created successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")
        print(f"Database URL being used: {settings.database_url}")
        # Don't raise the error - let the app start even if DB is not available
        pass

async def get_db():
    async with async_session() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()