"""
資料庫連接池管理器

提供連接池監控、動態調整和健康檢查功能。
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from loguru import logger
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool


@dataclass
class PoolStats:
    """連接池統計"""
    total_connections_created: int = 0
    total_connections_closed: int = 0
    connection_errors: int = 0
    checkout_count: int = 0
    checkin_count: int = 0
    overflow_count: int = 0
    invalidation_count: int = 0
    checkedout_peak: int = 0
    created_at: float = field(default_factory=time.time)

    # 延遲統計
    checkout_times: List[float] = field(default_factory=list)
    max_checkout_time: float = 0.0
    avg_checkout_time: float = 0.0


class DatabasePoolManager:
    """
    資料庫連接池管理器

    功能：
    - 連接池事件監控
    - 連接統計和健康檢查
    - 動態調整連接池大小
    - 連接泄漏檢測
    """

    def __init__(
        self,
        engine: Engine,
        leak_detection_threshold: float = 60.0,
        max_checkout_time_samples: int = 100,
    ):
        """
        初始化連接池管理器

        Args:
            engine: SQLAlchemy 引擎
            leak_detection_threshold: 連接泄漏檢測閾值（秒）
            max_checkout_time_samples: 保留的簽出時間樣本數
        """
        self.engine = engine
        self.pool = engine.pool
        self.leak_detection_threshold = leak_detection_threshold
        self.max_checkout_time_samples = max_checkout_time_samples

        # 統計
        self._stats = PoolStats()

        # 連接追蹤（用於泄漏檢測）
        self._active_connections: Dict[int, float] = {}  # connection_id -> checkout_time

        # 回調
        self._on_warning_callbacks: List[Callable] = []

        # 註冊事件監聽
        self._register_events()

        logger.info(
            f"資料庫連接池管理器初始化完成 "
            f"(池大小: {self.get_pool_size()}, "
            f"最大溢出: {self.get_max_overflow()})"
        )

    # ========================================================================
    # 事件監聽
    # ========================================================================

    def _register_events(self):
        """註冊連接池事件監聽"""

        @event.listens_for(self.pool, "connect")
        def on_connect(dbapi_conn, connection_record):
            """新連接創建"""
            self._stats.total_connections_created += 1
            logger.debug(
                f"新建資料庫連接 (總數: {self._stats.total_connections_created})"
            )

        @event.listens_for(self.pool, "checkout")
        def on_checkout(dbapi_conn, connection_record, connection_proxy):
            """連接簽出"""
            self._stats.checkout_count += 1
            conn_id = id(dbapi_conn)
            self._active_connections[conn_id] = time.time()

            # 更新峰值
            checkedout = self.get_checkedout_count()
            if checkedout > self._stats.checkedout_peak:
                self._stats.checkedout_peak = checkedout

            # 檢查使用率
            pool_size = self.get_pool_size()
            if pool_size > 0:
                usage_ratio = checkedout / pool_size
                if usage_ratio > 0.8:
                    self._emit_warning(
                        f"連接使用率過高: {checkedout}/{pool_size} "
                        f"({usage_ratio:.1%})"
                    )

        @event.listens_for(self.pool, "checkin")
        def on_checkin(dbapi_conn, connection_record):
            """連接歸還"""
            self._stats.checkin_count += 1
            conn_id = id(dbapi_conn)

            # 計算使用時間
            if conn_id in self._active_connections:
                checkout_time = time.time() - self._active_connections[conn_id]
                self._record_checkout_time(checkout_time)
                del self._active_connections[conn_id]

        @event.listens_for(self.pool, "close")
        def on_close(dbapi_conn, connection_record):
            """連接關閉"""
            self._stats.total_connections_closed += 1
            logger.debug("資料庫連接已關閉")

        @event.listens_for(self.pool, "invalidate")
        def on_invalidate(dbapi_conn, connection_record, exception):
            """連接失效"""
            self._stats.invalidation_count += 1
            self._stats.connection_errors += 1
            logger.warning(f"資料庫連接失效: {exception}")

        @event.listens_for(self.pool, "reset")
        def on_reset(dbapi_conn, connection_record):
            """連接重置"""
            logger.debug("資料庫連接已重置")

        # 溢出監控（QueuePool 特有）
        if isinstance(self.pool, QueuePool):

            @event.listens_for(self.pool, "checkout")
            def on_overflow(dbapi_conn, connection_record, connection_proxy):
                if self.get_checkedout_count() > self.get_pool_size():
                    self._stats.overflow_count += 1

    def _record_checkout_time(self, checkout_time: float):
        """記錄簽出時間"""
        self._stats.checkout_times.append(checkout_time)

        # 限制樣本數量
        if len(self._stats.checkout_times) > self.max_checkout_time_samples:
            self._stats.checkout_times.pop(0)

        # 更新最大值
        if checkout_time > self._stats.max_checkout_time:
            self._stats.max_checkout_time = checkout_time

        # 更新平均值
        self._stats.avg_checkout_time = sum(self._stats.checkout_times) / len(
            self._stats.checkout_times
        )

    def _emit_warning(self, message: str):
        """發出警告"""
        logger.warning(f"[連接池警告] {message}")

        for callback in self._on_warning_callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"警告回調執行失敗: {e}")

    # ========================================================================
    # 連接池信息
    # ========================================================================

    def get_pool_size(self) -> int:
        """獲取連接池大小"""
        if isinstance(self.pool, QueuePool):
            return self.pool.size()
        return 0

    def get_max_overflow(self) -> int:
        """獲取最大溢出數"""
        if isinstance(self.pool, QueuePool):
            return self.pool._max_overflow
        return 0

    def get_checkedout_count(self) -> int:
        """獲取已簽出的連接數"""
        if isinstance(self.pool, QueuePool):
            return self.pool.checkedout()
        return len(self._active_connections)

    def get_available_count(self) -> int:
        """獲取可用連接數"""
        return max(0, self.get_pool_size() - self.get_checkedout_count())

    # ========================================================================
    # 統計和監控
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """獲取連接池統計信息"""
        uptime = time.time() - self._stats.created_at

        return {
            "pool_size": self.get_pool_size(),
            "max_overflow": self.get_max_overflow(),
            "checkedout": self.get_checkedout_count(),
            "available": self.get_available_count(),
            "checkedout_peak": self._stats.checkedout_peak,
            "total_connections_created": self._stats.total_connections_created,
            "total_connections_closed": self._stats.total_connections_closed,
            "connection_errors": self._stats.connection_errors,
            "checkout_count": self._stats.checkout_count,
            "checkin_count": self._stats.checkin_count,
            "overflow_count": self._stats.overflow_count,
            "invalidation_count": self._stats.invalidation_count,
            "max_checkout_time_seconds": self._stats.max_checkout_time,
            "avg_checkout_time_seconds": self._stats.avg_checkout_time,
            "uptime_seconds": uptime,
            "active_connections": len(self._active_connections),
        }

    # ========================================================================
    # 健康檢查
    # ========================================================================

    async def health_check(self) -> Dict[str, Any]:
        """
        執行連接池健康檢查

        Returns:
            健康狀態字典
        """
        result = {
            "healthy": True,
            "checks": {},
            "warnings": [],
        }

        # 檢查 1: 連接測試
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            result["checks"]["connection_test"] = "passed"
        except Exception as e:
            result["healthy"] = False
            result["checks"]["connection_test"] = f"failed: {e}"

        # 檢查 2: 使用率
        checkedout = self.get_checkedout_count()
        pool_size = self.get_pool_size()

        if pool_size > 0:
            usage_ratio = checkedout / pool_size
            result["checks"]["usage_ratio"] = f"{usage_ratio:.1%}"

            if usage_ratio > 0.9:
                result["warnings"].append(f"連接使用率過高: {usage_ratio:.1%}")
            elif usage_ratio > 0.8:
                result["warnings"].append(f"連接使用率較高: {usage_ratio:.1%}")

        # 檢查 3: 錯誤率
        if self._stats.checkout_count > 0:
            error_rate = self._stats.connection_errors / self._stats.checkout_count
            result["checks"]["error_rate"] = f"{error_rate:.2%}"

            if error_rate > 0.05:
                result["warnings"].append(f"連接錯誤率過高: {error_rate:.2%}")

        # 檢查 4: 連接泄漏
        leaked_connections = self._detect_connection_leaks()
        if leaked_connections:
            result["warnings"].append(
                f"檢測到 {len(leaked_connections)} 個可能泄漏的連接"
            )

        result["healthy"] = result["healthy"] and len(result["warnings"]) == 0

        return result

    def _detect_connection_leaks(self) -> List[Dict[str, Any]]:
        """檢測連接泄漏"""
        current_time = time.time()
        leaked = []

        for conn_id, checkout_time in self._active_connections.items():
            duration = current_time - checkout_time
            if duration > self.leak_detection_threshold:
                leaked.append(
                    {
                        "connection_id": conn_id,
                        "checkout_duration_seconds": duration,
                        "threshold_seconds": self.leak_detection_threshold,
                    }
                )

        return leaked

    # ========================================================================
    # 動態調整
    # ========================================================================

    def resize_pool(
        self,
        new_pool_size: Optional[int] = None,
        new_max_overflow: Optional[int] = None,
    ) -> bool:
        """
        動態調整連接池大小

        注意：這在運行時可能不完全生效，建議在低負載時執行。

        Args:
            new_pool_size: 新的池大小
            new_max_overflow: 新的最大溢出

        Returns:
            是否成功
        """
        if not isinstance(self.pool, QueuePool):
            logger.warning("當前連接池類型不支持動態調整")
            return False

        try:
            old_size = self.get_pool_size()
            old_overflow = self.get_max_overflow()

            if new_pool_size is not None:
                # 注意：這是一個簡化的實現
                # 實際上 SQLAlchemy 的 QueuePool 不直接支持運行時調整
                logger.info(f"連接池大小調整請求: {old_size} -> {new_pool_size}")

            if new_max_overflow is not None:
                self.pool._max_overflow = new_max_overflow
                logger.info(f"最大溢出調整: {old_overflow} -> {new_max_overflow}")

            return True

        except Exception as e:
            logger.error(f"調整連接池大小失敗: {e}")
            return False

    # ========================================================================
    # 清理和關閉
    # ========================================================================

    def on_warning(self, callback: Callable):
        """註冊警告回調"""
        self._on_warning_callbacks.append(callback)
        return callback

    async def cleanup(self):
        """清理資源"""
        logger.info("關閉資料庫連接池...")

        try:
            # 等待活躍連接歸還
            wait_start = time.time()
            while self._active_connections and (time.time() - wait_start) < 10:
                logger.info(f"等待 {len(self._active_connections)} 個活躍連接歸還...")
                await asyncio.sleep(1)

            # 關閉連接池
            self.engine.dispose()
            logger.info("資料庫連接池已關閉")

        except Exception as e:
            logger.error(f"關閉連接池失敗: {e}")


# 需要導入 asyncio
import asyncio
