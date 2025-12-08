"""
JWT 認證系統示範

展示如何使用 JWT 認證功能。
"""

from datetime import timedelta
from fastapi import FastAPI, Depends
import uvicorn

from medical_chatbot.auth import (
    JWTHandler,
    TokenData,
    UserRole,
    Permission,
    User,
    UserCreate,
    hash_password,
    verify_password,
    get_current_user,
    require_roles,
    require_permissions,
    setup_auth,
    create_auth_router,
)


# ============================================================================
# 基本 JWT 用法
# ============================================================================


def jwt_basic_example():
    """JWT 基本用法示範"""
    print("=" * 60)
    print("JWT 基本用法示範")
    print("=" * 60)

    # 創建 JWT 處理器
    jwt_handler = JWTHandler(
        secret_key="your-super-secret-key",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
    )

    # 創建訪問令牌
    access_token = jwt_handler.create_access_token(
        user_id="user-123",
        username="alice",
        role=UserRole.USER,
    )
    print(f"訪問令牌: {access_token[:50]}...")

    # 創建刷新令牌
    refresh_token = jwt_handler.create_refresh_token(
        user_id="user-123",
        username="alice",
    )
    print(f"刷新令牌: {refresh_token[:50]}...")

    # 創建令牌對
    token_pair = jwt_handler.create_token_pair(
        user_id="user-456",
        username="bob",
        role=UserRole.ADMIN,
    )
    print(f"\n令牌對:")
    print(f"  訪問令牌過期: {token_pair.access_expires_at}")
    print(f"  刷新令牌過期: {token_pair.refresh_expires_at}")

    # 解碼令牌
    token_data = jwt_handler.decode_token(access_token)
    print(f"\n解碼結果:")
    print(f"  用戶 ID: {token_data.sub}")
    print(f"  用戶名: {token_data.username}")
    print(f"  角色: {token_data.role}")
    print(f"  類型: {token_data.type}")

    # 驗證令牌
    verified = jwt_handler.verify_token(access_token, token_type="access")
    print(f"\n令牌驗證: {'成功' if verified else '失敗'}")

    # 撤銷令牌
    jwt_handler.revoke_token(access_token)
    revoked_check = jwt_handler.decode_token(access_token)
    print(f"撤銷後驗證: {'成功' if revoked_check else '令牌已撤銷'}")


# ============================================================================
# 密碼處理
# ============================================================================


def password_example():
    """密碼處理示範"""
    print("\n" + "=" * 60)
    print("密碼處理示範")
    print("=" * 60)

    from medical_chatbot.auth.password import PasswordHandler

    handler = PasswordHandler()

    # 哈希密碼
    password = "SecurePassword123!"
    hashed = hash_password(password)
    print(f"原始密碼: {password}")
    print(f"哈希結果: {hashed[:50]}...")

    # 驗證密碼
    is_valid = verify_password(password, hashed)
    print(f"密碼驗證: {'成功' if is_valid else '失敗'}")

    wrong_valid = verify_password("wrong_password", hashed)
    print(f"錯誤密碼驗證: {'成功' if wrong_valid else '失敗'}")

    # 生成隨機密碼
    random_password = PasswordHandler.generate_password(length=16)
    print(f"\n生成的隨機密碼: {random_password}")

    # 驗證密碼強度
    is_strong, errors = PasswordHandler.validate_password_strength(
        "weak",
        min_length=8,
        require_uppercase=True,
        require_lowercase=True,
        require_digit=True,
    )
    print(f"\n密碼 'weak' 強度驗證:")
    print(f"  有效: {is_strong}")
    print(f"  錯誤: {errors}")


# ============================================================================
# 角色和權限
# ============================================================================


