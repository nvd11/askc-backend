import asyncio
import json
import time
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from langchain_core.messages import AIMessage, HumanMessage

from src.services.llm_service import LLMService
from src.schemas.chat import ChatRequest, PureChatRequest
from src.dao import message_dao
from src.schemas.message import MessageCreateSchema
from src.configs.db import AsyncSessionFactory

from sqlalchemy.exc import InterfaceError, OperationalError

async def save_partial_response_task(conversation_id: int, content: str):
    """
    Background task to save partial response when stream is cancelled.
    Creates a fresh DB session. Includes a retry mechanism to handle potential
    connection race conditions (e.g., picking up a closing connection).
    """
    for attempt in range(3):
        try:
            async with AsyncSessionFactory() as session:
                assistant_message_to_save = MessageCreateSchema(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=content,
                )
                await message_dao.create_message(session, message=assistant_message_to_save)
                logger.info(f"Saved partial assistant response in background task: conv={conversation_id} len={len(content)}")
                return  # Success, exit loop
        except (InterfaceError, OperationalError, OSError) as e:
            if attempt < 2:
                logger.warning(f"Failed to save partial response (attempt {attempt + 1}), retrying in 0.1s: {e}")
                await asyncio.sleep(0.1)  # Small delay before retry
            else:
                logger.error(f"Failed to save partial response after {attempt + 1} attempts: {e}")
        except Exception as e:
            logger.error(f"Failed to save partial response due to unexpected error: {e}")
            break  # Don't retry on unknown errors

async def stream_chat_response(
    request: ChatRequest, llm_service: LLMService, db: AsyncSession
):
    """
    Handles the logic of saving messages, retrieving history,
    streaming the LLM response, and saving the final response.
    """
    if not llm_service:
        error_message = "LLM Service is not available."
        logger.error(error_message)
        # Fallback to simple text if service not available, or construct a JSON error
        # Since we want to standardize, let's use JSON even here
        error_data = {
            "id": f"chatcmpl-error",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{"index": 0, "delta": {"content": error_message}, "finish_reason": "stop"}]
        }
        yield f"data: {json.dumps(error_data)}\n\n"
        yield "data: [DONE]\n\n"
        return

    # 1. Save user message
    user_message_to_save = MessageCreateSchema(
        conversation_id=request.conversation_id, role="user", content=request.message
    )
    await message_dao.create_message(db, message=user_message_to_save)

    # 2. Define history limit and load conversation history from DB
    MAX_HISTORY_LENGTH = 20
    history_from_db = await message_dao.get_messages_by_conversation(
        db, conversation_id=request.conversation_id, limit=MAX_HISTORY_LENGTH
    )
    
    # Reverse the list to restore chronological order (oldest first)
    history_from_db.reverse()

    # Format history for the LLM
    chat_history = []
    for msg in history_from_db:
        if msg['role'] == 'user':
            chat_history.append(HumanMessage(content=msg['content']))
        elif msg['role'] == 'assistant':
            chat_history.append(AIMessage(content=msg['content']))

    logger.info(f"Initiating true stream for conversation {request.conversation_id} with {len(chat_history)} messages in history.")
    
    full_response_content = ""
    response_saved = False
    try:
        # 3. Call the astream method on the service with history
        llm_stream = llm_service.llm.astream(chat_history)
        
        # 4. Iterate over the stream with timeout protection (300 seconds = 5 minutes per chunk)
        stream_iter = llm_stream.__aiter__()
        timeout_seconds = 300.0
        
        while True:
            try:
                # Get next chunk with timeout (prevents hanging on a single chunk)
                chunk_task = asyncio.create_task(stream_iter.__anext__())
                chunk = await asyncio.wait_for(chunk_task, timeout=timeout_seconds)
                
                logger.debug(f"Received chunk of type {type(chunk)}: {chunk}")
                if hasattr(chunk, 'content') and chunk.content:
                    full_response_content += chunk.content
                    
                    # Construct OpenAI-compatible SSE chunk
                    chunk_data = {
                        "id": f"chatcmpl-{request.conversation_id}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": request.model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {
                                    "content": chunk.content
                                },
                                "finish_reason": None
                            }
                        ]
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n"
            except StopAsyncIteration:
                # Stream ended normally
                break
            except asyncio.TimeoutError:
                logger.warning(f"LLM stream timeout for conversation {request.conversation_id}, partial response length={len(full_response_content)}")
                if full_response_content:
                    # Save partial response on timeout
                    # Use background task here too for safety, although loop is still running
                    asyncio.create_task(save_partial_response_task(request.conversation_id, full_response_content))
                    response_saved = True
                    logger.info(f"Triggered background save for partial response due to timeout: conv={request.conversation_id} len={len(full_response_content)}")
                
                # Send timeout message as content
                timeout_data = {
                    "id": f"chatcmpl-{request.conversation_id}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": request.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "content": "\n\n[Stream timeout after 5 minutes]"
                            },
                            "finish_reason": "stop"
                        }
                    ]
                }
                yield f"data: {json.dumps(timeout_data)}\n\n"
                yield "data: [DONE]\n\n"
                return
        
        logger.info("Streaming finished.")
        yield "data: [DONE]\n\n"
        
        # 5. Save assistant's full response
        if full_response_content:
            logger.info(f"Saving assistant response conv={request.conversation_id} len={len(full_response_content)} preview={full_response_content[:100]}")
            assistant_message_to_save = MessageCreateSchema(
                conversation_id=request.conversation_id,
                role="assistant",
                content=full_response_content,
            )
            await message_dao.create_message(db, message=assistant_message_to_save)
            response_saved = True

    except asyncio.CancelledError:
        # Client disconnected, save partial response if available
        logger.warning(f"Stream cancelled (client disconnected) for conversation {request.conversation_id}, partial response length={len(full_response_content)}")
        if full_response_content and not response_saved:
            # Use a background task with a fresh session to save, as the current session/task is cancelled
            asyncio.create_task(save_partial_response_task(request.conversation_id, full_response_content))
        raise  # Re-raise to properly clean up

    except Exception as e:
        error_message = f"An error occurred during streaming: {e}"
        logger.exception(error_message)
        # Try to save partial response on other errors
        if full_response_content and not response_saved:
            # Also use background task for consistency, though current session might be valid depending on error
            asyncio.create_task(save_partial_response_task(request.conversation_id, full_response_content))
        
        # Send error as content
        error_data = {
            "id": f"chatcmpl-{request.conversation_id}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "content": f"\n\n{error_message}"
                    },
                    "finish_reason": "stop"
                }
            ]
        }
        yield f"data: {json.dumps(error_data)}\n\n"
        yield "data: [DONE]\n\n"


