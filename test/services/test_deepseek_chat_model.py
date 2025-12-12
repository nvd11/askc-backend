import src.configs.config
import time
import src.configs.config
from src.llm.deepseek_chat_model import get_deepseek_llm
from loguru import logger

def test_deepseek_chat_model_invoke():
    """
    Tests the invocation of the DeepSeek chat model and measures response time.
    """
    # 1. Get the chat model
    model = get_deepseek_llm()

    # 2. Invoke the model with a simple prompt and measure time
    prompt = "Hello, who are you?"
    logger.info(f"--- Invoke Test: Prompt: '{prompt}' ---")
    start_time = time.time()
    result = model.invoke(prompt)
    end_time = time.time()
    
    response_time = end_time - start_time
    logger.info(f"Invoke mode - Total response time: {response_time:.4f} seconds")

    # 4. Log the response and assert that it's valid
    logger.info(f"Invoke response: {result.content}")
    assert result.content is not None
    assert len(result.content) > 0


def test_deepseek_chat_model_stream():
    """
    Tests the streaming invocation of the DeepSeek chat model and measures time to first chunk.
    """
    # 1. Get the chat model
    model = get_deepseek_llm()

    # 2. Stream the model's response to a simple prompt
    prompt = "Tell me a short story about a dragon."
    logger.info(f"--- Stream Test: Prompt: '{prompt}' ---")
    start_time = time.time()
    stream = model.stream(prompt)

    # 4. Log each chunk, measure time to first chunk, and collect the full response
    full_response = ""
    first_chunk_received = False
    time_to_first_chunk = 0
    
    logger.info("--- Streaming Response ---")
    for chunk in stream:
        if not first_chunk_received:
            time_to_first_chunk = time.time() - start_time
            logger.info(f"Stream mode - Time to first chunk: {time_to_first_chunk:.4f} seconds")
            first_chunk_received = True
        
        # logger.info(chunk.content) # This can be noisy, so we comment it out
        full_response += chunk.content
    
    total_stream_time = time.time() - start_time
    logger.info("--- End of Stream ---")
    logger.info(f"Stream mode - Total response time: {total_stream_time:.4f} seconds")

    # 5. Assert that the full response is valid
    assert full_response is not None
    assert len(full_response) > 0
    logger.info(f"Full streamed response length: {len(full_response)}")
