"""
認證測試

測試 JWT 認證和授權功能。
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from medical_chatbot.auth.jwt_handler import JWTHandler, TokenData, TokenPair
from medical_chatbot.auth.password import PasswordHandler
from medical_chatbot.auth.models import (
    User,
    UserRole,
    Permission,
    UserCreate,
    get_role_permissions,
    has_permission,
)


# ============================================================================
# JWT Handler 測試
# ============================================================================


class TestJWTHandler:
    """JWT 處理器測試"""

    @pytest.fixture
    def jwt_handler(self):
        """創建 JWT 處理器"""
        return JWTHandler(
            secret_key="test-secret-key",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7,
        )

    def test_create_access_token(self, jwt_handler):
        """測試創建訪問令牌"""
        token = jwt_handler.create_access_token(
            user_id="user-123",
            username="testuser",
            role=UserRole.USER,
        )

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self, jwt_handler):
        """測試創建刷新令牌"""
        token = jwt_handler.create_refresh_token(
            user_id="user-123",
            username="testuser",
        )

        assert token is not None
        assert isinstance(token, str)

    def test_create_token_pair(self, jwt_handler):
        """測試創建令牌對"""
        token_pair = jwt_handler.create_token_pair(
            user_id="user-123",
            username="testuser",
            role=UserRole.USER,
        )

        assert isinstance(token_pair, TokenPair)
        assert token_pair.access_token is not None
        assert token_pair.refresh_token is not None
        assert token_pair.access_expires_at > datetime.utcnow()
        assert token_pair.refresh_expires_at > datetime.utcnow()

    def test_decode_access_token(self, jwt_handler):
        """測試解碼訪問令牌"""
        token = jwt_handler.create_access_token(
            user_id="user-123",
            username="testuser",
            role=UserRole.ADMIN,
        )

        token_data = jwt_handler.decode_token(token)

        assert token_data is not None
        assert token_data.sub == "user-123"
        assert token_data.username == "testuser"
        assert token_data.role == UserRole.ADMIN
        assert token_data.type == "access"

    def test_decode_refresh_token(self, jwt_handler):
        """測試解碼刷新令牌"""
        token = jwt_handler.create_refresh_token(
            user_id="user-123",
            username="testuser",
        )

        token_data = jwt_handler.decode_token(token)

        assert token_data is not None
        assert token_data.sub == "user-123"
        assert token_data.type == "refresh"

    def test_verify_token_type(self, jwt_handler):
        """測試驗證令牌類型"""
        access_token = jwt_handler.create_access_token(user_id="user-123")
        refresh_token = jwt_handler.create_refresh_token(user_id="user-123")

        # 驗證訪問令牌
        access_data = jwt_handler.verify_token(access_token, token_type="access")
        assert access_data is not None

        # 訪問令牌不應該通過刷新令牌驗證
        wrong_type = jwt_handler.verify_token(access_token, token_type="refresh")
        assert wrong_type is None

        # 驗證刷新令牌
        refresh_data = jwt_handler.verify_token(refresh_token, token_type="refresh")
        assert refresh_data is not None

    def test_invalid_token(self, jwt_handler):
        """測試無效令牌"""
        token_data = jwt_handler.decode_token("invalid-token")
        assert token_data is None

    def test_expired_token(self, jwt_handler):
        """測試過期令牌"""
        # 創建已過期的令牌
        token = jwt_handler.create_access_token(
            user_id="user-123",
            expires_delta=timedelta(seconds=-1),  # 已過期
        )

        token_data = jwt_handler.decode_token(token)
        assert token_data is None

    def test_revoke_token(self, jwt_handler):
        """測試撤銷令牌"""
        token = jwt_handler.create_access_token(user_id="user-123")

        # 撤銷前可以解碼
        assert jwt_handler.decode_token(token) is not None

        # 撤銷令牌
        jwt_handler.revoke_token(token)

        # 撤銷後無法解碼
        assert jwt_handler.decode_token(token) is None

    def test_is_token_revoked(self, jwt_handler):
        """測試檢查令牌是否已撤銷"""
        token = jwt_handler.create_access_token(user_id="user-123")

        assert jwt_handler.is_token_revoked(token) is False

        jwt_handler.revoke_token(token)

        assert jwt_handler.is_token_revoked(token) is True

    def test_extra_data_in_token(self, jwt_handler):
        """測試令牌中的額外數據"""
        token = jwt_handler.create_access_token(
            user_id="user-123",
            extra_data={"custom_field": "custom_value"},
        )

        # 額外數據應該被編碼但不在 TokenData 中
        # 可以通過原始解碼獲取
        from jose import jwt as jose_jwt
        payload = jose_jwt.decode(
            token,
            jwt_handler.secret_key,
            algorithms=[jwt_handler.algorithm],
        )

        assert payload.get("custom_field") == "custom_value"


# ============================================================================
# Password Handler 測試
# ============================================================================


class TestPasswordHandler:
    """密碼處理器測試"""

    @pytest.fixture
    def password_handler(self):
        """創建密碼處理器"""
        return PasswordHandler()

    def test_hash_password(self, password_handler):
        """測試密碼哈希"""
        password = "secure_password_123"
        hashed = password_handler.hash_password(password)

        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 0

    def test_verify_password(self, password_handler):
        """測試密碼驗證"""
        password = "secure_password_123"
        hashed = password_handler.hash_password(password)

        assert password_handler.verify_password(password, hashed) is True
        assert password_handler.verify_password("wrong_password", hashed) is False

    def test_different_hashes(self, password_handler):
        """測試相同密碼產生不同哈希"""
        password = "secure_password_123"
        hash1 = password_handler.hash_password(password)
        hash2 = password_handler.hash_password(password)

        # 應該產生不同的哈希（因為使用隨機鹽）
        assert hash1 != hash2

        # 但兩個哈希都應該驗證成功
        assert password_handler.verify_password(password, hash1) is True
        assert password_handler.verify_password(password, hash2) is True

    def test_generate_password(self):
        """測試生成密碼"""
        password = PasswordHandler.generate_password(length=16)

        assert len(password) == 16
        assert any(c.isupper() for c in password)
        assert any(c.islower() for c in password)
        assert any(c.isdigit() for c in password)

    def test_generate_password_custom(self):
        """測試自定義生成密碼"""
        password = PasswordHandler.generate_password(
            length=12,
            include_uppercase=True,
            include_lowercase=True,
            include_digits=False,
            include_special=False,
        )

        assert len(password) == 12
        assert not any(c.isdigit() for c in password)

    def test_validate_password_strength(self):
        """測試密碼強度驗證"""
        # 強密碼
        is_valid, errors = PasswordHandler.validate_password_strength(
            "SecurePass123",
            min_length=8,
            require_uppercase=True,
            require_lowercase=True,
            require_digit=True,
        )
        assert is_valid is True
        assert len(errors) == 0

        # 弱密碼
        is_valid, errors = PasswordHandler.validate_password_strength(
            "weak",
            min_length=8,
            require_uppercase=True,
            require_lowercase=True,
            require_digit=True,
        )
        assert is_valid is False
        assert len(errors) > 0


# ============================================================================
# User Model 測試
# ============================================================================


class TestUserModel:
    """用戶模型測試"""

    def test_get_role_permissions(self):
        """測試獲取角色權限"""
        user_permissions = get_role_permissions(UserRole.USER)

        assert Permission.CHAT_READ in user_permissions
        assert Permission.CHAT_WRITE in user_permissions
        assert Permission.ADMIN_WRITE not in user_permissions

    def test_admin_permissions(self):
        """測試管理員權限"""
        admin_permissions = get_role_permissions(UserRole.ADMIN)

        assert Permission.ADMIN_READ in admin_permissions
        assert Permission.ADMIN_WRITE in admin_permissions
        assert Permission.USER_READ in admin_permissions
        assert Permission.USER_WRITE in admin_permissions

    def test_super_admin_all_permissions(self):
        """測試超級管理員擁有所有權限"""
        super_admin_permissions = get_role_permissions(UserRole.SUPER_ADMIN)

        # 應該擁有所有權限
        for permission in Permission:
            assert permission in super_admin_permissions

    def test_has_permission(self):
        """測試權限檢查"""
        assert has_permission(UserRole.USER, Permission.CHAT_READ) is True
        assert has_permission(UserRole.USER, Permission.ADMIN_WRITE) is False
        assert has_permission(UserRole.ADMIN, Permission.ADMIN_WRITE) is True

    def test_user_model(self):
        """測試用戶模型"""
        user = User(
            id="user-123",
            username="testuser",
            email="test@example.com",
            hashed_password="hashed",
            role=UserRole.USER,
        )

        assert user.id == "user-123"
        assert user.username == "testuser"
        assert user.has_permission(Permission.CHAT_READ) is True
        assert user.has_permission(Permission.ADMIN_WRITE) is False

    def test_user_extra_permissions(self):
        """測試用戶額外權限"""
        user = User(
            id="user-123",
            username="testuser",
            hashed_password="hashed",
            role=UserRole.USER,
            extra_permissions={Permission.ADMIN_READ},
        )

        # 用戶角色沒有 ADMIN_READ，但有額外權限
        assert user.has_permission(Permission.ADMIN_READ) is True

    def test_user_has_any_permission(self):
        """測試任一權限檢查"""
        user = User(
            id="user-123",
            username="testuser",
            hashed_password="hashed",
            role=UserRole.USER,
        )

        assert user.has_any_permission([Permission.CHAT_READ, Permission.ADMIN_WRITE]) is True
        assert user.has_any_permission([Permission.ADMIN_READ, Permission.ADMIN_WRITE]) is False

    def test_user_has_all_permissions(self):
        """測試所有權限檢查"""
        user = User(
            id="user-123",
            username="testuser",
            hashed_password="hashed",
            role=UserRole.USER,
        )

        assert user.has_all_permissions([Permission.CHAT_READ, Permission.CHAT_WRITE]) is True
        assert user.has_all_permissions([Permission.CHAT_READ, Permission.ADMIN_WRITE]) is False

    def test_user_create_model(self):
        """測試用戶創建模型"""
        user_create = UserCreate(
            username="newuser",
            email="new@example.com",
            password="SecurePass123",
            full_name="New User",
        )

        assert user_create.username == "newuser"
        assert user_create.password == "SecurePass123"
        assert user_create.role == UserRole.USER  # 默認角色
