from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.configs.db import get_db_session
from src.schemas.conversation import ConversationSchema, ConversationCreateSchema, ConversationWithMessagesSchema
from src.schemas.message import MessageSchema
from src.dao import conversation_dao, message_dao

from src.routers.dependencies import validate_token_and_get_user

from src.schemas.user import UserSchema

router = APIRouter(
    prefix="/api/v1",
    tags=["Conversations"],
)

@router.post("/conversations/", response_model=ConversationSchema)
async def create_conversation_endpoint(
    conv: ConversationCreateSchema, 
    db: AsyncSession = Depends(get_db_session),
    current_user: UserSchema = Depends(validate_token_and_get_user)
):
    """
    Create a new conversation for a user.
    """
    # Security Fix: Ensure the user can only create a conversation for themselves.
    if conv.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to create a conversation for another user.")

    created_conv = await conversation_dao.create_conversation(db=db, conv=conv)
    return created_conv

@router.get("/users/{user_id}/conversations", response_model=List[ConversationSchema])
async def get_user_conversations_endpoint(
    user_id: int, 
    skip: int = 0, 
    limit: int = 10, 
    db: AsyncSession = Depends(get_db_session),
    current_user: UserSchema = Depends(validate_token_and_get_user)
):
    """
    Get all conversations for a specific user.
    """
    # Security Fix: Ensure the authenticated user can only access their own conversations.
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this resource.")

    conversations = await conversation_dao.get_conversations_by_user(
        db=db, user_id=user_id, skip=skip, limit=limit
    )
    return conversations

@router.get("/conversations/{conversation_id}", response_model=ConversationWithMessagesSchema)
async def get_conversation_with_messages_endpoint(
    conversation_id: int, 
    db: AsyncSession = Depends(get_db_session),
    current_user: UserSchema = Depends(validate_token_and_get_user)
):
    """
    Get a single conversation with all its messages.
    """
    # This is not the most efficient way, but it's simple.
    # A single query with a JOIN would be better.
    conv_dict = await conversation_dao.get_conversation(db, conversation_id)
    if not conv_dict:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Security Fix: Ensure the authenticated user can only access their own conversation.
    if conv_dict['user_id'] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this resource.")

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
