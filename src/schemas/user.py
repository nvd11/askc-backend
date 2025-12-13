from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    username: str
    email: Optional[str] = None

class UserCreateSchema(UserBase):
    pass

class UserSchema(UserBase):
    id: int
    created_at: datetime

class IAPUser(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None
    idp_user_id: Optional[str] = None
    username: Optional[str] = None
