import os
import typing
from typing import Any, List, Optional, Sequence, Callable
from loguru import logger

from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_core.callbacks.manager import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult, ChatGenerationChunk
from langchain_google_genai import ChatGoogleGenerativeAI, HarmBlockThreshold, HarmCategory
from src.configs.config import yaml_configs
from typing import AsyncIterator

class GeminiChatModel(BaseChatModel):
    """
    A custom Gemini LLM class that integrates with LangChain's BaseChatModel.
    It reads configuration from the project's YAML files.
    """
    client: Any = None
    model: str = "gemini-2.5-pro"
    temperature: float = 0.7

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        
        # Get API key env var name from config
        api_key_env_var = yaml_configs.get("gemini", {}).get("api-key", "GEMINI_API_KEY")
        resolved_api_key = os.getenv(api_key_env_var)
        
        if not resolved_api_key:
            logger.error(f"CRITICAL: Environment variable '{api_key_env_var}' for Gemini not found!")
            raise ValueError(f"{api_key_env_var} not found in environment variables.")

        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        # Let BaseChatModel handle the kwargs. The actual model and temperature
        # are accessed via self.model and self.temperature.
        self.client = ChatGoogleGenerativeAI(
            model=self.model,
            google_api_key=resolved_api_key,
            temperature=self.temperature,
            transport="rest",
            safety_settings=safety_settings
        )
        logger.info(f"GeminiChatModel initialized with model: {self.model}")

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        llm_result = self.client.generate([messages], stop=stop, callbacks=run_manager, **kwargs)
        return ChatResult(generations=llm_result.generations[0])

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        llm_result = await self.client.agenerate([messages], stop=stop, callbacks=run_manager, **kwargs)
        return ChatResult(generations=llm_result.generations[0])

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        async for chunk in self.client.astream(messages, stop=stop, callbacks=run_manager, **kwargs):
            yield ChatGenerationChunk(message=chunk)

    def bind_tools(
        self,
        tools: Sequence[typing.Dict[str, Any] | type | Callable | BaseTool],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> Runnable:
        return self.client.bind_tools(tools, tool_choice=tool_choice, **kwargs)

    @property
    def _llm_type(self) -> str:
        return "gemini_chat_model"

def get_gemini_llm():
    """
    Initializes and returns a GeminiChatModel instance.
    """
    model = yaml_configs.get("gemini", {}).get("model-name", "gemini-2.5-pro")
    temperature = yaml_configs.get("gemini", {}).get("temperature", 0.7)
    
    return GeminiChatModel(
        model=model,
        temperature=temperature
    )
