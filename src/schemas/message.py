from pydantic import BaseModel
from datetime import datetime

class MessageBase(BaseModel):
    role: str
    content: str

class MessageCreateSchema(MessageBase):
    conversation_id: int

class MessageSchema(MessageBase):
    id: int
    conversation_id: int
    created_at: datetime
