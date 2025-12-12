# This import is crucial to ensure that the configuration is loaded before the db module is accessed.
import src.configs.config

import pytest
from sqlalchemy.sql import text
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger

from src.configs.db import get_async_engine

async_engine = get_async_engine()

@pytest.mark.asyncio
async def test_database_connection():
    """
    Tests the database connection by connecting and executing a simple query.
    This test will fail if the database is not accessible with the configured credentials.
    """
    logger.info("--- Starting Database Connection Test ---")
    try:
        async with async_engine.connect() as connection:
            logger.info("Successfully connected to the database.")
            
            # Execute a simple query
            result = await connection.execute(text("SELECT 1"))
            
            # Check if the result is as expected
            assert result.scalar() == 1, "Database connection test failed: Query 'SELECT 1' did not return 1."
            
            logger.success("Database connection test successful! Query 'SELECT 1' returned 1.")

    except SQLAlchemyError as e:
        logger.error(f"Database connection failed due to SQLAlchemyError: {e}")
        pytest.fail(f"Database connection failed with SQLAlchemyError: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during DB connection test: {e}")
        pytest.fail(f"An unexpected error occurred during DB connection test: {e}")
    finally:
        # Dispose the engine to close all connections gracefully
        await async_engine.dispose()
        logger.info("--- Database Connection Test Finished ---")
