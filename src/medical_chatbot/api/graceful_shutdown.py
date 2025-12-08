"""
優雅關閉管理器

實現服務的優雅關閉功能，確保現有請求完成後再關閉。
"""

import asyncio
import signal
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware


class ShutdownState(Enum):
    """關閉狀態"""
    RUNNING = "running"
    DRAINING = "draining"  # 排空中（不接受新請求）
    SHUTTING_DOWN = "shutting_down"  # 關閉中
    STOPPED = "stopped"


@dataclass
class ShutdownStats:
    """關閉統計"""
    start_time: Optional[float] = None
    drain_start_time: Optional[float] = None
    shutdown_start_time: Optional[float] = None
    end_time: Optional[float] = None
    requests_completed: int = 0
    requests_rejected: int = 0
    cleanup_completed: int = 0
    cleanup_failed: int = 0


class GracefulShutdownManager:
    """
    優雅關閉管理器

    功能：
    - 信號處理 (SIGTERM, SIGINT)
    - 請求排空（等待現有請求完成）
    - 超時保護
    - 清理回調執行
    - 關閉統計
    """

    def __init__(
        self,
        shutdown_timeout: float = 30.0,
        drain_timeout: float = 10.0,
        force_shutdown_timeout: float = 60.0,
    ):
        """
        初始化優雅關閉管理器

        Args:
            shutdown_timeout: 關閉超時（秒）
            drain_timeout: 排空超時（秒）
            force_shutdown_timeout: 強制關閉超時（秒）
        """
        self.shutdown_timeout = shutdown_timeout
        self.drain_timeout = drain_timeout
        self.force_shutdown_timeout = force_shutdown_timeout

        # 狀態
        self._state = ShutdownState.RUNNING
        self._shutdown_event: Optional[asyncio.Event] = None
        self._active_requests: int = 0
        self._lock = asyncio.Lock()

        # 回調
        self._cleanup_callbacks: List[tuple[str, Callable]] = []
        self._pre_shutdown_callbacks: List[Callable] = []
        self._post_shutdown_callbacks: List[Callable] = []

        # 統計
        self._stats = ShutdownStats()

        logger.info(
            f"優雅關閉管理器初始化完成 "
            f"(關閉超時: {shutdown_timeout}s, 排空超時: {drain_timeout}s)"
        )

    # ========================================================================
    # 狀態屬性
    # ========================================================================

    @property
    def state(self) -> ShutdownState:
        """獲取當前狀態"""
        return self._state

    @property
    def is_running(self) -> bool:
        """是否運行中"""
        return self._state == ShutdownState.RUNNING

    @property
    def is_shutting_down(self) -> bool:
        """是否正在關閉"""
        return self._state in (ShutdownState.DRAINING, ShutdownState.SHUTTING_DOWN)

    @property
    def active_requests(self) -> int:
        """活躍請求數"""
        return self._active_requests

    # ========================================================================
    # 回調註冊
    # ========================================================================

    def register_cleanup(self, name: str, callback: Callable):
        """
        註冊清理回調

        Args:
            name: 回調名稱
            callback: 清理函數（支援同步和異步）
        """
        self._cleanup_callbacks.append((name, callback))
        logger.debug(f"註冊清理回調: {name}")

    def on_pre_shutdown(self, callback: Callable):
        """註冊關閉前回調"""
        self._pre_shutdown_callbacks.append(callback)
        return callback

    def on_post_shutdown(self, callback: Callable):
        """註冊關閉後回調"""
        self._post_shutdown_callbacks.append(callback)
        return callback

    # ========================================================================
    # 請求追蹤
    # ========================================================================

    async def track_request_start(self) -> bool:
        """
        追蹤請求開始

        Returns:
            是否允許請求（如果正在關閉則返回 False）
        """
        async with self._lock:
            if self._state != ShutdownState.RUNNING:
                self._stats.requests_rejected += 1
                return False

            self._active_requests += 1
            return True

    async def track_request_end(self):
        """追蹤請求結束"""
        async with self._lock:
            self._active_requests = max(0, self._active_requests - 1)
            self._stats.requests_completed += 1

    # ========================================================================
    # 關閉流程
    # ========================================================================

    def trigger_shutdown(self, reason: str = "manual"):
        """
        觸發關閉

        Args:
            reason: 關閉原因
        """
        if self._state != ShutdownState.RUNNING:
            logger.warning(f"已經在關閉中，忽略觸發請求 (原因: {reason})")
            return

        logger.info(f"觸發優雅關閉 (原因: {reason})")
        self._state = ShutdownState.DRAINING
        self._stats.start_time = time.time()

        if self._shutdown_event:
            self._shutdown_event.set()

    async def wait_for_shutdown(self):
        """等待關閉信號"""
        if self._shutdown_event is None:
            self._shutdown_event = asyncio.Event()
        await self._shutdown_event.wait()

    async def graceful_shutdown(self):
        """
        執行優雅關閉

        步驟：
        1. 進入排空狀態（停止接受新請求）
        2. 等待現有請求完成
        3. 執行清理回調
        4. 完成關閉
        """
        logger.info("=" * 60)
        logger.info("開始優雅關閉流程")
        logger.info("=" * 60)

        self._stats.drain_start_time = time.time()

        # 1. 執行關閉前回調
        await self._execute_callbacks(self._pre_shutdown_callbacks, "pre-shutdown")

        # 2. 進入排空狀態
        self._state = ShutdownState.DRAINING
        logger.info(f"進入排空狀態，當前活躍請求: {self._active_requests}")

        # 3. 等待現有請求完成
        await self._drain_requests()

        # 4. 進入關閉狀態
        self._state = ShutdownState.SHUTTING_DOWN
        self._stats.shutdown_start_time = time.time()
        logger.info("開始執行清理任務...")

        # 5. 執行清理回調
        await self._execute_cleanup_callbacks()

        # 6. 執行關閉後回調
        await self._execute_callbacks(self._post_shutdown_callbacks, "post-shutdown")

        # 7. 完成關閉
        self._state = ShutdownState.STOPPED
        self._stats.end_time = time.time()

        logger.info("=" * 60)
        logger.info("優雅關閉完成")
        logger.info(f"統計: {self._format_stats()}")
        logger.info("=" * 60)

    async def _drain_requests(self):
        """排空現有請求"""
        start_time = time.time()

        while self._active_requests > 0:
            elapsed = time.time() - start_time

            if elapsed > self.drain_timeout:
                logger.warning(
                    f"排空超時 ({self.drain_timeout}s)，"
                    f"仍有 {self._active_requests} 個活躍請求"
                )
                break

            remaining = self.drain_timeout - elapsed
            logger.info(
                f"等待 {self._active_requests} 個活躍請求完成 "
                f"(剩餘時間: {remaining:.1f}s)"
            )

            await asyncio.sleep(1)

        if self._active_requests == 0:
            logger.info("所有請求已完成")

    async def _execute_cleanup_callbacks(self):
        """執行清理回調"""
        for name, callback in self._cleanup_callbacks:
            start_time = time.time()

            try:
                logger.info(f"執行清理: {name}")

                if asyncio.iscoroutinefunction(callback):
                    await asyncio.wait_for(
                        callback(),
                        timeout=self.shutdown_timeout / len(self._cleanup_callbacks)
                        if self._cleanup_callbacks
                        else self.shutdown_timeout,
                    )
                else:
                    callback()

                elapsed = time.time() - start_time
                logger.info(f"清理完成: {name} ({elapsed:.2f}s)")
                self._stats.cleanup_completed += 1

            except asyncio.TimeoutError:
                logger.error(f"清理超時: {name}")
                self._stats.cleanup_failed += 1

            except Exception as e:
                logger.error(f"清理失敗: {name} - {e}")
                self._stats.cleanup_failed += 1

    async def _execute_callbacks(self, callbacks: List[Callable], phase: str):
        """執行回調列表"""
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"{phase} 回調執行失敗: {e}")

    def _format_stats(self) -> str:
        """格式化統計信息"""
        total_time = (self._stats.end_time or time.time()) - (
            self._stats.start_time or time.time()
        )

        return (
            f"總耗時: {total_time:.2f}s, "
            f"完成請求: {self._stats.requests_completed}, "
            f"拒絕請求: {self._stats.requests_rejected}, "
            f"清理成功: {self._stats.cleanup_completed}, "
            f"清理失敗: {self._stats.cleanup_failed}"
        )

    # ========================================================================
    # 統計和監控
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """獲取關閉統計"""
        return {
            "state": self._state.value,
            "active_requests": self._active_requests,
            "requests_completed": self._stats.requests_completed,
            "requests_rejected": self._stats.requests_rejected,
            "cleanup_completed": self._stats.cleanup_completed,
            "cleanup_failed": self._stats.cleanup_failed,
            "registered_callbacks": len(self._cleanup_callbacks),
        }


