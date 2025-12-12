from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.configs.db import get_db_session
from src.schemas.user import UserSchema, UserCreateSchema, IAPUser
from src.dao import user_dao

router = APIRouter(
    prefix="/api/v1",
    tags=["Users & Conversations"],
)

@router.post("/users/", response_model=UserSchema)
async def create_user_endpoint(
    user: UserCreateSchema, db: AsyncSession = Depends(get_db_session)
):
    """
    Create a new user.
    """
    db_user = await user_dao.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    created_user = await user_dao.create_user(db=db, user=user)
    return created_user

@router.get("/users/{username}", response_model=UserSchema)
async def get_user_endpoint(username: str, db: AsyncSession = Depends(get_db_session)):
    """
    Get a single user by username.
    """
    db_user = await user_dao.get_user_by_username(db, username=username)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.get("/me", response_model=IAPUser)
async def get_current_user_from_iap(request: Request):
    """
    Get the current authenticated user's info from IAP headers.
    This endpoint is designed to be used when the application is deployed behind Google Cloud IAP.
    """
    email = request.headers.get("X-Goog-Authenticated-User-Email")
    user_id = request.headers.get("X-Goog-Authenticated-User-Id")
    
    # IAP email header often comes in the format: "accounts.google.com:user@example.com"
    if email and ":" in email:
        email = email.split(":")[-1]

    return {"email": email, "user_id": user_id}
