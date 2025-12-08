"""
斷路器

實現斷路器模式以提高系統彈性。
"""

import asyncio
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Type

from loguru import logger


class CircuitState(Enum):
    """斷路器狀態"""
    CLOSED = "closed"       # 正常狀態，允許請求通過
    OPEN = "open"           # 開啟狀態，拒絕所有請求
    HALF_OPEN = "half_open" # 半開狀態，允許部分請求測試


class CircuitBreakerOpen(Exception):
    """斷路器開啟異常"""

    def __init__(self, name: str, message: str = None):
        self.name = name
        self.message = message or f"斷路器 '{name}' 已開啟，拒絕請求"
        super().__init__(self.message)


@dataclass
class CircuitBreakerConfig:
    """斷路器配置"""
    # 失敗閾值：連續失敗多少次後開啟斷路器
    failure_threshold: int = 5

    # 成功閾值：半開狀態下連續成功多少次後關閉斷路器
    success_threshold: int = 3

    # 超時時間：開啟狀態下等待多久後進入半開狀態（秒）
    timeout: float = 30.0

    # 半開狀態最大並發請求數
    half_open_max_calls: int = 3

    # 排除的異常類型（這些異常不計入失敗）
    excluded_exceptions: List[Type[Exception]] = field(default_factory=list)

    # 監控的異常類型（只有這些異常計入失敗，為空表示所有異常）
    monitored_exceptions: List[Type[Exception]] = field(default_factory=list)

    # 是否啟用
    enabled: bool = True


class CircuitBreaker:
    """
    斷路器

    實現三種狀態：
    - CLOSED: 正常狀態，請求通過，記錄失敗次數
    - OPEN: 開啟狀態，拒絕所有請求
    - HALF_OPEN: 半開狀態，允許部分請求測試服務健康

    使用方式：
    1. 作為上下文管理器
    2. 使用 call/call_async 方法
    3. 使用裝飾器
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ):
        """
        初始化斷路器

        Args:
            name: 斷路器名稱
            config: 斷路器配置
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()

        # 狀態
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0

        # 時間戳
        self._last_failure_time: Optional[float] = None
        self._opened_at: Optional[float] = None

        # 統計
        self._total_calls = 0
        self._total_successes = 0
        self._total_failures = 0
        self._total_rejections = 0

        # 回調
        self.on_state_change: Optional[Callable[[CircuitState, CircuitState], None]] = None
        self.on_success: Optional[Callable[[], None]] = None
        self.on_failure: Optional[Callable[[Exception], None]] = None

        # 線程安全
        self._lock = threading.RLock()

        logger.info(f"斷路器 '{name}' 初始化完成")

    # ========================================================================
    # 狀態屬性
    # ========================================================================

    @property
    def state(self) -> CircuitState:
        """獲取當前狀態"""
        return self._state

    @property
    def is_closed(self) -> bool:
        """是否關閉狀態"""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """是否開啟狀態"""
        return self._state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """是否半開狀態"""
        return self._state == CircuitState.HALF_OPEN

    @property
    def failure_count(self) -> int:
        """當前失敗計數"""
        return self._failure_count

    @property
    def success_count(self) -> int:
        """當前成功計數"""
        return self._success_count

    # ========================================================================
    # 核心方法
    # ========================================================================

    def can_execute(self) -> bool:
        """
        檢查是否可以執行請求

        Returns:
            是否允許執行
        """
        if not self.config.enabled:
            return True

        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            elif self._state == CircuitState.OPEN:
                # 檢查是否超時
                if self._should_try_reset():
                    self._transition_to(CircuitState.HALF_OPEN)
                    return True
                return False

            elif self._state == CircuitState.HALF_OPEN:
                # 限制半開狀態的並發請求
                if self._half_open_calls < self.config.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False

        return False

    def record_success(self):
        """記錄成功"""
        if not self.config.enabled:
            return

        with self._lock:
            self._total_calls += 1
            self._total_successes += 1

            if self._state == CircuitState.CLOSED:
                # 重置失敗計數
                self._failure_count = 0
                self._success_count += 1

            elif self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                self._half_open_calls = max(0, self._half_open_calls - 1)

                # 檢查是否達到成功閾值
                if self._success_count >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)

        # 觸發回調
        if self.on_success:
            try:
                self.on_success()
            except Exception as e:
                logger.error(f"成功回調執行失敗: {e}")

    def record_failure(self, exception: Optional[Exception] = None):
        """
        記錄失敗

        Args:
            exception: 異常實例（可選）
        """
        if not self.config.enabled:
            return

        # 檢查是否應該記錄此異常
        if exception and not self._should_record_exception(exception):
            return

        with self._lock:
            self._total_calls += 1
            self._total_failures += 1
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.CLOSED:
                # 檢查是否達到失敗閾值
                if self._failure_count >= self.config.failure_threshold:
                    self._transition_to(CircuitState.OPEN)

            elif self._state == CircuitState.HALF_OPEN:
                # 半開狀態下失敗，立即重新開啟
                self._half_open_calls = max(0, self._half_open_calls - 1)
                self._transition_to(CircuitState.OPEN)

        # 觸發回調
        if self.on_failure and exception:
            try:
                self.on_failure(exception)
            except Exception as e:
                logger.error(f"失敗回調執行失敗: {e}")

    def reset(self):
        """重置斷路器"""
        with self._lock:
            old_state = self._state
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0
            self._opened_at = None

            if old_state != CircuitState.CLOSED:
                logger.info(f"斷路器 '{self.name}' 已重置")

    # ========================================================================
    # 調用方法
    # ========================================================================

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        通過斷路器調用函數

        Args:
            func: 要調用的函數
            *args: 位置參數
            **kwargs: 關鍵字參數

        Returns:
            函數返回值

        Raises:
            CircuitBreakerOpen: 斷路器開啟時
        """
        if not self.can_execute():
            self._total_rejections += 1
            raise CircuitBreakerOpen(self.name)

        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure(e)
            raise

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        通過斷路器調用異步函數

        Args:
            func: 要調用的異步函數
            *args: 位置參數
            **kwargs: 關鍵字參數

        Returns:
            函數返回值

        Raises:
            CircuitBreakerOpen: 斷路器開啟時
        """
        if not self.can_execute():
            self._total_rejections += 1
            raise CircuitBreakerOpen(self.name)

        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure(e)
            raise

    # ========================================================================
    # 內部方法
    # ========================================================================

    def _transition_to(self, new_state: CircuitState):
        """轉換到新狀態"""
        old_state = self._state
        self._state = new_state

        if new_state == CircuitState.OPEN:
            self._opened_at = time.time()
            self._success_count = 0
            logger.warning(f"斷路器 '{self.name}' 已開啟")

        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
            self._success_count = 0
            logger.info(f"斷路器 '{self.name}' 進入半開狀態")

        elif new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
            self._opened_at = None
            logger.info(f"斷路器 '{self.name}' 已關閉")

        # 觸發狀態變更回調
        if self.on_state_change:
            try:
                self.on_state_change(old_state, new_state)
            except Exception as e:
                logger.error(f"狀態變更回調執行失敗: {e}")

    def _should_try_reset(self) -> bool:
        """檢查是否應該嘗試重置（進入半開狀態）"""
        if self._opened_at is None:
            return True
        return time.time() - self._opened_at >= self.config.timeout

    def _should_record_exception(self, exception: Exception) -> bool:
        """檢查是否應該記錄此異常"""
        # 檢查排除列表
        for exc_type in self.config.excluded_exceptions:
            if isinstance(exception, exc_type):
                return False

        # 檢查監控列表
        if self.config.monitored_exceptions:
            for exc_type in self.config.monitored_exceptions:
                if isinstance(exception, exc_type):
                    return True
            return False

        return True

    # ========================================================================
    # 統計和監控
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """獲取統計信息"""
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "total_calls": self._total_calls,
                "total_successes": self._total_successes,
                "total_failures": self._total_failures,
                "total_rejections": self._total_rejections,
                "opened_at": self._opened_at,
                "last_failure_time": self._last_failure_time,
            }

    # ========================================================================
    # 上下文管理器
    # ========================================================================

    def __enter__(self):
        """進入上下文"""
        if not self.can_execute():
            self._total_rejections += 1
            raise CircuitBreakerOpen(self.name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        if exc_type is None:
            self.record_success()
        elif exc_val is not None:
            self.record_failure(exc_val)
        return False


# ============================================================================
# 全局斷路器管理
# ============================================================================

_circuit_breakers: Dict[str, CircuitBreaker] = {}
_lock = threading.Lock()


def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
) -> CircuitBreaker:
    """
    獲取或創建斷路器

    Args:
        name: 斷路器名稱
        config: 斷路器配置（僅創建時使用）

    Returns:
        CircuitBreaker 實例
    """
    global _circuit_breakers

    with _lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(name, config)
        return _circuit_breakers[name]


