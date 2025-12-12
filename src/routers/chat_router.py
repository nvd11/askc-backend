from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import StreamingResponse
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.llm.deepseek_chat_model import get_deepseek_llm
from src.llm.gemini_chat_model import get_gemini_llm
from src.services.llm_service import LLMService
from src.configs.db import get_db_session
from src.schemas.chat import ChatRequest, PureChatRequest
from src.services import chat_service

# Create an API router
router = APIRouter(
    prefix="/api/v1",
    tags=["Chat"],
)

# --- API Endpoint ---
@router.post("/chat")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Receives a user message, saves it, retrieves conversation history,
    and returns the model's response as a stream of Server-Sent Events (SSE).
    The assistant's final response is also saved to the database.
    """
    logger.info(f"Received chat request for conv {request.conversation_id} with model: {request.model}")

    try:
        if request.model == "gemini":
            llm = get_gemini_llm()
        elif request.model == "deepseek":
            llm = get_deepseek_llm()
        else:
            raise HTTPException(status_code=400, detail=f"Invalid model '{request.model}'. Please use 'gemini' or 'deepseek'.")
        
        llm_service = LLMService(llm=llm)

    except Exception as e:
        logger.error(f"Failed to initialize LLM service for request: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize LLM service.")

    return StreamingResponse(
        chat_service.stream_chat_response(request, llm_service, db),
        media_type="text/event-stream"
    )

@router.post("/purechat")
async def pure_chat(
    request: PureChatRequest,
):
    """
    Receives a user message and directly returns the model's response as a 
    stream of Server-Sent Events (SSE) without any database interaction.
    """
    logger.info(f"Received pure chat request with model: {request.model}")
    
    try:
        if request.model == "gemini":
            llm = get_gemini_llm()
        elif request.model == "deepseek":
            llm = get_deepseek_llm()
        else:
            raise HTTPException(status_code=400, detail=f"Invalid model '{request.model}'. Please use 'gemini' or 'deepseek'.")

        llm_service = LLMService(llm=llm)

    except Exception as e:
        logger.error(f"Failed to initialize LLM service for request: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize LLM service.")

    return StreamingResponse(
        chat_service.stream_pure_chat_response(request, llm_service),
        media_type="text/event-stream"
    )
