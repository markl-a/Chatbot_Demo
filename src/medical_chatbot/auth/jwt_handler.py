"""
JWT 處理器

處理 JWT 令牌的創建、驗證和解碼。
"""

import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from loguru import logger
from pydantic import BaseModel

from medical_chatbot.auth.models import UserRole


class TokenData(BaseModel):
    """令牌數據模型"""
    sub: str  # 主體（用戶 ID）
    username: Optional[str] = None
    role: Optional[UserRole] = None
    exp: Optional[datetime] = None
    iat: Optional[datetime] = None
    jti: Optional[str] = None  # JWT ID
    type: str = "access"  # access 或 refresh


@dataclass
class TokenPair:
    """令牌對"""
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime


class JWTHandler:
    """
    JWT 處理器

    支援：
    - 創建訪問令牌和刷新令牌
    - 驗證和解碼令牌
    - 令牌黑名單（可選）
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
        issuer: Optional[str] = None,
        audience: Optional[str] = None,
    ):
        """
        初始化 JWT 處理器

        Args:
            secret_key: 密鑰（如果未提供，將從環境變量獲取或生成）
            algorithm: 加密算法
            access_token_expire_minutes: 訪問令牌過期時間（分鐘）
            refresh_token_expire_days: 刷新令牌過期時間（天）
            issuer: 發行者
            audience: 受眾
        """
        self.secret_key = secret_key or os.getenv("JWT_SECRET_KEY") or secrets.token_urlsafe(32)
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.issuer = issuer
        self.audience = audience

        # 令牌黑名單（用於撤銷令牌）
        self._blacklist: set = set()

        logger.info(f"JWT 處理器初始化完成 (算法: {algorithm})")

    def create_access_token(
        self,
        user_id: str,
        username: Optional[str] = None,
        role: Optional[UserRole] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        創建訪問令牌

        Args:
            user_id: 用戶 ID
            username: 用戶名
            role: 用戶角色
            extra_data: 額外數據
            expires_delta: 自定義過期時間

        Returns:
            JWT 字符串
        """
        return self._create_token(
            user_id=user_id,
            username=username,
            role=role,
            extra_data=extra_data,
            expires_delta=expires_delta or timedelta(minutes=self.access_token_expire_minutes),
            token_type="access",
        )

    def create_refresh_token(
        self,
        user_id: str,
        username: Optional[str] = None,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        創建刷新令牌

        Args:
            user_id: 用戶 ID
            username: 用戶名
            expires_delta: 自定義過期時間

        Returns:
            JWT 字符串
        """
        return self._create_token(
            user_id=user_id,
            username=username,
            role=None,
            extra_data=None,
            expires_delta=expires_delta or timedelta(days=self.refresh_token_expire_days),
            token_type="refresh",
        )

    def create_token_pair(
        self,
        user_id: str,
        username: Optional[str] = None,
        role: Optional[UserRole] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> TokenPair:
        """
        創建令牌對（訪問令牌 + 刷新令牌）

        Args:
            user_id: 用戶 ID
            username: 用戶名
            role: 用戶角色
            extra_data: 額外數據

        Returns:
            TokenPair 實例
        """
        now = datetime.utcnow()
        access_expires = now + timedelta(minutes=self.access_token_expire_minutes)
        refresh_expires = now + timedelta(days=self.refresh_token_expire_days)

        access_token = self.create_access_token(
            user_id=user_id,
            username=username,
            role=role,
            extra_data=extra_data,
        )

        refresh_token = self.create_refresh_token(
            user_id=user_id,
            username=username,
        )

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_at=access_expires,
            refresh_expires_at=refresh_expires,
        )

    def _create_token(
        self,
        user_id: str,
        username: Optional[str],
        role: Optional[UserRole],
        extra_data: Optional[Dict[str, Any]],
        expires_delta: timedelta,
        token_type: str,
    ) -> str:
        """創建令牌的內部方法"""
        now = datetime.utcnow()
        expire = now + expires_delta

        payload = {
            "sub": user_id,
            "type": token_type,
            "iat": now,
            "exp": expire,
            "jti": secrets.token_urlsafe(16),
        }

        if username:
            payload["username"] = username

        if role:
            payload["role"] = role.value

        if self.issuer:
            payload["iss"] = self.issuer

        if self.audience:
            payload["aud"] = self.audience

        if extra_data:
            payload.update(extra_data)

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_token(
        self,
        token: str,
        verify_exp: bool = True,
    ) -> Optional[TokenData]:
        """
        解碼令牌

        Args:
            token: JWT 字符串
            verify_exp: 是否驗證過期時間

        Returns:
            TokenData 實例，或 None（如果解碼失敗）
        """
        try:
            options = {"verify_exp": verify_exp}

            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options=options,
                audience=self.audience,
                issuer=self.issuer,
            )

            # 檢查黑名單
            jti = payload.get("jti")
            if jti and jti in self._blacklist:
                logger.warning(f"令牌已被撤銷: {jti}")
                return None

            # 解析角色
            role = None
            if payload.get("role"):
                try:
                    role = UserRole(payload["role"])
                except ValueError:
                    pass

            return TokenData(
                sub=payload.get("sub"),
                username=payload.get("username"),
                role=role,
                exp=datetime.fromtimestamp(payload.get("exp")) if payload.get("exp") else None,
                iat=datetime.fromtimestamp(payload.get("iat")) if payload.get("iat") else None,
                jti=jti,
                type=payload.get("type", "access"),
            )

        except JWTError as e:
            logger.debug(f"令牌解碼失敗: {e}")
            return None

    def verify_token(
        self,
        token: str,
        token_type: str = "access",
    ) -> Optional[TokenData]:
        """
        驗證令牌

        Args:
            token: JWT 字符串
            token_type: 預期的令牌類型

        Returns:
            TokenData 實例，或 None（如果驗證失敗）
        """
        token_data = self.decode_token(token)

        if token_data is None:
            return None

        if token_data.type != token_type:
            logger.warning(f"令牌類型不匹配: 預期 {token_type}, 實際 {token_data.type}")
            return None

        return token_data

    def revoke_token(self, token: str):
        """
        撤銷令牌

        Args:
            token: JWT 字符串
        """
        token_data = self.decode_token(token, verify_exp=False)
        if token_data and token_data.jti:
            self._blacklist.add(token_data.jti)
            logger.info(f"令牌已撤銷: {token_data.jti}")

    def is_token_revoked(self, token: str) -> bool:
        """
        檢查令牌是否已被撤銷

        Args:
            token: JWT 字符串

        Returns:
            是否已撤銷
        """
        token_data = self.decode_token(token, verify_exp=False)
        if token_data and token_data.jti:
            return token_data.jti in self._blacklist
        return False

    def clear_blacklist(self):
        """清空黑名單"""
        self._blacklist.clear()


# ============================================================================
# 全局實例和便捷函數
# ============================================================================

_jwt_handler: Optional[JWTHandler] = None


def get_jwt_handler() -> JWTHandler:
    """獲取全局 JWT 處理器"""
    global _jwt_handler
    if _jwt_handler is None:
        _jwt_handler = JWTHandler()
    return _jwt_handler


def set_jwt_handler(handler: JWTHandler):
    """設置全局 JWT 處理器"""
    global _jwt_handler
    _jwt_handler = handler


def create_access_token(
    user_id: str,
    username: Optional[str] = None,
    role: Optional[UserRole] = None,
    extra_data: Optional[Dict[str, Any]] = None,
) -> str:
    """創建訪問令牌（便捷函數）"""
    return get_jwt_handler().create_access_token(
        user_id=user_id,
        username=username,
        role=role,
        extra_data=extra_data,
    )


def create_refresh_token(
    user_id: str,
    username: Optional[str] = None,
) -> str:
    """創建刷新令牌（便捷函數）"""
    return get_jwt_handler().create_refresh_token(
        user_id=user_id,
        username=username,
    )


def decode_token(token: str) -> Optional[TokenData]:
    """解碼令牌（便捷函數）"""
    return get_jwt_handler().decode_token(token)


def verify_token(token: str, token_type: str = "access") -> Optional[TokenData]:
    """驗證令牌（便捷函數）"""
    return get_jwt_handler().verify_token(token, token_type)
