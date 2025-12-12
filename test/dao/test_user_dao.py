import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.exc import IntegrityError

# Ensure config is loaded before other imports
import src.configs.config
from src.configs.db import DATABASE_URL
from src.models.tables import metadata
from src.schemas.user import UserCreateSchema
from src.dao import user_dao

@pytest.fixture(scope="function")
async def managed_db_session():
    """
    A fixture that provides a clean database and a session for each test.
    It handles setup (engine creation, table creation) and teardown (engine disposal).
    """
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)
        await conn.run_sync(metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session
    
    await engine.dispose()

@pytest.mark.asyncio
async def test_create_user(managed_db_session: AsyncSession):
    """
    Test creating a new user.
    """
    user_to_create = UserCreateSchema(username="testuser", email="test@example.com")
    created_user = await user_dao.create_user(managed_db_session, user=user_to_create)

    assert created_user is not None
    assert created_user["username"] == "testuser"
    assert created_user["email"] == "test@example.com"
    assert "id" in created_user
    assert "created_at" in created_user

@pytest.mark.asyncio
async def test_get_user_by_username(managed_db_session: AsyncSession):
    """
    Test fetching an existing user by username.
    """
    # First, create a user to fetch
    user_to_create = UserCreateSchema(username="testuser2", email="test2@example.com")
    await user_dao.create_user(managed_db_session, user=user_to_create)

    # Now, fetch the user
    fetched_user = await user_dao.get_user_by_username(managed_db_session, username="testuser2")

    assert fetched_user is not None
    assert fetched_user["username"] == "testuser2"
    assert fetched_user["email"] == "test2@example.com"

@pytest.mark.asyncio
async def test_get_non_existent_user(managed_db_session: AsyncSession):
    """
    Test fetching a user that does not exist.
    """
    fetched_user = await user_dao.get_user_by_username(managed_db_session, username="nonexistent")
    assert fetched_user is None

@pytest.mark.asyncio
async def test_create_duplicate_user_fails(managed_db_session: AsyncSession):
    """
    Test that creating a user with a duplicate username raises an IntegrityError.
    """
    user_to_create = UserCreateSchema(username="duplicateuser")
    await user_dao.create_user(managed_db_session, user=user_to_create)

    # Attempt to create the same user again
    with pytest.raises(IntegrityError):
        await user_dao.create_user(managed_db_session, user=user_to_create)