# ============================================================================
# FastAPI 中間件
# ============================================================================


class GracefulShutdownMiddleware(BaseHTTPMiddleware):
    """
    優雅關閉中間件

    - 追蹤活躍請求
    - 在關閉期間拒絕新請求
    """

    def __init__(self, app, shutdown_manager: GracefulShutdownManager):
        super().__init__(app)
        self.shutdown_manager = shutdown_manager

    async def dispatch(self, request: Request, call_next):
        # 嘗試追蹤請求
        if not await self.shutdown_manager.track_request_start():
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Service Unavailable",
                    "message": "服務正在關閉，請稍後重試",
                    "retry_after": 30,
                },
                headers={"Retry-After": "30"},
            )

        try:
            response = await call_next(request)
            return response
        finally:
            await self.shutdown_manager.track_request_end()


# ============================================================================
# FastAPI 整合
# ============================================================================


def setup_graceful_shutdown(
    app: FastAPI,
    shutdown_timeout: float = 30.0,
    drain_timeout: float = 10.0,
) -> GracefulShutdownManager:
    """
    設置優雅關閉功能

    Args:
        app: FastAPI 應用
        shutdown_timeout: 關閉超時
        drain_timeout: 排空超時

    Returns:
        GracefulShutdownManager 實例
    """
    manager = GracefulShutdownManager(
        shutdown_timeout=shutdown_timeout,
        drain_timeout=drain_timeout,
    )

    # 添加中間件
    app.add_middleware(GracefulShutdownMiddleware, shutdown_manager=manager)

    # 設置信號處理
    def signal_handler(signum, frame):
        sig_name = signal.Signals(signum).name
        manager.trigger_shutdown(reason=f"signal:{sig_name}")

    # 註冊信號（僅在主線程）
    try:
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        logger.info("信號處理器已註冊 (SIGTERM, SIGINT)")
    except ValueError:
        logger.warning("無法註冊信號處理器（可能不在主線程）")

    # 添加關閉狀態端點
    @app.get("/shutdown/status")
    async def shutdown_status():
        """獲取關閉狀態"""
        return manager.get_stats()

    logger.info("優雅關閉功能已設置")

    return manager


@asynccontextmanager
async def graceful_lifespan(
    app: FastAPI,
    shutdown_manager: GracefulShutdownManager,
    startup_callback: Optional[Callable] = None,
):
    """
    優雅的生命週期管理器

    使用方式：
    manager = GracefulShutdownManager()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with graceful_lifespan(app, manager, startup):
            yield

    app = FastAPI(lifespan=lifespan)
    """
    try:
        # 啟動回調
        if startup_callback:
            if asyncio.iscoroutinefunction(startup_callback):
                await startup_callback()
            else:
                startup_callback()

        logger.info("應用啟動完成")
        yield

    finally:
        # 優雅關閉
        await shutdown_manager.graceful_shutdown()
