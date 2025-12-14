from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from src.dao import user_dao
from src.schemas.user import UserCreateSchema
from src.services.auth_service import auth_service
from loguru import logger

async def get_or_create_user(db: AsyncSession, email: str, idp_user_id: str, username: str) -> dict:
    """
    Check if a user exists by username. If not, create a new user.
    Returns a dictionary compatible with IAPUser schema.
    """
    if not username:
        raise HTTPException(status_code=400, detail="Username is required to get or create a user.")

    # Check if user exists by username
    db_user = await user_dao.get_user_by_username(db, username=username)
    
    if not db_user:
        logger.info(f"User '{username}' not found. Creating new user.")
        new_user_schema = UserCreateSchema(username=username, email=email)
        try:
            created_user = await user_dao.create_user(db, new_user_schema)
            user_id = created_user["id"]
        except Exception as e:
            logger.error(f"Failed to create user '{username}': {e}")
            raise HTTPException(status_code=500, detail="Could not create user account.")
    else:
        logger.info(f"Found existing user '{username}' with id {db_user['id']}.")
        user_id = db_user["id"]

    return {"email": email, "idp_user_id": idp_user_id, "user_id": user_id, "username": username}

async def process_auth0_login(db: AsyncSession, token: str) -> dict:
    """
    Handles the logic for an Auth0 login.
    1. Verifies the token.
    2. Fetches user info from Auth0's /userinfo endpoint.
    3. Creates or retrieves the corresponding user in the local database.
    """
    # Step 1: Verify token & get user info
    auth_service.verify_token(token)
    user_info = await auth_service.get_user_info(token)
    logger.debug(f"Auth0 UserInfo received in service: {user_info}")

    email = user_info.get("email")
    idp_user_id = user_info.get("sub")
    username = user_info.get("nickname") # Get username from 'nickname' claim

    if not email:
        logger.warning(f"Email not found in UserInfo payload. Cannot create user. Sub: {idp_user_id}")
        return {"email": None, "idp_user_id": idp_user_id, "user_id": None, "username": username}

    if not username:
        logger.warning(f"Username ('nickname') not found in UserInfo payload. Using email prefix as fallback. Sub: {idp_user_id}")
        username = email.split('@')[0]

    # Step 2: Get or create user in local DB
    return await get_or_create_user(db, email, idp_user_id, username)
