import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# Ensure config is loaded before other imports
import src.configs.config
from src.configs.db import DATABASE_URL
from src.models.tables import metadata
from src.schemas.user import UserCreateSchema
from src.schemas.conversation import ConversationCreateSchema
from src.schemas.message import MessageCreateSchema
from src.dao import user_dao, conversation_dao, message_dao

@pytest.fixture(scope="function")
async def managed_db_session():
    """
    A fixture that provides a clean database and a session for each test.
    """
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)
        await conn.run_sync(metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session
    
    await engine.dispose()

@pytest.mark.asyncio
async def test_create_and_get_messages(managed_db_session: AsyncSession):
    """
    Test creating and retrieving messages for a conversation.
    """
    # 1. Create a user and a conversation
    user = await user_dao.create_user(managed_db_session, user=UserCreateSchema(username="msg_test_user"))
    conv_to_create = ConversationCreateSchema(user_id=user["id"])
    conv = await conversation_dao.create_conversation(managed_db_session, conv=conv_to_create)
    conv_id = conv["id"]

    # 2. Create two messages in this conversation
    msg1_to_create = MessageCreateSchema(conversation_id=conv_id, role="user", content="Hello")
    await message_dao.create_message(managed_db_session, message=msg1_to_create)

    msg2_to_create = MessageCreateSchema(conversation_id=conv_id, role="assistant", content="Hi there!")
    await message_dao.create_message(managed_db_session, message=msg2_to_create)

    # 3. Retrieve the messages for this conversation
    messages = await message_dao.get_messages_by_conversation(managed_db_session, conversation_id=conv_id)

    # 4. Assertions
    assert messages is not None
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Hi there!"

@pytest.mark.asyncio
async def test_get_messages_for_empty_conversation(managed_db_session: AsyncSession):
    """
    Test retrieving messages for a conversation that has none.
    """
    # 1. Create a user and a conversation
    user = await user_dao.create_user(managed_db_session, user=UserCreateSchema(username="empty_conv_user"))
    conv_to_create = ConversationCreateSchema(user_id=user["id"])
    conv = await conversation_dao.create_conversation(managed_db_session, conv=conv_to_create)
    conv_id = conv["id"]

    # 2. Retrieve messages
    messages = await message_dao.get_messages_by_conversation(managed_db_session, conversation_id=conv_id)

    # 3. Assertions
    assert messages is not None
    assert len(messages) == 0
