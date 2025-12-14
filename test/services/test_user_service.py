import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.services import user_service
from src.schemas.user import UserCreateSchema

@pytest.mark.asyncio
async def test_get_or_create_user_existing_user():
    """
    Test: User exists by username, returns existing user ID.
    """
    mock_db = AsyncMock(spec=AsyncSession)
    username = "existing_user"
    email = "existing@example.com"
    idp_user_id = "some-idp-id"
    existing_user = {"id": 10, "username": username, "email": email}

    with patch("src.services.user_service.user_dao.get_user_by_username", new_callable=AsyncMock) as mock_get_by_username, \
         patch("src.services.user_service.user_dao.create_user", new_callable=AsyncMock) as mock_create_user:
        
        mock_get_by_username.return_value = existing_user

        result = await user_service.get_or_create_user(mock_db, email, idp_user_id, username)

        assert result["user_id"] == 10
        assert result["username"] == username
        mock_get_by_username.assert_called_once_with(mock_db, username=username)
        mock_create_user.assert_not_called()

@pytest.mark.asyncio
async def test_get_or_create_user_new_user():
    """
    Test: User does not exist, creates a new user successfully.
    """
    mock_db = AsyncMock(spec=AsyncSession)
    username = "new_user"
    email = "new@example.com"
    idp_user_id = "some-idp-id-2"
    created_user_db = {"id": 20, "username": username, "email": email}

    with patch("src.services.user_service.user_dao.get_user_by_username", new_callable=AsyncMock) as mock_get_by_username, \
         patch("src.services.user_service.user_dao.create_user", new_callable=AsyncMock) as mock_create_user:
        
        mock_get_by_username.return_value = None
        mock_create_user.return_value = created_user_db

        result = await user_service.get_or_create_user(mock_db, email, idp_user_id, username)

        assert result["user_id"] == 20
        assert result["username"] == username
        mock_get_by_username.assert_called_once_with(mock_db, username=username)
        mock_create_user.assert_called_once()
        call_args = mock_create_user.call_args[0][1]
        assert call_args.username == username
        assert call_args.email == email

@pytest.mark.asyncio
async def test_process_auth0_login_success_with_nickname():
    """
    Test: process_auth0_login with a token containing email and nickname.
    """
    mock_db = AsyncMock(spec=AsyncSession)
    token = "dummy_token"
    user_info = {"email": "test@example.com", "sub": "auth0|123", "nickname": "testuser"}
    
    with patch("src.services.user_service.auth_service.verify_token") as mock_verify, \
         patch("src.services.user_service.auth_service.get_user_info", new_callable=AsyncMock) as mock_get_info, \
         patch("src.services.user_service.get_or_create_user", new_callable=AsyncMock) as mock_get_or_create:

        mock_verify.return_value = True # Just needs to not fail
        mock_get_info.return_value = user_info
        mock_get_or_create.return_value = {"user_id": 1, "username": "testuser", "email": "test@example.com", "idp_user_id": "auth0|123"}

        result = await user_service.process_auth0_login(mock_db, token)

        mock_verify.assert_called_once_with(token)
        mock_get_info.assert_called_once_with(token)
        mock_get_or_create.assert_called_once_with(mock_db, "test@example.com", "auth0|123", "testuser")
        assert result["user_id"] == 1

@pytest.mark.asyncio
async def test_process_auth0_login_fallback_to_email_prefix():
    """
    Test: process_auth0_login when token has email but no nickname.
    """
    mock_db = AsyncMock(spec=AsyncSession)
    token = "dummy_token_no_nick"
    user_info = {"email": "fallback@example.com", "sub": "auth0|456"} # No nickname

    with patch("src.services.user_service.auth_service.verify_token") as mock_verify, \
         patch("src.services.user_service.auth_service.get_user_info", new_callable=AsyncMock) as mock_get_info, \
         patch("src.services.user_service.get_or_create_user", new_callable=AsyncMock) as mock_get_or_create:

        mock_verify.return_value = True
        mock_get_info.return_value = user_info
        mock_get_or_create.return_value = {"user_id": 2, "username": "fallback", "email": "fallback@example.com", "idp_user_id": "auth0|456"}
        
        await user_service.process_auth0_login(mock_db, token)

        # Verify that get_or_create_user was called with the email prefix as username
        mock_get_or_create.assert_called_once_with(mock_db, "fallback@example.com", "auth0|456", "fallback")

@pytest.mark.asyncio
async def test_process_auth0_login_no_email():
    """
    Test: process_auth0_login when token has no email.
    """
    mock_db = AsyncMock(spec=AsyncSession)
    token = "dummy_token_no_email"
    user_info = {"sub": "auth0|789", "nickname": "no_email_user"} # No email

    with patch("src.services.user_service.auth_service.verify_token") as mock_verify, \
         patch("src.services.user_service.auth_service.get_user_info", new_callable=AsyncMock) as mock_get_info, \
         patch("src.services.user_service.get_or_create_user", new_callable=AsyncMock) as mock_get_or_create:
        
        mock_verify.return_value = True
        mock_get_info.return_value = user_info

        result = await user_service.process_auth0_login(mock_db, token)

        # Should not attempt to create a user
        mock_get_or_create.assert_not_called()
        # Should return null user_id
        assert result["user_id"] is None
        assert result["username"] == "no_email_user"
