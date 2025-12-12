import os
import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from loguru import logger

from src.configs.config import yaml_configs

def build_db_url(db_config: dict) -> str | None:
    """Builds the database URL from configuration."""
    user = db_config.get("user")
    password_env_var = db_config.get("password_env_var")

    password = os.getenv(password_env_var)

    if not all([user, password]):
        logger.error(f"DB user not in config or password not in env var ('{password_env_var}').")
        return None

    host = db_config.get("host")
    port = db_config.get("port")
    dbname = db_config.get("dbname")

    if not all([host, port, dbname]):
        logger.error("DB host, port, or dbname missing in config.")
        return None

    if host.startswith("/"):
        # Unix socket connection
        return f"postgresql+asyncpg://{user}:{password}@/{dbname}?host={host}"
    else:
        # TCP connection
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{dbname}"

# --- Database Engine and Session Setup ---

# Default to a dummy URL to prevent crashes on import if config is missing.
DATABASE_URL = "postgresql+asyncpg://dummy:dummy@localhost/dummy"
db_config = yaml_configs.get("database") if yaml_configs else None

if db_config:
    url = build_db_url(db_config)
    if url:
        DATABASE_URL = url
        logger.info("Database connection URL built successfully.")
    else:
        logger.error("Failed to build database URL. Using dummy URL.")
else:
    logger.warning("Database configuration not found, using dummy URL.")

from functools import lru_cache

@lru_cache()
def get_async_engine():
    """
    Returns a cached async engine instance.
    The engine is created on the first call and reused on subsequent calls
    within the same event loop.
    """
    logger.info("Creating new async engine instance.")
    return create_async_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        echo=False,  # Set to True to see generated SQL statements
    )

# Create a sessionmaker for creating AsyncSession instances
# The bind is deferred until the engine is created.
AsyncSessionFactory = sessionmaker(
    bind=get_async_engine(),
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for declarative models
Base = declarative_base()

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get a database session."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
        finally:
            await session.close()

logger.info("Database engine and session factory configured.")
