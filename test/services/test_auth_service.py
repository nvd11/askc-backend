import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
from src.services.auth_service import AuthService
import jwt
import httpx

# Since AuthService is a singleton, we get the instance
auth_service = AuthService()

@pytest.fixture
def mock_env(monkeypatch):
    """
    A Pytest fixture to prepare the environment for auth service tests.
    
    Fixtures are reusable functions that run before each test function that requests them.
    
    This fixture does the following:
    1. Uses the 'monkeypatch' fixture (built-in to pytest) to temporarily set
       environment variables required by the AuthService.
    2. Forces the AuthService singleton to re-initialize with these mocked variables.
    3. Clears the userinfo cache before each test to ensure test isolation.
    """
    monkeypatch.setenv("AUTH0_DOMAIN", "fake-domain.auth0.com")
    monkeypatch.setenv("AUTH0_AUDIENCE", "https://fake-api.com")
    # Force re-initialization of the singleton with mocked env
    auth_service._initialize()
    # Clear cache for each test
    if hasattr(auth_service, 'userinfo_cache'):
        auth_service.userinfo_cache.clear()

def test_verify_token_success(mock_env):
    """
    Test successful token verification.
    """
    token = "valid_token"
    payload = {"sub": "user123"}
    
    with patch("jwt.decode", return_value=payload) as mock_decode, \
         patch.object(auth_service.jwks_client, 'get_signing_key_from_jwt', return_value=MagicMock(key="secret")) as mock_get_key:
        
        result = auth_service.verify_token(token)
        
        mock_get_key.assert_called_once_with(token)
        mock_decode.assert_called_once()
        assert result == payload

def test_verify_token_invalid_signature(mock_env):
    """
    Test token verification failure due to invalid signature.
    """
    token = "invalid_token"
    
    with patch.object(auth_service.jwks_client, 'get_signing_key_from_jwt', side_effect=jwt.PyJWTError("Invalid signature")) as mock_get_key:
        
        with pytest.raises(HTTPException) as exc_info:
            auth_service.verify_token(token)
        
        assert exc_info.value.status_code == 401
        assert "Invalid signature" in exc_info.value.detail

@pytest.mark.asyncio
@patch("httpx.AsyncClient")
async def test_get_user_info_success(MockAsyncClient, mock_env):
    """
    Test successful fetching of user info from /userinfo endpoint.
    """
    token = "valid_token_for_userinfo"
    user_info = {"email": "test@test.com", "sub": "user123"}
    
    # Configure the mock response object
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = user_info
    
    # Configure the mock client instance
    mock_client_instance = MockAsyncClient.return_value.__aenter__.return_value
    mock_client_instance.get.return_value = mock_response

    result = await auth_service.get_user_info(token)
    
    mock_client_instance.get.assert_called_once()
    assert result == user_info

@pytest.mark.asyncio
@patch("httpx.AsyncClient")
async def test_get_user_info_cached(MockAsyncClient, mock_env):
    """
    Test that user info is cached after the first call.
    """
    token = "cached_token"
    user_info = {"email": "cached@test.com", "sub": "user456"}

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = user_info
    
    mock_client_instance = MockAsyncClient.return_value.__aenter__.return_value
    mock_client_instance.get.return_value = mock_response
    
    # First call - should call the API
    result1 = await auth_service.get_user_info(token)
    
    # Second call - should hit the cache
    result2 = await auth_service.get_user_info(token)

    # Verify API was called only once
    mock_client_instance.get.assert_called_once()
    assert result1 == user_info
    assert result2 == user_info
