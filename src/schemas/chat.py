from pydantic import BaseModel, Field
from typing import Optional

class ChatRequest(BaseModel):
    conversation_id: int
    message: str
    model: Optional[str] = Field("gemini", description="The model to use, e.g., 'gemini' or 'deepseek'")

class PureChatRequest(BaseModel):
    message: str
    model: Optional[str] = Field("gemini", description="The model to use, e.g., 'gemini' or 'deepseek'")
