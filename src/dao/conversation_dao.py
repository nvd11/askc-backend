from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from typing import List
from loguru import logger

from src.models.tables import conversations_table, messages_table
from src.schemas.conversation import ConversationCreateSchema

async def create_conversation(db: AsyncSession, conv: ConversationCreateSchema) -> dict:
    """
    Creates a new conversation for a user.
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

async def get_conversation(db: AsyncSession, conversation_id: int) -> dict | None:
    """
    Fetches a single conversation by its ID.
    """
    query = select(conversations_table).where(conversations_table.c.id == conversation_id)
    result = await db.execute(query)
    conv = result.first()
    return conv._asdict() if conv else None

async def get_conversations_by_user(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 10) -> List[dict]:
    """
    Fetches all conversations for a specific user with preview.
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
