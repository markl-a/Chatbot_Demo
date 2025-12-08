"""
超時處理

實現超時控制功能。
"""

import asyncio
import signal
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Optional

from loguru import logger


class TimeoutError(Exception):
    """超時異常"""

    def __init__(self, timeout: float, operation: str = "操作"):
        self.timeout = timeout
        self.operation = operation
        super().__init__(f"{operation}超時 ({timeout} 秒)")


@dataclass
class TimeoutConfig:
    """超時配置"""
    # 超時時間（秒）
    timeout: float = 30.0

    # 操作名稱（用於日誌和錯誤消息）
    operation_name: str = "操作"

    # 是否在超時時取消操作
    cancel_on_timeout: bool = True


def timeout(
    seconds: float,
    operation_name: str = "操作",
):
    """
    超時裝飾器（同步函數）

    使用線程池實現超時控制。

    Args:
        seconds: 超時時間
        operation_name: 操作名稱

    Returns:
        裝飾器
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, *args, **kwargs)
                try:
                    return future.result(timeout=seconds)
                except FuturesTimeoutError:
                    logger.warning(
                        f"函數 '{func.__name__}' 超時 ({seconds} 秒)"
                    )
                    raise TimeoutError(seconds, operation_name)

        return wrapper

    return decorator


def timeout_async(
    seconds: float,
    operation_name: str = "操作",
):
    """
    超時裝飾器（異步函數）

    使用 asyncio.wait_for 實現超時控制。

    Args:
        seconds: 超時時間
        operation_name: 操作名稱

    Returns:
        裝飾器
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    f"異步函數 '{func.__name__}' 超時 ({seconds} 秒)"
                )
                raise TimeoutError(seconds, operation_name)

        return wrapper

    return decorator


class TimeoutContext:
    """
    超時上下文管理器

    使用方式：
    async with TimeoutContext(30.0) as ctx:
        await some_operation()
    """

    def __init__(
        self,
        timeout: float,
        operation_name: str = "操作",
    ):
        self.timeout = timeout
        self.operation_name = operation_name
        self._task: Optional[asyncio.Task] = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is asyncio.TimeoutError:
            raise TimeoutError(self.timeout, self.operation_name)
        return False

    async def run(self, coro):
        """
        運行協程並應用超時

        Args:
            coro: 協程

        Returns:
            協程結果
        """
        try:
            return await asyncio.wait_for(coro, timeout=self.timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(self.timeout, self.operation_name)


class DeadlineContext:
    """
    截止時間上下文管理器

    設置一個絕對的截止時間，而不是相對超時。

    使用方式：
    deadline = time.time() + 60  # 60秒後截止
    async with DeadlineContext(deadline) as ctx:
        while ctx.remaining > 0:
            await some_operation()
    """

    def __init__(
        self,
        deadline: float,
        operation_name: str = "操作",
    ):
        """
        初始化截止時間上下文

        Args:
            deadline: 截止時間（Unix 時間戳）
            operation_name: 操作名稱
        """
        self.deadline = deadline
        self.operation_name = operation_name

    @property
    def remaining(self) -> float:
        """剩餘時間"""
        import time
        return max(0, self.deadline - time.time())

    @property
    def is_expired(self) -> bool:
        """是否已過期"""
        return self.remaining <= 0

    def check(self):
        """檢查是否超時，如果超時則拋出異常"""
        if self.is_expired:
            raise TimeoutError(0, self.operation_name)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    async def run(self, coro):
        """
        運行協程並應用截止時間

        Args:
            coro: 協程

        Returns:
            協程結果
        """
        remaining = self.remaining
        if remaining <= 0:
            raise TimeoutError(0, self.operation_name)

        try:
            return await asyncio.wait_for(coro, timeout=remaining)
        except asyncio.TimeoutError:
            raise TimeoutError(remaining, self.operation_name)


def with_timeout(
    timeout_seconds: float,
    operation_name: str = "操作",
):
    """
    創建帶超時的協程

    使用方式：
    result = await with_timeout(30.0)(some_async_function())

    Args:
        timeout_seconds: 超時時間
        operation_name: 操作名稱

    Returns:
        包裝函數
    """

    async def wrapper(coro):
        try:
            return await asyncio.wait_for(coro, timeout=timeout_seconds)
        except asyncio.TimeoutError:
            raise TimeoutError(timeout_seconds, operation_name)

    return wrapper
