from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from typing import List, Dict, Any, Optional
from loguru import logger

from src.models.tables import conversations_table, messages_table
from src.schemas.conversation import ConversationCreateSchema

async def create_conversation(db: AsyncSession, conv: ConversationCreateSchema) -> Dict[str, Any]:
    """Creates a new conversation in the database.

    Args:
        db (AsyncSession): The database session.
        conv (ConversationCreateSchema): The Pydantic model containing the data for the new conversation.

    Returns:
        Dict[str, Any]: A dictionary representing the newly created conversation record.
    """
    query = insert(conversations_table).values(
        user_id=conv.user_id,
        name=conv.name
    ).returning(conversations_table)
    
    logger.info("Executing insert query for new conversation...")
    result = await db.execute(query)
    logger.info("Insert query executed.")
    
    created_conv = result.first()
    
    logger.info("Committing transaction...")
    await db.commit()
    logger.info("Transaction committed.")
    
    return created_conv._asdict()



async def get_conversation(db: AsyncSession, conversation_id: int) -> Optional[Dict[str, Any]]:
    """Fetches a single conversation by its ID.

    Args:
        db (AsyncSession): The database session.
        conversation_id (int): The ID of the conversation to fetch.

    Returns:
        Optional[Dict[str, Any]]: A dictionary representing the conversation, or None if not found.
    """
    query = select(conversations_table).where(conversations_table.c.id == conversation_id)
    result = await db.execute(query)
    conv = result.first()
    return conv._asdict() if conv else None



async def get_conversations_by_user(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 10) -> List[Dict[str, Any]]:
    """Fetches a paginated list of conversations for a user, including a message preview.

    The preview is the content of the first user message in the conversation.

    Args:
        db (AsyncSession): The database session.
        user_id (int): The ID of the user whose conversations to fetch.
        skip (int): The number of conversations to skip for pagination.
        limit (int): The maximum number of conversations to return.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, where each dictionary
                               represents a conversation with an added 'preview' field.
    """
    # Subquery to get the first user message content as preview
    preview_subquery = (
        select(messages_table.c.content)
        .where(
            messages_table.c.conversation_id == conversations_table.c.id,
            messages_table.c.role == 'user'
        )
        .order_by(messages_table.c.created_at.asc())
        .limit(1)
        .scalar_subquery()
        .label("preview")
    )

    query = (
        select(conversations_table, preview_subquery)
        .where(conversations_table.c.user_id == user_id)
        .order_by(conversations_table.c.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    
    result = await db.execute(query)
    conversations = result.mappings().all()
    return [dict(conv) for conv in conversations]
