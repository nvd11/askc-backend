from fastapi.testclient import TestClient
from server import app
from src.schemas.user import IAPUser
import pytest
from unittest.mock import AsyncMock, patch

client = TestClient(app)

@pytest.mark.asyncio
async def test_get_current_user_from_iap_create_new_user():
    """
    测试 IAP 用户不存在时自动创建新用户 (通过 Mock Service)
    """
    headers = {
        "X-Goog-Authenticated-User-Email": "accounts.google.com:newuser@example.com",
        "X-Goog-Authenticated-User-Id": "1234567890"
    }

    # Mock user_service.get_or_create_iap_user
    # Note: We patch where it is imported in the router, or the module itself if referenced fully.
    # In router it is imported as 'from src.services import user_service' and used as 'user_service.get_or_create_iap_user'
    
    with patch("src.routers.user_router.user_service.get_or_create_iap_user", new_callable=AsyncMock) as mock_get_or_create:
        
        # Service returns a dict as per implementation
        mock_get_or_create.return_value = {
            "email": "newuser@example.com",
            "idp_user_id": "1234567890",
            "user_id": 101,
            "username": "newuser"
        }

        response = client.get("/api/v1/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["idp_user_id"] == "1234567890"
        assert data["user_id"] == 101
        assert data["username"] == "newuser"
        
        # Verify Service was called with correct arguments
        # args[0] is db session, we might not be able to equal check it easily, but email and idp_id we can.
        call_args = mock_get_or_create.call_args
        assert call_args[0][1] == "newuser@example.com" # email
        assert call_args[0][2] == "1234567890" # idp_user_id


@pytest.mark.asyncio
async def test_get_current_user_from_iap_existing_user():
    """
    测试 IAP 用户已存在时直接返回 DB ID (通过 Mock Service)
    """
    headers = {
        "X-Goog-Authenticated-User-Email": "accounts.google.com:existing@example.com",
        "X-Goog-Authenticated-User-Id": "9876543210"
    }

    with patch("src.routers.user_router.user_service.get_or_create_iap_user", new_callable=AsyncMock) as mock_get_or_create:
        
        mock_get_or_create.return_value = {
            "email": "existing@example.com",
            "idp_user_id": "9876543210",
            "user_id": 202,
            "username": "existing"
        }

        response = client.get("/api/v1/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "existing@example.com"
        assert data["idp_user_id"] == "9876543210"
        assert data["user_id"] == 202
        assert data["username"] == "existing"

def test_get_current_user_no_headers():
    """
    测试没有 IAP 头的情况
    """
    # Service implementation handles None email gracefully (returns None user_id, etc)
    # But wait, Router extracts header. 
    # If no header, email is None.
    # Router passes None to Service.
    # Service checks if email:.
    
    # We should verify Router calls Service with None.
    
    with patch("src.routers.user_router.user_service.get_or_create_iap_user", new_callable=AsyncMock) as mock_get_or_create:
        mock_get_or_create.return_value = {
            "email": None,
            "idp_user_id": None,
            "user_id": None,
            "username": None
        }

        response = client.get("/api/v1/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] is None
        assert data["idp_user_id"] is None
        assert data["user_id"] is None
        assert data["username"] is None
        
        call_args = mock_get_or_create.call_args
        assert call_args[0][1] is None
        assert call_args[0][2] is None
