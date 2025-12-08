"""
認證模型

定義用戶、角色和權限模型。
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Set

from pydantic import BaseModel, EmailStr, Field


class Permission(str, Enum):
    """權限枚舉"""
    # 聊天權限
    CHAT_READ = "chat:read"
    CHAT_WRITE = "chat:write"
    CHAT_STREAM = "chat:stream"

    # 對話權限
    CONVERSATION_READ = "conversation:read"
    CONVERSATION_WRITE = "conversation:write"
    CONVERSATION_DELETE = "conversation:delete"

    # 用戶管理
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"

    # 系統管理
    ADMIN_READ = "admin:read"
    ADMIN_WRITE = "admin:write"
    SYSTEM_MANAGE = "system:manage"

    # API 權限
    API_ACCESS = "api:access"
    API_UNLIMITED = "api:unlimited"


class UserRole(str, Enum):
    """用戶角色枚舉"""
    GUEST = "guest"
    USER = "user"
    PREMIUM = "premium"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


# 角色權限映射
ROLE_PERMISSIONS: dict[UserRole, Set[Permission]] = {
    UserRole.GUEST: {
        Permission.CHAT_READ,
        Permission.API_ACCESS,
    },
    UserRole.USER: {
        Permission.CHAT_READ,
        Permission.CHAT_WRITE,
        Permission.CHAT_STREAM,
        Permission.CONVERSATION_READ,
        Permission.CONVERSATION_WRITE,
        Permission.API_ACCESS,
    },
    UserRole.PREMIUM: {
        Permission.CHAT_READ,
        Permission.CHAT_WRITE,
        Permission.CHAT_STREAM,
        Permission.CONVERSATION_READ,
        Permission.CONVERSATION_WRITE,
        Permission.CONVERSATION_DELETE,
        Permission.API_ACCESS,
        Permission.API_UNLIMITED,
    },
    UserRole.MODERATOR: {
        Permission.CHAT_READ,
        Permission.CHAT_WRITE,
        Permission.CHAT_STREAM,
        Permission.CONVERSATION_READ,
        Permission.CONVERSATION_WRITE,
        Permission.CONVERSATION_DELETE,
        Permission.USER_READ,
        Permission.API_ACCESS,
        Permission.API_UNLIMITED,
        Permission.ADMIN_READ,
    },
    UserRole.ADMIN: {
        Permission.CHAT_READ,
        Permission.CHAT_WRITE,
        Permission.CHAT_STREAM,
        Permission.CONVERSATION_READ,
        Permission.CONVERSATION_WRITE,
        Permission.CONVERSATION_DELETE,
        Permission.USER_READ,
        Permission.USER_WRITE,
        Permission.API_ACCESS,
        Permission.API_UNLIMITED,
        Permission.ADMIN_READ,
        Permission.ADMIN_WRITE,
    },
    UserRole.SUPER_ADMIN: set(Permission),  # 所有權限
}


def get_role_permissions(role: UserRole) -> Set[Permission]:
    """獲取角色的所有權限"""
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(role: UserRole, permission: Permission) -> bool:
    """檢查角色是否有特定權限"""
    return permission in get_role_permissions(role)


class UserBase(BaseModel):
    """用戶基礎模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用戶名")
    email: Optional[EmailStr] = Field(None, description="電子郵件")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")
    role: UserRole = Field(default=UserRole.USER, description="用戶角色")
    is_active: bool = Field(default=True, description="是否啟用")


class UserCreate(UserBase):
    """用戶創建模型"""
    password: str = Field(..., min_length=8, description="密碼")


class UserUpdate(BaseModel):
    """用戶更新模型"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class User(UserBase):
    """用戶模型"""
    id: str = Field(..., description="用戶 ID")
    hashed_password: str = Field(..., description="哈希密碼")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="創建時間")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新時間")
    last_login: Optional[datetime] = Field(None, description="最後登入時間")
    extra_permissions: Set[Permission] = Field(default_factory=set, description="額外權限")

    class Config:
        from_attributes = True

    @property
    def permissions(self) -> Set[Permission]:
        """獲取用戶的所有權限（角色權限 + 額外權限）"""
        return get_role_permissions(self.role) | self.extra_permissions

    def has_permission(self, permission: Permission) -> bool:
        """檢查用戶是否有特定權限"""
        return permission in self.permissions

    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """檢查用戶是否有任一權限"""
        return any(p in self.permissions for p in permissions)

    def has_all_permissions(self, permissions: List[Permission]) -> bool:
        """檢查用戶是否有所有權限"""
        return all(p in self.permissions for p in permissions)


class UserResponse(BaseModel):
    """用戶響應模型（不包含敏感信息）"""
    id: str
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """登入請求模型"""
    username: str = Field(..., description="用戶名或電子郵件")
    password: str = Field(..., description="密碼")


class LoginResponse(BaseModel):
    """登入響應模型"""
    access_token: str = Field(..., description="訪問令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌類型")
    expires_in: int = Field(..., description="過期時間（秒）")
    user: UserResponse = Field(..., description="用戶信息")


class RefreshRequest(BaseModel):
    """刷新令牌請求模型"""
    refresh_token: str = Field(..., description="刷新令牌")


class TokenResponse(BaseModel):
    """令牌響應模型"""
    access_token: str = Field(..., description="訪問令牌")
    token_type: str = Field(default="bearer", description="令牌類型")
    expires_in: int = Field(..., description="過期時間（秒）")
