from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.configs.db import get_db_session
from src.schemas.conversation import ConversationSchema, ConversationCreateSchema, ConversationWithMessagesSchema
from src.schemas.message import MessageSchema
from src.dao import conversation_dao, message_dao

router = APIRouter(
    prefix="/api/v1",
    tags=["Conversations"],
)

@router.post("/conversations/", response_model=ConversationSchema)
async def create_conversation_endpoint(
    conv: ConversationCreateSchema, db: AsyncSession = Depends(get_db_session)
):
    """
    Create a new conversation for a user.
    """
    # In a real app, you'd verify the user exists first.
    created_conv = await conversation_dao.create_conversation(db=db, conv=conv)
    return created_conv

@router.get("/users/{user_id}/conversations", response_model=List[ConversationSchema])
async def get_user_conversations_endpoint(
    user_id: int, skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db_session)
):
    """
    Get all conversations for a specific user.
    """
    conversations = await conversation_dao.get_conversations_by_user(
        db=db, user_id=user_id, skip=skip, limit=limit
    )
    return conversations

@router.get("/conversations/{conversation_id}", response_model=ConversationWithMessagesSchema)
async def get_conversation_with_messages_endpoint(
    conversation_id: int, db: AsyncSession = Depends(get_db_session)
):
    """
    Get a single conversation with all its messages.
    """
    # This is not the most efficient way, but it's simple.
    # A single query with a JOIN would be better.
    conv_dict = await conversation_dao.get_conversation(db, conversation_id)
    if not conv_dict:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = await message_dao.get_messages_by_conversation(
        db=db, conversation_id=conversation_id
    )
    
    # Manually construct the final response model
    response_data = {
        "id": conv_dict['id'],
        "user_id": conv_dict['user_id'],
        "name": conv_dict.get('name'),
        "created_at": conv_dict['created_at'],
        "messages": messages
    }
    return ConversationWithMessagesSchema(**response_data)
