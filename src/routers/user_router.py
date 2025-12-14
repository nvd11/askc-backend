from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.configs.db import get_db_session
from src.schemas.user import UserSchema, UserCreateSchema, IAPUser
from src.dao import user_dao
from loguru import logger
from src.services import user_service
from src.services.auth_service import auth_service
from src.routers.dependencies import validate_token_and_get_user

router = APIRouter(
    prefix="/api/v1",
    tags=["Users & Conversations"],
)

security = HTTPBearer(auto_error=False)

@router.post("/users/", response_model=UserSchema)
async def create_user_endpoint(
    user: UserCreateSchema, 
    db: AsyncSession = Depends(get_db_session),
    current_user: UserSchema = Depends(validate_token_and_get_user)
):
    """
    Create a new user.

    Note: This endpoint is not used in the standard Auth0 login flow,
    as users are created automatically upon their first login via the /auth0/me endpoint.
    This can be used for administrative or testing purposes.
    """
    db_user = await user_dao.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    created_user = await user_dao.create_user(db=db, user=user)
    return created_user

@router.get("/users/{username}", response_model=UserSchema)
async def get_user_endpoint(
    username: str, 
    db: AsyncSession = Depends(get_db_session),
    current_user: UserSchema = Depends(validate_token_and_get_user)
):
    """
    Get a single user by username.

    Note: This endpoint is not currently used by the frontend, but is kept for potential future use.
    """
    # Security Fix: Ensure the authenticated user can only access their own details.
    if current_user.username != username:
        raise HTTPException(status_code=403, detail="Not authorized to access this resource.")
        
    db_user = await user_dao.get_user_by_username(db, username=username)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.get("/me", response_model=IAPUser)
async def get_current_user_from_iap(request: Request, db: AsyncSession = Depends(get_db_session)):
    """
    [Google IAP ONLY] Get the current authenticated user's info from IAP headers.
    This endpoint is designed to be used when the application is deployed behind Google Cloud IAP.
    """
    email = request.headers.get("X-Goog-Authenticated-User-Email")
    idp_user_id = request.headers.get("X-Goog-Authenticated-User-Id")
    
    # IAP email header often comes in the format: "accounts.google.com:user@example.com"
    if email and ":" in email:
        email = email.split(":")[-1]
    
    username = None
    if email:
        username = email.split('@')[0]

    return await user_service.get_or_create_user(db, email, idp_user_id, username)

@router.get("/auth0/me", response_model=IAPUser)
async def get_current_user_from_auth0(
    token: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
):
    """
    [Auth0 ONLY] Get the current authenticated user's info from Bearer Token.
    
    Why do we need this endpoint if Auth0 SDK already provides user info on frontend?
    1. Synchronization: We need to ensure the user exists in our local database (`users` table).
    2. Mapping: We need to retrieve the internal database `id` (e.g. integer) which is required 
       for other business logic (like creating conversations), mapping it from Auth0's `sub` string.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Missing Bearer Token")

    try:
        return await user_service.process_auth0_login(db, token.credentials)
    except HTTPException as e:
        # Re-raise HTTPException to preserve status code and detail
        raise e
    except Exception as e:
        logger.error(f"Unhandled error in /auth0/me endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error processing authentication.")
