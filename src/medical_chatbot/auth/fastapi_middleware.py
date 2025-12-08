"""
認證中間件和路由

FastAPI 認證整合。
"""

import uuid
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from medical_chatbot.auth.jwt_handler import JWTHandler, TokenData, get_jwt_handler, set_jwt_handler
from medical_chatbot.auth.models import (
    LoginRequest,
    LoginResponse,
    Permission,
    RefreshRequest,
    TokenResponse,
    User,
    UserCreate,
    UserResponse,
    UserRole,
)
from medical_chatbot.auth.password import hash_password, verify_password
from medical_chatbot.auth.dependencies import get_current_user, get_optional_user


class AuthMiddleware(BaseHTTPMiddleware):
    """
    認證中間件

    在每個請求中驗證令牌並注入用戶信息。
    """

    def __init__(
        self,
        app,
        jwt_handler: Optional[JWTHandler] = None,
        exclude_paths: list = None,
    ):
        """
        初始化認證中間件

        Args:
            app: FastAPI 應用
            jwt_handler: JWT 處理器
            exclude_paths: 排除認證的路徑列表
        """
        super().__init__(app)
        self.jwt_handler = jwt_handler or get_jwt_handler()
        self.exclude_paths = exclude_paths or [
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth/login",
            "/auth/register",
            "/auth/refresh",
        ]

    async def dispatch(self, request: Request, call_next: Callable):
        """處理請求"""
        # 檢查是否排除路徑
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            return await call_next(request)

        # 獲取令牌
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            token_data = self.jwt_handler.verify_token(token)

            if token_data:
                # 注入用戶信息到請求狀態
                request.state.user = token_data
                request.state.user_id = token_data.sub
                request.state.user_role = token_data.role

        response = await call_next(request)
        return response


class UserStore:
    """
    簡單的用戶存儲（示例用）

    生產環境應該使用數據庫。
    """

    def __init__(self):
        self._users: Dict[str, User] = {}
        self._username_index: Dict[str, str] = {}  # username -> user_id
        self._email_index: Dict[str, str] = {}  # email -> user_id

    def create_user(self, user_create: UserCreate) -> User:
        """創建用戶"""
        # 檢查用戶名是否已存在
        if user_create.username in self._username_index:
            raise ValueError("用戶名已存在")

        # 檢查郵箱是否已存在
        if user_create.email and user_create.email in self._email_index:
            raise ValueError("郵箱已被使用")

        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            username=user_create.username,
            email=user_create.email,
            full_name=user_create.full_name,
            role=user_create.role,
            is_active=user_create.is_active,
            hashed_password=hash_password(user_create.password),
        )

        self._users[user_id] = user
        self._username_index[user_create.username] = user_id
        if user_create.email:
            self._email_index[user_create.email] = user_id

        return user

    def get_user(self, user_id: str) -> Optional[User]:
        """獲取用戶"""
        return self._users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """通過用戶名獲取用戶"""
        user_id = self._username_index.get(username)
        if user_id:
            return self._users.get(user_id)
        return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """通過郵箱獲取用戶"""
        user_id = self._email_index.get(email)
        if user_id:
            return self._users.get(user_id)
        return None

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """驗證用戶"""
        user = self.get_user_by_username(username)
        if user is None:
            # 嘗試通過郵箱查找
            user = self.get_user_by_email(username)

        if user is None:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        if not user.is_active:
            return None

        return user

    def update_last_login(self, user_id: str):
        """更新最後登入時間"""
        user = self._users.get(user_id)
        if user:
            user.last_login = datetime.utcnow()


# 全局用戶存儲
_user_store: Optional[UserStore] = None


def get_user_store() -> UserStore:
    """獲取用戶存儲"""
    global _user_store
    if _user_store is None:
        _user_store = UserStore()
    return _user_store


