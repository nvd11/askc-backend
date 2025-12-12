from fastapi.testclient import TestClient
from server import app
from src.schemas.user import IAPUser

client = TestClient(app)

def test_get_current_user_from_iap_with_prefix():
    """
    测试从带有 accounts.google.com: 前缀的 IAP 头中获取用户信息
    """
    headers = {
        "X-Goog-Authenticated-User-Email": "accounts.google.com:testuser@example.com",
        "X-Goog-Authenticated-User-Id": "1234567890"
    }
    response = client.get("/api/v1/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "testuser@example.com"
    assert data["user_id"] == "1234567890"

def test_get_current_user_from_iap_without_prefix():
    """
    测试从不带前缀的 IAP 头中获取用户信息（虽然通常都有前缀，但也应兼容）
    """
    headers = {
        "X-Goog-Authenticated-User-Email": "testuser@example.com",
        "X-Goog-Authenticated-User-Id": "1234567890"
    }
    response = client.get("/api/v1/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "testuser@example.com"
    assert data["user_id"] == "1234567890"

def test_get_current_user_no_headers():
    """
    测试没有 IAP 头的情况
    """
    response = client.get("/api/v1/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] is None
    assert data["user_id"] is None