async def stream_pure_chat_response(
    request: PureChatRequest, llm_service: LLMService
):
    """
    Handles the logic of streaming the LLM response directly, without any database interaction.
    """
    if not llm_service:
        error_message = "LLM Service is not available."
        logger.error(error_message)
        error_data = {
            "id": "chatcmpl-pure-error",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{"index": 0, "delta": {"content": error_message}, "finish_reason": "stop"}]
        }
        yield f"data: {json.dumps(error_data)}\n\n"
        yield "data: [DONE]\n\n"
        return

    logger.info(f"Initiating pure stream with message: '{request.message}'")
    
    try:
        # Call the astream method on the service with just the user's message
        llm_stream = llm_service.astream(request.message)
        
        # Iterate over the stream and yield each chunk formatted as an SSE event
        async for chunk in llm_stream:
            if hasattr(chunk, 'content') and chunk.content:
                chunk_data = {
                    "id": "chatcmpl-pure",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": request.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "content": chunk.content
                            },
                            "finish_reason": None
                        }
                    ]
                }
                yield f"data: {json.dumps(chunk_data)}\n\n"
        
        logger.info("Pure streaming finished.")
        yield "data: [DONE]\n\n"

    except Exception as e:
        error_message = f"An error occurred during pure streaming: {e}"
        logger.exception(error_message)
        
        error_data = {
            "id": "chatcmpl-pure",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "content": f"\n\n{error_message}"
                    },
                    "finish_reason": "stop"
                }
            ]
        }
        yield f"data: {json.dumps(error_data)}\n\n"
        yield "data: [DONE]\n\n"