def create_auth_router(
    jwt_handler: Optional[JWTHandler] = None,
    user_store: Optional[UserStore] = None,
    prefix: str = "/auth",
    tags: list = None,
) -> APIRouter:
    """
    創建認證路由

    Args:
        jwt_handler: JWT 處理器
        user_store: 用戶存儲
        prefix: 路由前綴
        tags: API 標籤

    Returns:
        FastAPI APIRouter
    """
    router = APIRouter(prefix=prefix, tags=tags or ["認證"])

    jwt = jwt_handler or get_jwt_handler()
    store = user_store or get_user_store()

    @router.post("/register", response_model=UserResponse)
    async def register(user_create: UserCreate):
        """
        註冊新用戶

        創建一個新的用戶帳戶。
        """
        try:
            user = store.create_user(user_create)
            logger.info(f"用戶註冊成功: {user.username}")
            return UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                role=user.role,
                is_active=user.is_active,
                created_at=user.created_at,
                last_login=user.last_login,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    @router.post("/login", response_model=LoginResponse)
    async def login(login_request: LoginRequest):
        """
        用戶登入

        驗證憑證並返回訪問令牌和刷新令牌。
        """
        user = store.authenticate(login_request.username, login_request.password)

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用戶名或密碼錯誤",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 更新最後登入時間
        store.update_last_login(user.id)

        # 創建令牌對
        token_pair = jwt.create_token_pair(
            user_id=user.id,
            username=user.username,
            role=user.role,
        )

        logger.info(f"用戶登入成功: {user.username}")

        return LoginResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            token_type="bearer",
            expires_in=jwt.access_token_expire_minutes * 60,
            user=UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                role=user.role,
                is_active=user.is_active,
                created_at=user.created_at,
                last_login=user.last_login,
            ),
        )

    @router.post("/refresh", response_model=TokenResponse)
    async def refresh(refresh_request: RefreshRequest):
        """
        刷新訪問令牌

        使用刷新令牌獲取新的訪問令牌。
        """
        token_data = jwt.verify_token(refresh_request.refresh_token, token_type="refresh")

        if token_data is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無效的刷新令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 獲取用戶（可選：檢查用戶是否仍然有效）
        user = store.get_user(token_data.sub)
        if user and not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用戶已被禁用",
            )

        # 創建新的訪問令牌
        role = user.role if user else token_data.role
        access_token = jwt.create_access_token(
            user_id=token_data.sub,
            username=token_data.username,
            role=role,
        )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=jwt.access_token_expire_minutes * 60,
        )

    @router.post("/logout")
    async def logout(
        token_data: TokenData = Depends(get_current_user),
        credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    ):
        """
        用戶登出

        撤銷當前的訪問令牌。
        """
        jwt.revoke_token(credentials.credentials)
        logger.info(f"用戶登出: {token_data.username}")
        return {"message": "登出成功"}

    @router.get("/me", response_model=UserResponse)
    async def get_me(token_data: TokenData = Depends(get_current_user)):
        """
        獲取當前用戶信息
        """
        user = store.get_user(token_data.sub)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用戶不存在",
            )

        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login,
        )

    @router.get("/verify")
    async def verify_token_endpoint(token_data: TokenData = Depends(get_current_user)):
        """
        驗證令牌

        檢查令牌是否有效。
        """
        return {
            "valid": True,
            "user_id": token_data.sub,
            "username": token_data.username,
            "role": token_data.role.value if token_data.role else None,
            "expires_at": token_data.exp.isoformat() if token_data.exp else None,
        }

    return router


def setup_auth(
    app: FastAPI,
    secret_key: Optional[str] = None,
    access_token_expire_minutes: int = 30,
    refresh_token_expire_days: int = 7,
    exclude_paths: list = None,
    add_middleware: bool = True,
    prefix: str = "/auth",
) -> tuple[JWTHandler, UserStore]:
    """
    設置認證功能

    Args:
        app: FastAPI 應用
        secret_key: JWT 密鑰
        access_token_expire_minutes: 訪問令牌過期時間
        refresh_token_expire_days: 刷新令牌過期時間
        exclude_paths: 排除認證的路徑
        add_middleware: 是否添加認證中間件
        prefix: 認證路由前綴

    Returns:
        (JWTHandler, UserStore) 元組
    """
    # 創建 JWT 處理器
    jwt_handler = JWTHandler(
        secret_key=secret_key,
        access_token_expire_minutes=access_token_expire_minutes,
        refresh_token_expire_days=refresh_token_expire_days,
    )
    set_jwt_handler(jwt_handler)

    # 創建用戶存儲
    user_store = get_user_store()

    # 添加認證路由
    router = create_auth_router(
        jwt_handler=jwt_handler,
        user_store=user_store,
        prefix=prefix,
    )
    app.include_router(router)

    # 添加認證中間件
    if add_middleware:
        app.add_middleware(
            AuthMiddleware,
            jwt_handler=jwt_handler,
            exclude_paths=exclude_paths,
        )

    logger.info("認證功能已設置完成")

    return jwt_handler, user_store
