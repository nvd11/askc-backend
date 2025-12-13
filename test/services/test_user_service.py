import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.services import user_service
from src.schemas.user import UserCreateSchema

@pytest.mark.asyncio
async def test_get_or_create_iap_user_existing_email():
    """
    测试: 邮箱已存在，直接返回现有用户 ID
    """
    mock_db = AsyncMock(spec=AsyncSession)
    email = "existing@example.com"
    idp_user_id = "iap-123"
    existing_user = {"id": 10, "username": "existing", "email": email}

    # Patch user_dao methods used in user_service
    with patch("src.services.user_service.user_dao.get_user_by_email", new_callable=AsyncMock) as mock_get_by_email, \
         patch("src.services.user_service.user_dao.create_user", new_callable=AsyncMock) as mock_create_user:
        
        mock_get_by_email.return_value = existing_user

        result = await user_service.get_or_create_iap_user(mock_db, email, idp_user_id)

        # 验证结果
        assert result["email"] == email
        assert result["idp_user_id"] == idp_user_id
        assert result["user_id"] == 10
        assert result["username"] == "existing"
        
        # 验证调用
        mock_get_by_email.assert_called_once_with(mock_db, email=email)
        mock_create_user.assert_not_called()

@pytest.mark.asyncio
async def test_get_or_create_iap_user_new_user_success():
    """
    测试: 邮箱不存在，创建新用户成功
    """
    mock_db = AsyncMock(spec=AsyncSession)
    email = "newuser@example.com"
    idp_user_id = "iap-456"
    expected_username = "newuser"
    new_user_db = {"id": 20, "username": expected_username, "email": email}

    with patch("src.services.user_service.user_dao.get_user_by_email", new_callable=AsyncMock) as mock_get_by_email, \
         patch("src.services.user_service.user_dao.create_user", new_callable=AsyncMock) as mock_create_user:
        
        mock_get_by_email.return_value = None
        mock_create_user.return_value = new_user_db

        result = await user_service.get_or_create_iap_user(mock_db, email, idp_user_id)

        # 验证结果
        assert result["email"] == email
        assert result["idp_user_id"] == idp_user_id
        assert result["user_id"] == 20
        assert result["username"] == expected_username
        
        # 验证调用
        mock_get_by_email.assert_called_once_with(mock_db, email=email)
        mock_create_user.assert_called_once()
        
        # 验证传给 create_user 的参数
        call_args = mock_create_user.call_args
        assert call_args[0][0] == mock_db # db session
        created_schema = call_args[0][1]
        assert isinstance(created_schema, UserCreateSchema)
        assert created_schema.username == expected_username
        assert created_schema.email == email

@pytest.mark.asyncio
async def test_get_or_create_iap_user_creation_conflict():
    """
    测试: 邮箱不存在，但在创建时发生异常，且检查发现用户名已存在 (冲突)
    应抛出 500 错误
    """
    mock_db = AsyncMock(spec=AsyncSession)
    email = "conflict@example.com"
    idp_user_id = "iap-789"
    username = "conflict"

    with patch("src.services.user_service.user_dao.get_user_by_email", new_callable=AsyncMock) as mock_get_by_email, \
         patch("src.services.user_service.user_dao.create_user", new_callable=AsyncMock) as mock_create_user, \
         patch("src.services.user_service.user_dao.get_user_by_username", new_callable=AsyncMock) as mock_get_by_username:
        
        mock_get_by_email.return_value = None
        # 模拟创建失败
        mock_create_user.side_effect = Exception("DB Error")
        # 模拟用户名已存在
        mock_get_by_username.return_value = {"id": 99, "username": username}

        with pytest.raises(HTTPException) as exc_info:
            await user_service.get_or_create_iap_user(mock_db, email, idp_user_id)
        
        assert exc_info.value.status_code == 500
        assert "username conflict" in exc_info.value.detail

@pytest.mark.asyncio
async def test_get_or_create_iap_user_creation_other_error():
    """
    测试: 邮箱不存在，创建时发生异常，且用户名也不存在 (真正的数据库错误)
    应抛出原始异常
    """
    mock_db = AsyncMock(spec=AsyncSession)
    email = "error@example.com"
    idp_user_id = "iap-000"

    with patch("src.services.user_service.user_dao.get_user_by_email", new_callable=AsyncMock) as mock_get_by_email, \
         patch("src.services.user_service.user_dao.create_user", new_callable=AsyncMock) as mock_create_user, \
         patch("src.services.user_service.user_dao.get_user_by_username", new_callable=AsyncMock) as mock_get_by_username:
        
        mock_get_by_email.return_value = None
        # 模拟创建失败
        db_error = Exception("Connection Failed")
        mock_create_user.side_effect = db_error
        # 用户名也不存在
        mock_get_by_username.return_value = None

        with pytest.raises(Exception) as exc_info:
            await user_service.get_or_create_iap_user(mock_db, email, idp_user_id)
        
        assert exc_info.value is db_error