def get_all_circuit_breakers() -> Dict[str, CircuitBreaker]:
    """獲取所有斷路器"""
    return _circuit_breakers.copy()


def reset_all_circuit_breakers():
    """重置所有斷路器"""
    for cb in _circuit_breakers.values():
        cb.reset()


# ============================================================================
# 裝飾器
# ============================================================================


def circuit_breaker(
    name: Optional[str] = None,
    failure_threshold: int = 5,
    success_threshold: int = 3,
    timeout: float = 30.0,
    excluded_exceptions: List[Type[Exception]] = None,
    fallback: Optional[Callable] = None,
):
    """
    斷路器裝飾器

    Args:
        name: 斷路器名稱（默認使用函數名）
        failure_threshold: 失敗閾值
        success_threshold: 成功閾值
        timeout: 超時時間
        excluded_exceptions: 排除的異常類型
        fallback: 降級函數

    Returns:
        裝飾器
    """

    def decorator(func: Callable) -> Callable:
        cb_name = name or func.__name__
        config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
            timeout=timeout,
            excluded_exceptions=excluded_exceptions or [],
        )
        cb = get_circuit_breaker(cb_name, config)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return cb.call(func, *args, **kwargs)
            except CircuitBreakerOpen:
                if fallback:
                    return fallback(*args, **kwargs)
                raise

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await cb.call_async(func, *args, **kwargs)
            except CircuitBreakerOpen:
                if fallback:
                    if asyncio.iscoroutinefunction(fallback):
                        return await fallback(*args, **kwargs)
                    return fallback(*args, **kwargs)
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
