from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from typing import List, Dict, Any, Optional

from src.models.tables import messages_table
from src.schemas.message import MessageCreateSchema

async def create_message(db: AsyncSession, message: MessageCreateSchema) -> Dict[str, Any]:
    """Creates a new message in a conversation.

    Args:
        db (AsyncSession): The database session.
        message (MessageCreateSchema): The Pydantic model containing the message data.

    Returns:
        Dict[str, Any]: A dictionary representing the newly created message record.
    """
    query = insert(messages_table).values(
        conversation_id=message.conversation_id,
        role=message.role,
        content=message.content
    ).returning(messages_table)
    
    result = await db.execute(query)
    created_message = result.first()
    await db.commit()
    return created_message._asdict()



async def get_messages_by_conversation(
    db: AsyncSession, 
    conversation_id: int, 
    skip: int = 0,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Fetches messages for a specific conversation with pagination.

    Args:
        db (AsyncSession): The database session.
        conversation_id (int): The ID of the conversation to fetch messages for.
        skip (int): The number of messages to skip for pagination.
        limit (Optional[int]): The maximum number of messages to return. If provided,
                               fetches the most recent messages (descending order).
                               Otherwise, fetches all messages (ascending order).

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, where each dictionary represents a message.
    """
    query = select(messages_table).where(
        messages_table.c.conversation_id == conversation_id
    )
    
    if limit:
        query = query.order_by(messages_table.c.created_at.desc()).offset(skip).limit(limit)
    else:
        query = query.order_by(messages_table.c.created_at)
    
    result = await db.execute(query)
    messages = result.fetchall()
    return [msg._asdict() for msg in messages]
