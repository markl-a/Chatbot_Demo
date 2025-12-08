"""
密碼處理器

處理密碼的哈希和驗證。
"""

import secrets
import string
from typing import Optional

from passlib.context import CryptContext
from loguru import logger


class PasswordHandler:
    """
    密碼處理器

    使用 bcrypt 進行密碼哈希和驗證。
    """

    def __init__(
        self,
        schemes: list = None,
        deprecated: str = "auto",
    ):
        """
        初始化密碼處理器

        Args:
            schemes: 哈希方案列表
            deprecated: 過時方案處理方式
        """
        self.context = CryptContext(
            schemes=schemes or ["bcrypt"],
            deprecated=deprecated,
        )
        logger.debug("密碼處理器初始化完成")

    def hash_password(self, password: str) -> str:
        """
        哈希密碼

        Args:
            password: 明文密碼

        Returns:
            哈希後的密碼
        """
        return self.context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        驗證密碼

        Args:
            plain_password: 明文密碼
            hashed_password: 哈希密碼

        Returns:
            密碼是否匹配
        """
        try:
            return self.context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"密碼驗證失敗: {e}")
            return False

    def needs_rehash(self, hashed_password: str) -> bool:
        """
        檢查密碼是否需要重新哈希

        Args:
            hashed_password: 哈希密碼

        Returns:
            是否需要重新哈希
        """
        return self.context.needs_update(hashed_password)

    @staticmethod
    def generate_password(
        length: int = 16,
        include_uppercase: bool = True,
        include_lowercase: bool = True,
        include_digits: bool = True,
        include_special: bool = True,
    ) -> str:
        """
        生成隨機密碼

        Args:
            length: 密碼長度
            include_uppercase: 包含大寫字母
            include_lowercase: 包含小寫字母
            include_digits: 包含數字
            include_special: 包含特殊字符

        Returns:
            隨機密碼
        """
        characters = ""

        if include_uppercase:
            characters += string.ascii_uppercase
        if include_lowercase:
            characters += string.ascii_lowercase
        if include_digits:
            characters += string.digits
        if include_special:
            characters += "!@#$%^&*()_+-=[]{}|;:,.<>?"

        if not characters:
            characters = string.ascii_letters + string.digits

        # 確保密碼包含所有要求的字符類型
        password = []

        if include_uppercase:
            password.append(secrets.choice(string.ascii_uppercase))
        if include_lowercase:
            password.append(secrets.choice(string.ascii_lowercase))
        if include_digits:
            password.append(secrets.choice(string.digits))
        if include_special:
            password.append(secrets.choice("!@#$%^&*()_+-=[]{}|;:,.<>?"))

        # 填充剩餘長度
        remaining_length = length - len(password)
        password.extend(secrets.choice(characters) for _ in range(remaining_length))

        # 打亂順序
        secrets.SystemRandom().shuffle(password)

        return "".join(password)

    @staticmethod
    def validate_password_strength(
        password: str,
        min_length: int = 8,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_special: bool = False,
    ) -> tuple[bool, list[str]]:
        """
        驗證密碼強度

        Args:
            password: 密碼
            min_length: 最小長度
            require_uppercase: 要求大寫字母
            require_lowercase: 要求小寫字母
            require_digit: 要求數字
            require_special: 要求特殊字符

        Returns:
            (是否有效, 錯誤列表)
        """
        errors = []

        if len(password) < min_length:
            errors.append(f"密碼長度必須至少 {min_length} 個字符")

        if require_uppercase and not any(c.isupper() for c in password):
            errors.append("密碼必須包含至少一個大寫字母")

        if require_lowercase and not any(c.islower() for c in password):
            errors.append("密碼必須包含至少一個小寫字母")

        if require_digit and not any(c.isdigit() for c in password):
            errors.append("密碼必須包含至少一個數字")

        if require_special and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("密碼必須包含至少一個特殊字符")

        return len(errors) == 0, errors


# ============================================================================
# 全局實例和便捷函數
# ============================================================================

_password_handler: Optional[PasswordHandler] = None


def get_password_handler() -> PasswordHandler:
    """獲取全局密碼處理器"""
    global _password_handler
    if _password_handler is None:
        _password_handler = PasswordHandler()
    return _password_handler


def hash_password(password: str) -> str:
    """哈希密碼（便捷函數）"""
    return get_password_handler().hash_password(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """驗證密碼（便捷函數）"""
    return get_password_handler().verify_password(plain_password, hashed_password)
