import os
from typing import Optional
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.configs.db import get_db_session
from src.services import user_service
from src.dao import user_dao
from src.schemas.user import UserSchema
from src.utils.auth_utils import oauth2_scheme

async def validate_token_and_get_user(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    token: str = Depends(oauth2_scheme)
) -> UserSchema:
    """
    A dependency that validates the authentication method (IAP or Auth0)
    and returns the corresponding user from the database.
    
    This will be applied to all protected routers.
    """
    provider = os.getenv("AUTH_PROVIDER", "iap")
    
    user_info = None

    if provider == "auth0":
        # The token is now a string from OAuth2 scheme, not credentials object
        if not token: # This check is somewhat redundant as Depends(oauth2_scheme) would fail first
            raise HTTPException(status_code=401, detail="Authentication token required.")
        user_info = await user_service.process_auth0_login(db, token)
    
    elif provider == "iap":
        email = request.headers.get("X-Goog-Authenticated-User-Email")
        idp_user_id = request.headers.get("X-Goog-Authenticated-User-Id")
        if email and ":" in email:
            email = email.split(":")[-1]
        
        username = None
        if email:
            username = email.split('@')[0]
        
        user_info = await user_service.get_or_create_user(db, email, idp_user_id, username)

    if not user_info or not user_info.get("user_id"):
        raise HTTPException(status_code=403, detail="Could not validate user identity or user not found.")

    # Why do we fetch the user again from the DB instead of returning user_info directly?
    # 1. Data Consistency: The user_info from the service might be a subset of the full user model.
    #    Fetching from the DB ensures we have the complete and most up-to-date user record.
    # 2. Type Safety: This ensures the returned object is a dict derived from the DB table,
    #    which reliably matches the UserSchema Pydantic model.
    final_user = await user_dao.get_user_by_id(db, user_info["user_id"])
    if not final_user:
        raise HTTPException(status_code=404, detail="User not found in database after authentication.")
        
    return UserSchema(**final_user)
