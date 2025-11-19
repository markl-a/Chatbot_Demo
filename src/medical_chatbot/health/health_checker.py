"""
健康檢查器

檢查各個組件的健康狀態（資料庫、Redis、模型等）。
"""
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime
import time
import asyncio

from loguru import logger


class HealthStatus(Enum):
    """健康狀態"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"  # 降級
    UNHEALTHY = "unhealthy"


class ComponentStatus:
    """組件狀態"""

    def __init__(
        self,
        name: str,
        status: HealthStatus,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
        response_time: Optional[float] = None,
    ):
        self.name = name
        self.status = status
        self.message = message
        self.details = details or {}
        self.response_time = response_time
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "response_time": self.response_time,
            "timestamp": self.timestamp.isoformat(),
        }

    @property
    def is_healthy(self) -> bool:
        """是否健康"""
        return self.status == HealthStatus.HEALTHY


class HealthChecker:
    """健康檢查器"""

    def __init__(
        self,
        database_manager=None,
        redis_cache=None,
        model_generator=None,
    ):
        """
        初始化健康檢查器

        Args:
            database_manager: 資料庫管理器
            redis_cache: Redis 快取
            model_generator: 模型生成器
        """
        self.database_manager = database_manager
        self.redis_cache = redis_cache
        self.model_generator = model_generator

        self.checks = {}
        self._register_default_checks()

        logger.info("健康檢查器初始化完成")

    # ========================================================================
    # 組件檢查
    # ========================================================================

    def check_database(self) -> ComponentStatus:
        """檢查資料庫連接"""
        if not self.database_manager:
            return ComponentStatus(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message="資料庫管理器未配置",
            )

        try:
            start_time = time.time()

            # 執行簡單查詢
            with self.database_manager.get_db() as db:
                # 測試連接
                db.execute("SELECT 1")

            response_time = time.time() - start_time

            return ComponentStatus(
                name="database",
                status=HealthStatus.HEALTHY,
                message="資料庫連接正常",
                response_time=response_time,
                details={
                    "url": str(self.database_manager.engine.url).split("@")[-1],  # 隱藏憑證
                    "pool_size": self.database_manager.engine.pool.size(),
                    "checked_out": self.database_manager.engine.pool.checkedout(),
                },
            )

        except Exception as e:
            logger.error(f"資料庫健康檢查失敗: {e}")

            return ComponentStatus(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"資料庫連接失敗: {str(e)}",
            )

    def check_redis(self) -> ComponentStatus:
        """檢查 Redis 連接"""
        if not self.redis_cache:
            return ComponentStatus(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message="Redis 快取未配置",
            )

        try:
            start_time = time.time()

            # 測試 ping
            pong = self.redis_cache.ping()

            response_time = time.time() - start_time

            if not pong:
                return ComponentStatus(
                    name="redis",
                    status=HealthStatus.UNHEALTHY,
                    message="Redis ping 失敗",
                )

            # 獲取資訊
            info = self.redis_cache.info()

            return ComponentStatus(
                name="redis",
                status=HealthStatus.HEALTHY,
                message="Redis 連接正常",
                response_time=response_time,
                details={
                    "version": info.get("redis_version", "unknown"),
                    "used_memory": info.get("used_memory_human", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                    "uptime_days": info.get("uptime_in_days", 0),
                },
            )

        except Exception as e:
            logger.error(f"Redis 健康檢查失敗: {e}")

            return ComponentStatus(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis 連接失敗: {str(e)}",
            )

    def check_model(self) -> ComponentStatus:
        """檢查模型狀態"""
        if not self.model_generator:
            return ComponentStatus(
                name="model",
                status=HealthStatus.UNHEALTHY,
                message="模型生成器未配置",
            )

        try:
            start_time = time.time()

            # 測試簡單生成
            test_prompt = "測試"
            response = self.model_generator.generate(test_prompt, max_length=10)

            response_time = time.time() - start_time

            if not response:
                return ComponentStatus(
                    name="model",
                    status=HealthStatus.DEGRADED,
                    message="模型生成為空",
                    response_time=response_time,
                )

            return ComponentStatus(
                name="model",
                status=HealthStatus.HEALTHY,
                message="模型運行正常",
                response_time=response_time,
                details={
                    "model_name": getattr(self.model_generator, "model_name", "unknown"),
                    "device": getattr(self.model_generator, "device", "unknown"),
                },
            )

        except Exception as e:
            logger.error(f"模型健康檢查失敗: {e}")

            return ComponentStatus(
                name="model",
                status=HealthStatus.UNHEALTHY,
                message=f"模型檢查失敗: {str(e)}",
            )

    def check_disk_space(self) -> ComponentStatus:
        """檢查磁碟空間"""
        try:
            import shutil

            start_time = time.time()

            # 檢查當前目錄的磁碟空間
            usage = shutil.disk_usage(".")

            response_time = time.time() - start_time

            # 計算使用率
            used_percent = (usage.used / usage.total) * 100

            # 判斷狀態
            if used_percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f"磁碟空間嚴重不足: {used_percent:.1f}%"
            elif used_percent > 80:
                status = HealthStatus.DEGRADED
                message = f"磁碟空間偏低: {used_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"磁碟空間正常: {used_percent:.1f}%"

            return ComponentStatus(
                name="disk",
                status=status,
                message=message,
                response_time=response_time,
                details={
                    "total": f"{usage.total / (1024**3):.2f} GB",
                    "used": f"{usage.used / (1024**3):.2f} GB",
                    "free": f"{usage.free / (1024**3):.2f} GB",
                    "percent": f"{used_percent:.1f}%",
                },
            )

        except Exception as e:
            logger.error(f"磁碟空間檢查失敗: {e}")

            return ComponentStatus(
                name="disk",
                status=HealthStatus.UNHEALTHY,
                message=f"磁碟空間檢查失敗: {str(e)}",
            )

    def check_memory(self) -> ComponentStatus:
        """檢查記憶體使用"""
        try:
            import psutil

            start_time = time.time()

            # 獲取記憶體資訊
            memory = psutil.virtual_memory()

            response_time = time.time() - start_time

            # 判斷狀態
            if memory.percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f"記憶體使用過高: {memory.percent:.1f}%"
            elif memory.percent > 80:
                status = HealthStatus.DEGRADED
                message = f"記憶體使用偏高: {memory.percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"記憶體使用正常: {memory.percent:.1f}%"

            return ComponentStatus(
                name="memory",
                status=status,
                message=message,
                response_time=response_time,
                details={
                    "total": f"{memory.total / (1024**3):.2f} GB",
                    "available": f"{memory.available / (1024**3):.2f} GB",
                    "used": f"{memory.used / (1024**3):.2f} GB",
                    "percent": f"{memory.percent:.1f}%",
                },
            )

        except ImportError:
            return ComponentStatus(
                name="memory",
                status=HealthStatus.DEGRADED,
                message="psutil 未安裝，無法檢查記憶體",
            )

        except Exception as e:
            logger.error(f"記憶體檢查失敗: {e}")

            return ComponentStatus(
                name="memory",
                status=HealthStatus.UNHEALTHY,
                message=f"記憶體檢查失敗: {str(e)}",
            )

    # ========================================================================
    # 自訂檢查
    # ========================================================================

    def _register_default_checks(self):
        """註冊預設檢查"""
        self.checks = {
            "database": self.check_database,
            "redis": self.check_redis,
            "model": self.check_model,
            "disk": self.check_disk_space,
            "memory": self.check_memory,
        }

    def register_check(self, name: str, check_func):
        """
        註冊自訂健康檢查

        Args:
            name: 檢查名稱
            check_func: 檢查函數（返回 ComponentStatus）
        """
        self.checks[name] = check_func
        logger.info(f"註冊健康檢查: {name}")

    def unregister_check(self, name: str):
        """
        取消註冊健康檢查

        Args:
            name: 檢查名稱
        """
        if name in self.checks:
            del self.checks[name]
            logger.info(f"取消註冊健康檢查: {name}")

    # ========================================================================
    # 執行檢查
    # ========================================================================

    def check_component(self, component_name: str) -> ComponentStatus:
        """
        檢查單個組件

        Args:
            component_name: 組件名稱

        Returns:
            組件狀態
        """
        if component_name not in self.checks:
            return ComponentStatus(
                name=component_name,
                status=HealthStatus.UNHEALTHY,
                message=f"未知的組件: {component_name}",
            )

        try:
            return self.checks[component_name]()

        except Exception as e:
            logger.error(f"檢查 {component_name} 時發生錯誤: {e}")

            return ComponentStatus(
                name=component_name,
                status=HealthStatus.UNHEALTHY,
                message=f"檢查失敗: {str(e)}",
            )

    def check_all(self, include: Optional[List[str]] = None) -> Dict[str, ComponentStatus]:
        """
        檢查所有組件

        Args:
            include: 要包含的組件列表（None 表示全部）

        Returns:
            組件狀態字典
        """
        components_to_check = include or list(self.checks.keys())

        results = {}

        for component in components_to_check:
            if component in self.checks:
                results[component] = self.check_component(component)

        return results

    async def check_all_async(self, include: Optional[List[str]] = None) -> Dict[str, ComponentStatus]:
        """
        異步檢查所有組件

        Args:
            include: 要包含的組件列表

        Returns:
            組件狀態字典
        """
        components_to_check = include or list(self.checks.keys())

        # 使用 asyncio 並行檢查
        tasks = []

        for component in components_to_check:
            if component in self.checks:
                task = asyncio.create_task(
                    asyncio.to_thread(self.check_component, component)
                )
                tasks.append((component, task))

        results = {}

        for component, task in tasks:
            try:
                results[component] = await task
            except Exception as e:
                logger.error(f"異步檢查 {component} 失敗: {e}")
                results[component] = ComponentStatus(
                    name=component,
                    status=HealthStatus.UNHEALTHY,
                    message=f"異步檢查失敗: {str(e)}",
                )

        return results

    # ========================================================================
    # 報告生成
    # ========================================================================

    def get_health_report(self, include: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        獲取健康報告

        Args:
            include: 要包含的組件列表

        Returns:
            健康報告
        """
        start_time = time.time()

        # 檢查所有組件
        components = self.check_all(include=include)

        # 計算總體狀態
        all_healthy = all(c.is_healthy for c in components.values())
        any_unhealthy = any(c.status == HealthStatus.UNHEALTHY for c in components.values())

        if all_healthy:
            overall_status = HealthStatus.HEALTHY
        elif any_unhealthy:
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.DEGRADED

        total_time = time.time() - start_time

        return {
            "status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "checks": {
                name: status.to_dict()
                for name, status in components.items()
            },
            "summary": {
                "total_checks": len(components),
                "healthy": sum(1 for c in components.values() if c.status == HealthStatus.HEALTHY),
                "degraded": sum(1 for c in components.values() if c.status == HealthStatus.DEGRADED),
                "unhealthy": sum(1 for c in components.values() if c.status == HealthStatus.UNHEALTHY),
            },
            "response_time": total_time,
        }

    async def get_health_report_async(self, include: Optional[List[str]] = None) -> Dict[str, Any]:
        """異步獲取健康報告"""
        start_time = time.time()

        components = await self.check_all_async(include=include)

        all_healthy = all(c.is_healthy for c in components.values())
        any_unhealthy = any(c.status == HealthStatus.UNHEALTHY for c in components.values())

        if all_healthy:
            overall_status = HealthStatus.HEALTHY
        elif any_unhealthy:
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.DEGRADED

        total_time = time.time() - start_time

        return {
            "status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "checks": {
                name: status.to_dict()
                for name, status in components.items()
            },
            "summary": {
                "total_checks": len(components),
                "healthy": sum(1 for c in components.values() if c.status == HealthStatus.HEALTHY),
                "degraded": sum(1 for c in components.values() if c.status == HealthStatus.DEGRADED),
                "unhealthy": sum(1 for c in components.values() if c.status == HealthStatus.UNHEALTHY),
            },
            "response_time": total_time,
        }
