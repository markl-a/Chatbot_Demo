"""
認證依賴

FastAPI 依賴注入函數。
"""

from functools import wraps
from typing import Callable, List, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger

from medical_chatbot.auth.jwt_handler import TokenData, get_jwt_handler
from medical_chatbot.auth.models import Permission, User, UserRole, get_role_permissions


# HTTP Bearer 認證方案
security = HTTPBearer(auto_error=False)


async def get_token_data(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[TokenData]:
    """
    從請求中提取令牌數據

    Args:
        credentials: HTTP 認證憑證

    Returns:
        TokenData 或 None
    """
    if credentials is None:
        return None

    token = credentials.credentials
    jwt_handler = get_jwt_handler()

    return jwt_handler.verify_token(token, token_type="access")


async def get_current_user(
    token_data: Optional[TokenData] = Depends(get_token_data),
) -> TokenData:
    """
    獲取當前用戶（必須認證）

    Args:
        token_data: 令牌數據

    Returns:
        TokenData

    Raises:
        HTTPException: 未認證
    """
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未認證或令牌無效",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token_data


async def get_current_active_user(
    token_data: TokenData = Depends(get_current_user),
) -> TokenData:
    """
    獲取當前活躍用戶

    可以在這裡添加額外的檢查，例如：
    - 用戶是否被禁用
    - 用戶是否已驗證郵箱
    等

    Args:
        token_data: 令牌數據

    Returns:
        TokenData
    """
    # 可以在這裡查詢數據庫檢查用戶狀態
    # 目前直接返回令牌數據
    return token_data


async def get_optional_user(
    token_data: Optional[TokenData] = Depends(get_token_data),
) -> Optional[TokenData]:
    """
    獲取可選用戶（不要求認證）

    Args:
        token_data: 令牌數據

    Returns:
        TokenData 或 None
    """
    return token_data


def require_roles(roles: List[UserRole]) -> Callable:
    """
    要求特定角色

    Args:
        roles: 允許的角色列表

    Returns:
        依賴函數
    """

    async def role_checker(
        token_data: TokenData = Depends(get_current_user),
    ) -> TokenData:
        if token_data.role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="令牌中缺少角色信息",
            )

        if token_data.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要角色: {[r.value for r in roles]}",
            )

        return token_data

    return role_checker


def require_permissions(permissions: List[Permission]) -> Callable:
    """
    要求特定權限

    Args:
        permissions: 需要的權限列表

    Returns:
        依賴函數
    """

    async def permission_checker(
        token_data: TokenData = Depends(get_current_user),
    ) -> TokenData:
        if token_data.role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="令牌中缺少角色信息",
            )

        user_permissions = get_role_permissions(token_data.role)

        missing_permissions = [p for p in permissions if p not in user_permissions]

        if missing_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少權限: {[p.value for p in missing_permissions]}",
            )

        return token_data

    return permission_checker


class RoleRequired:
    """
    角色要求裝飾器類

    使用方式：
    @app.get("/admin")
    @RoleRequired([UserRole.ADMIN])
    async def admin_endpoint(user: TokenData = Depends(get_current_user)):
        ...
    """

    def __init__(self, roles: List[UserRole]):
        self.roles = roles

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        # 添加依賴
        wrapper.__wrapped__ = func
        return wrapper


class PermissionRequired:
    """
    權限要求裝飾器類

    使用方式：
    @app.get("/users")
    @PermissionRequired([Permission.USER_READ])
    async def users_endpoint(user: TokenData = Depends(get_current_user)):
        ...
    """

    def __init__(self, permissions: List[Permission]):
        self.permissions = permissions

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        wrapper.__wrapped__ = func
        return wrapper


# ============================================================================
# WebSocket 認證
# ============================================================================


async def get_websocket_user(token: Optional[str]) -> Optional[TokenData]:
    """
    從 WebSocket 連接參數獲取用戶

    Args:
        token: 令牌字符串

    Returns:
        TokenData 或 None
    """
    if token is None:
        return None

    jwt_handler = get_jwt_handler()
    return jwt_handler.verify_token(token, token_type="access")


def require_websocket_auth(token: Optional[str]) -> TokenData:
    """
    要求 WebSocket 認證

    Args:
        token: 令牌字符串

    Returns:
        TokenData

    Raises:
        HTTPException: 未認證
    """
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少認證令牌",
        )

    jwt_handler = get_jwt_handler()
    token_data = jwt_handler.verify_token(token, token_type="access")

    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的認證令牌",
        )

    return token_data
