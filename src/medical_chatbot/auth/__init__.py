"""
認證模組

提供 JWT 認證和授權功能。
"""

from medical_chatbot.auth.jwt_handler import (
    JWTHandler,
    TokenData,
    TokenPair,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token,
)
from medical_chatbot.auth.dependencies import (
    get_current_user,
    get_current_active_user,
    get_optional_user,
    require_roles,
    require_permissions,
)
from medical_chatbot.auth.models import User, UserRole, Permission
from medical_chatbot.auth.password import PasswordHandler, verify_password, hash_password
from medical_chatbot.auth.fastapi_middleware import (
    AuthMiddleware,
    setup_auth,
    create_auth_router,
)

__all__ = [
    # JWT
    "JWTHandler",
    "TokenData",
    "TokenPair",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "verify_token",
    # Dependencies
    "get_current_user",
    "get_current_active_user",
    "get_optional_user",
    "require_roles",
    "require_permissions",
    # Models
    "User",
    "UserRole",
    "Permission",
    # Password
    "PasswordHandler",
    "verify_password",
    "hash_password",
    # Middleware
    "AuthMiddleware",
    "setup_auth",
    "create_auth_router",
]
