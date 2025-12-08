"""
重試機制

實現帶指數退避的重試功能。
"""

import asyncio
import random
import time
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, List, Optional, Type, Tuple

from loguru import logger


@dataclass
class RetryConfig:
    """重試配置"""
    # 最大重試次數
    max_retries: int = 3

    # 初始延遲（秒）
    initial_delay: float = 1.0

    # 最大延遲（秒）
    max_delay: float = 60.0

    # 指數退避因子
    backoff_factor: float = 2.0

    # 是否添加抖動
    jitter: bool = True

    # 抖動範圍（0-1）
    jitter_factor: float = 0.1

    # 重試的異常類型
    retry_exceptions: List[Type[Exception]] = field(
        default_factory=lambda: [Exception]
    )

    # 不重試的異常類型
    no_retry_exceptions: List[Type[Exception]] = field(default_factory=list)

    # 重試條件函數
    retry_if: Optional[Callable[[Exception], bool]] = None


def exponential_backoff(
    attempt: int,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    jitter_factor: float = 0.1,
) -> float:
    """
    計算指數退避延遲

    Args:
        attempt: 當前嘗試次數（從 0 開始）
        initial_delay: 初始延遲
        max_delay: 最大延遲
        backoff_factor: 退避因子
        jitter: 是否添加抖動
        jitter_factor: 抖動因子

    Returns:
        延遲時間（秒）
    """
    delay = initial_delay * (backoff_factor ** attempt)
    delay = min(delay, max_delay)

    if jitter:
        jitter_range = delay * jitter_factor
        delay = delay + random.uniform(-jitter_range, jitter_range)

    return max(0, delay)


def should_retry(
    exception: Exception,
    config: RetryConfig,
) -> bool:
    """
    判斷是否應該重試

    Args:
        exception: 異常實例
        config: 重試配置

    Returns:
        是否應該重試
    """
    # 檢查不重試列表
    for exc_type in config.no_retry_exceptions:
        if isinstance(exception, exc_type):
            return False

    # 檢查自定義條件
    if config.retry_if is not None:
        return config.retry_if(exception)

    # 檢查重試列表
    for exc_type in config.retry_exceptions:
        if isinstance(exception, exc_type):
            return True

    return False


def retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retry_exceptions: List[Type[Exception]] = None,
    no_retry_exceptions: List[Type[Exception]] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
):
    """
    重試裝飾器

    Args:
        max_retries: 最大重試次數
        initial_delay: 初始延遲
        max_delay: 最大延遲
        backoff_factor: 退避因子
        jitter: 是否添加抖動
        retry_exceptions: 重試的異常類型
        no_retry_exceptions: 不重試的異常類型
        on_retry: 重試回調函數

    Returns:
        裝飾器
    """
    config = RetryConfig(
        max_retries=max_retries,
        initial_delay=initial_delay,
        max_delay=max_delay,
        backoff_factor=backoff_factor,
        jitter=jitter,
        retry_exceptions=retry_exceptions or [Exception],
        no_retry_exceptions=no_retry_exceptions or [],
    )

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt >= max_retries:
                        logger.error(
                            f"函數 '{func.__name__}' 重試 {max_retries} 次後失敗: {e}"
                        )
                        raise

                    if not should_retry(e, config):
                        logger.debug(f"異常 {type(e).__name__} 不在重試列表中")
                        raise

                    delay = exponential_backoff(
                        attempt=attempt,
                        initial_delay=config.initial_delay,
                        max_delay=config.max_delay,
                        backoff_factor=config.backoff_factor,
                        jitter=config.jitter,
                    )

                    logger.warning(
                        f"函數 '{func.__name__}' 第 {attempt + 1} 次失敗，"
                        f"{delay:.2f} 秒後重試: {e}"
                    )

                    if on_retry:
                        on_retry(attempt, e, delay)

                    time.sleep(delay)

            raise last_exception

        return wrapper

    return decorator


def retry_async(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retry_exceptions: List[Type[Exception]] = None,
    no_retry_exceptions: List[Type[Exception]] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
):
    """
    異步重試裝飾器

    Args:
        max_retries: 最大重試次數
        initial_delay: 初始延遲
        max_delay: 最大延遲
        backoff_factor: 退避因子
        jitter: 是否添加抖動
        retry_exceptions: 重試的異常類型
        no_retry_exceptions: 不重試的異常類型
        on_retry: 重試回調函數

    Returns:
        裝飾器
    """
    config = RetryConfig(
        max_retries=max_retries,
        initial_delay=initial_delay,
        max_delay=max_delay,
        backoff_factor=backoff_factor,
        jitter=jitter,
        retry_exceptions=retry_exceptions or [Exception],
        no_retry_exceptions=no_retry_exceptions or [],
    )

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt >= max_retries:
                        logger.error(
                            f"異步函數 '{func.__name__}' 重試 {max_retries} 次後失敗: {e}"
                        )
                        raise

                    if not should_retry(e, config):
                        logger.debug(f"異常 {type(e).__name__} 不在重試列表中")
                        raise

                    delay = exponential_backoff(
                        attempt=attempt,
                        initial_delay=config.initial_delay,
                        max_delay=config.max_delay,
                        backoff_factor=config.backoff_factor,
                        jitter=config.jitter,
                    )

                    logger.warning(
                        f"異步函數 '{func.__name__}' 第 {attempt + 1} 次失敗，"
                        f"{delay:.2f} 秒後重試: {e}"
                    )

                    if on_retry:
                        on_retry(attempt, e, delay)

                    await asyncio.sleep(delay)

            raise last_exception

        return wrapper

    return decorator


class RetryContext:
    """
    重試上下文管理器

    使用方式：
    async with RetryContext(max_retries=3) as ctx:
        result = await some_operation()
    """

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
    ):
        self.config = RetryConfig(
            max_retries=max_retries,
            initial_delay=initial_delay,
            max_delay=max_delay,
            backoff_factor=backoff_factor,
            jitter=jitter,
        )
        self.attempt = 0
        self.last_exception: Optional[Exception] = None

    @property
    def should_retry(self) -> bool:
        """是否應該重試"""
        return self.attempt < self.config.max_retries

    def get_delay(self) -> float:
        """獲取當前延遲"""
        return exponential_backoff(
            attempt=self.attempt,
            initial_delay=self.config.initial_delay,
            max_delay=self.config.max_delay,
            backoff_factor=self.config.backoff_factor,
            jitter=self.config.jitter,
        )

    def record_success(self):
        """記錄成功"""
        self.attempt = 0
        self.last_exception = None

    def record_failure(self, exception: Exception):
        """記錄失敗"""
        self.attempt += 1
        self.last_exception = exception

    async def wait(self):
        """等待重試延遲"""
        delay = self.get_delay()
        await asyncio.sleep(delay)