def rbac_example():
    """角色權限示範"""
    print("\n" + "=" * 60)
    print("角色權限 (RBAC) 示範")
    print("=" * 60)

    from medical_chatbot.auth.models import get_role_permissions, has_permission

    # 列出各角色的權限
    for role in UserRole:
        permissions = get_role_permissions(role)
        print(f"\n{role.value} 權限:")
        for perm in sorted(permissions, key=lambda x: x.value):
            print(f"  - {perm.value}")

    # 檢查特定權限
    print("\n權限檢查:")
    print(f"  USER 有 CHAT_READ: {has_permission(UserRole.USER, Permission.CHAT_READ)}")
    print(f"  USER 有 ADMIN_WRITE: {has_permission(UserRole.USER, Permission.ADMIN_WRITE)}")
    print(f"  ADMIN 有 ADMIN_WRITE: {has_permission(UserRole.ADMIN, Permission.ADMIN_WRITE)}")

    # 創建帶額外權限的用戶
    user = User(
        id="user-123",
        username="special_user",
        hashed_password="hashed",
        role=UserRole.USER,
        extra_permissions={Permission.ADMIN_READ},  # 額外權限
    )

    print(f"\n特殊用戶權限:")
    print(f"  基本角色: {user.role.value}")
    print(f"  有 CHAT_READ: {user.has_permission(Permission.CHAT_READ)}")
    print(f"  有 ADMIN_READ: {user.has_permission(Permission.ADMIN_READ)}")  # 額外權限
    print(f"  有 ADMIN_WRITE: {user.has_permission(Permission.ADMIN_WRITE)}")


# ============================================================================
# FastAPI 整合
# ============================================================================


def fastapi_auth_example():
    """FastAPI 認證整合示範"""
    print("\n" + "=" * 60)
    print("FastAPI 認證整合示範")
    print("=" * 60)

    app = FastAPI(title="認證示範 API")

    # 設置認證（最簡單的方式）
    jwt_handler, user_store = setup_auth(
        app,
        secret_key="your-secret-key",
        access_token_expire_minutes=30,
        prefix="/auth",
    )

    # 創建測試用戶
    test_user = user_store.create_user(
        UserCreate(
            username="testuser",
            email="test@example.com",
            password="TestPass123",
            role=UserRole.USER,
        )
    )
    print(f"測試用戶已創建: {test_user.username}")

    # 受保護的端點示範
    @app.get("/protected")
    async def protected_route(user: TokenData = Depends(get_current_user)):
        """需要認證的端點"""
        return {
            "message": "你已通過認證！",
            "user_id": user.sub,
            "username": user.username,
        }

    @app.get("/admin-only")
    async def admin_route(
        user: TokenData = Depends(require_roles([UserRole.ADMIN, UserRole.SUPER_ADMIN]))
    ):
        """只有管理員可以訪問"""
        return {
            "message": "歡迎，管理員！",
            "user_id": user.sub,
        }

    @app.get("/write-permission")
    async def write_route(
        user: TokenData = Depends(require_permissions([Permission.CHAT_WRITE]))
    ):
        """需要寫入權限"""
        return {
            "message": "你有寫入權限！",
            "user_id": user.sub,
        }

    print("""
認證 API 已設置完成！

端點：
- POST /auth/register - 註冊
- POST /auth/login - 登入
- POST /auth/refresh - 刷新令牌
- POST /auth/logout - 登出
- GET /auth/me - 獲取當前用戶
- GET /auth/verify - 驗證令牌

受保護端點：
- GET /protected - 需要認證
- GET /admin-only - 需要管理員角色
- GET /write-permission - 需要寫入權限

使用方式：
1. POST /auth/login 獲取令牌
2. 在請求標頭添加: Authorization: Bearer <token>
""")

    return app


# ============================================================================
# 主程序
# ============================================================================


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Medical Chatbot JWT 認證示範")
    print("=" * 60 + "\n")

    jwt_basic_example()
    password_example()
    rbac_example()
    app = fastapi_auth_example()

    # 可選：運行服務器
    # uvicorn.run(app, host="0.0.0.0", port=8000)
