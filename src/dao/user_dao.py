from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from typing import Optional

from src.models.tables import users_table
from src.schemas.user import UserCreateSchema

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[dict]:
    """
    Fetches a user by their username.
    """
    query = select(users_table).where(users_table.c.username == username)
    result = await db.execute(query)
    user = result.first()
    return user._asdict() if user else None

async def create_user(db: AsyncSession, user: UserCreateSchema) -> dict:
    """
    Creates a new user in the database.
    """
    query = insert(users_table).values(
        username=user.username,
        email=user.email
    ).returning(users_table)
    
    result = await db.execute(query)
    created_user = result.first()
    await db.commit()
    return created_user._asdict()
