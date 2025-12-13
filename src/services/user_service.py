from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from src.dao import user_dao
from src.schemas.user import UserCreateSchema

async def get_or_create_iap_user(db: AsyncSession, email: str, idp_user_id: str) -> dict:
    """
    Check if a user exists by email. If not, create a new user using the email prefix as username.
    Returns a dictionary compatible with IAPUser schema.
    """
    user_id = None
    username = None
    if email:
        # Check if user exists
        db_user = await user_dao.get_user_by_email(db, email=email)
        if not db_user:
            # Create user if not exists
            # Use part before @ as username
            username = email.split("@")[0]
            
            new_user = UserCreateSchema(username=username, email=email)
            try:
                # We might need to handle username collision if username is unique
                created_user = await user_dao.create_user(db, new_user)
                user_id = created_user["id"]
            except Exception as e:
                # Fallback logic: check if username exists
                existing_user_by_name = await user_dao.get_user_by_username(db, username)
                if existing_user_by_name:
                     # Since we already checked email and it didn't exist, this is a username collision.
                     # Requirements didn't specify handling, but we must fail or handle gracefully.
                     # Raising 500 as per previous logic implementation.
                    raise HTTPException(status_code=500, detail="Could not create user account due to username conflict")
                raise e
        else:
            user_id = db_user["id"]
            username = db_user["username"]

    return {"email": email, "idp_user_id": idp_user_id, "user_id": user_id, "username": username}
