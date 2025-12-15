from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from src.dao import user_dao
from src.schemas.user import UserCreateSchema
from src.services.auth_service import auth_service
from loguru import logger

async def get_or_create_user(db: AsyncSession, email: str, idp_user_id: str, username: str) -> dict:
    """Checks if a user exists by username, creating one if not found.

    This function serves as the central point for synchronizing users from an
    identity provider (like Google IAP or Auth0) with the local database.

    Args:
        db (AsyncSession): The database session.
        email (str): The user's email address.
        idp_user_id (str): The user's unique ID from the identity provider (e.g., Auth0 `sub`).
        username (str): The user's username.

    Returns:
        dict: A dictionary containing the synchronized user's information,
              matching the IAPUser schema.
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
        except IntegrityError as e:
            logger.error(f"Failed to create user '{username}' due to integrity error (e.g., username already exists): {e}")
            # Rollback the session in case of integrity error
            await db.rollback()
            raise HTTPException(status_code=409, detail=f"A user with username '{username}' may already exist.")
        except Exception as e:
            logger.error(f"Failed to create user '{username}' due to an unexpected error: {e}")
            await db.rollback()
            raise HTTPException(status_code=500, detail="Could not create user account.")
    else:
        logger.info(f"Found existing user '{username}' with id {db_user['id']}.")
        user_id = db_user["id"]

    return {"email": email, "idp_user_id": idp_user_id, "user_id": user_id, "username": username}



async def process_auth0_login(db: AsyncSession, token: str) -> dict:
    """Handles the full logic for an Auth0 login.

    This involves validating the token, fetching user info from the /userinfo 
    endpoint to ensure an email is present, and then creating or retrieving 
    the user in the local database.

    Args:
        db (AsyncSession): The database session.
        token (str): The raw Access Token from the 'Authorization: Bearer' header.

    Returns:
        dict: A dictionary containing the synchronized user's information,
              matching the IAPUser schema.
    """
    # Step 1: Verify token & get user info
    auth_service.verify_token(token)
    user_info = await auth_service.get_user_info(token)
    logger.debug(f"Auth0 UserInfo received in service: {user_info}")

    email = user_info.get("email")
    idp_user_id = user_info.get("sub")
    username = user_info.get("nickname") # Get username from 'nickname' claim

    if not email:
        logger.warning(f"Email not found in UserInfo payload. Cannot create or link user. Sub: {idp_user_id}")
        return {"email": None, "idp_user_id": idp_user_id, "user_id": None, "username": username}

    if not username:
        logger.warning(f"Username ('nickname') not found in UserInfo payload. Using email prefix as fallback. Sub: {idp_user_id}")
        username = email.split('@')[0]

    # Step 2: Get or create user in local DB
    return await get_or_create_user(db, email, idp_user_id, username)
