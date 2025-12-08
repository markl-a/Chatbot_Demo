"""
動態配置管理器

提供運行時配置更新、驗證和通知功能。
"""

import asyncio
import hashlib
import json
import os
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Generic, List, Optional, Set, TypeVar, Union

from loguru import logger


T = TypeVar("T")


class ConfigSource(str, Enum):
    """配置來源"""
    FILE = "file"
    ENVIRONMENT = "environment"
    REMOTE = "remote"
    DEFAULT = "default"


@dataclass
class ConfigValue(Generic[T]):
    """配置值包裝"""
    value: T
    source: ConfigSource
    updated_at: datetime = field(default_factory=datetime.utcnow)
    version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "value": self.value,
            "source": self.source.value,
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "metadata": self.metadata,
        }


@dataclass
class ConfigChange:
    """配置變更記錄"""
    key: str
    old_value: Any
    new_value: Any
    source: ConfigSource
    timestamp: datetime = field(default_factory=datetime.utcnow)
    changed_by: Optional[str] = None


class ConfigValidator(ABC):
    """配置驗證器基類"""

    @abstractmethod
    def validate(self, key: str, value: Any) -> tuple[bool, Optional[str]]:
        """
        驗證配置值

        Args:
            key: 配置鍵
            value: 配置值

        Returns:
            (是否有效, 錯誤消息)
        """
        pass


class TypeValidator(ConfigValidator):
    """類型驗證器"""

    def __init__(self, expected_types: Dict[str, type]):
        """
        初始化類型驗證器

        Args:
            expected_types: 鍵到預期類型的映射
        """
        self.expected_types = expected_types

    def validate(self, key: str, value: Any) -> tuple[bool, Optional[str]]:
        if key not in self.expected_types:
            return True, None

        expected_type = self.expected_types[key]
        if not isinstance(value, expected_type):
            return False, f"期望類型 {expected_type.__name__}，實際類型 {type(value).__name__}"
        return True, None


class RangeValidator(ConfigValidator):
    """範圍驗證器"""

    def __init__(self, ranges: Dict[str, tuple[Optional[float], Optional[float]]]):
        """
        初始化範圍驗證器

        Args:
            ranges: 鍵到 (最小值, 最大值) 的映射
        """
        self.ranges = ranges

    def validate(self, key: str, value: Any) -> tuple[bool, Optional[str]]:
        if key not in self.ranges:
            return True, None

        if not isinstance(value, (int, float)):
            return True, None  # 非數字類型跳過

        min_val, max_val = self.ranges[key]

        if min_val is not None and value < min_val:
            return False, f"值 {value} 小於最小值 {min_val}"

        if max_val is not None and value > max_val:
            return False, f"值 {value} 大於最大值 {max_val}"

        return True, None


class EnumValidator(ConfigValidator):
    """枚舉驗證器"""

    def __init__(self, allowed_values: Dict[str, Set[Any]]):
        """
        初始化枚舉驗證器

        Args:
            allowed_values: 鍵到允許值集合的映射
        """
        self.allowed_values = allowed_values

    def validate(self, key: str, value: Any) -> tuple[bool, Optional[str]]:
        if key not in self.allowed_values:
            return True, None

        allowed = self.allowed_values[key]
        if value not in allowed:
            return False, f"值 {value} 不在允許範圍 {allowed} 內"

        return True, None


class DynamicConfigManager:
    """
    動態配置管理器

    功能：
    - 多來源配置加載（文件、環境變量、遠端）
    - 運行時配置更新
    - 配置驗證
    - 變更通知
    - 配置版本追蹤
    """

    def __init__(
        self,
        config_file: Optional[str] = None,
        auto_reload: bool = False,
        reload_interval: float = 30.0,
        env_prefix: str = "APP_",
    ):
        """
        初始化動態配置管理器

        Args:
            config_file: 配置文件路徑
            auto_reload: 是否自動重新加載
            reload_interval: 重新加載間隔（秒）
            env_prefix: 環境變量前綴
        """
        self.config_file = config_file
        self.auto_reload = auto_reload
        self.reload_interval = reload_interval
        self.env_prefix = env_prefix

        # 配置存儲
        self._config: Dict[str, ConfigValue] = {}
        self._defaults: Dict[str, Any] = {}
        self._lock = threading.RLock()

        # 驗證器
        self._validators: List[ConfigValidator] = []

        # 回調
        self._change_listeners: List[Callable[[ConfigChange], None]] = []
        self._key_listeners: Dict[str, List[Callable[[str, Any, Any], None]]] = {}

        # 文件監控
        self._file_hash: Optional[str] = None
        self._reload_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

        # 加載初始配置
        if config_file:
            self._load_from_file(config_file)
        self._load_from_environment()

        logger.info(
            f"動態配置管理器初始化完成 "
            f"(配置項: {len(self._config)}, 自動重載: {auto_reload})"
        )

    # ========================================================================
    # 配置加載
    # ========================================================================

    def _load_from_file(self, file_path: str) -> bool:
        """從文件加載配置"""
        path = Path(file_path)

        if not path.exists():
            logger.warning(f"配置文件不存在: {file_path}")
            return False

        try:
            content = path.read_text(encoding="utf-8")
            self._file_hash = hashlib.md5(content.encode()).hexdigest()

            if path.suffix in (".yaml", ".yml"):
                try:
                    import yaml
                    data = yaml.safe_load(content)
                except ImportError:
                    logger.warning("未安裝 PyYAML，跳過 YAML 配置加載")
                    return False
            elif path.suffix == ".json":
                data = json.loads(content)
            else:
                logger.warning(f"不支持的配置文件格式: {path.suffix}")
                return False

            if isinstance(data, dict):
                self._merge_config(data, ConfigSource.FILE)
                logger.info(f"從文件加載了 {len(data)} 個配置項")
                return True

        except Exception as e:
            logger.error(f"加載配置文件失敗: {e}")

        return False

    def _load_from_environment(self):
        """從環境變量加載配置"""
        loaded_count = 0

        for key, value in os.environ.items():
            if key.startswith(self.env_prefix):
                config_key = key[len(self.env_prefix):].lower()
                parsed_value = self._parse_env_value(value)

                with self._lock:
                    self._config[config_key] = ConfigValue(
                        value=parsed_value,
                        source=ConfigSource.ENVIRONMENT,
                    )
                loaded_count += 1

        if loaded_count > 0:
            logger.info(f"從環境變量加載了 {loaded_count} 個配置項")

    def _parse_env_value(self, value: str) -> Any:
        """解析環境變量值"""
        # 嘗試解析為 JSON
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            pass

        # 嘗試解析為布爾值
        if value.lower() in ("true", "yes", "1", "on"):
            return True
        if value.lower() in ("false", "no", "0", "off"):
            return False

        # 嘗試解析為數字
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        return value

    def _merge_config(self, data: Dict[str, Any], source: ConfigSource):
        """合併配置數據"""
        with self._lock:
            for key, value in self._flatten_dict(data).items():
                existing = self._config.get(key)

                # 環境變量優先級最高
                if existing and existing.source == ConfigSource.ENVIRONMENT:
                    continue

                self._config[key] = ConfigValue(
                    value=value,
                    source=source,
                )

    def _flatten_dict(
        self,
        data: Dict[str, Any],
        prefix: str = "",
    ) -> Dict[str, Any]:
        """扁平化嵌套字典"""
        result = {}

        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                result.update(self._flatten_dict(value, full_key))
            else:
                result[full_key] = value

        return result

    # ========================================================================
    # 配置訪問
    # ========================================================================

    def get(self, key: str, default: Any = None) -> Any:
        """
        獲取配置值

        Args:
            key: 配置鍵
            default: 默認值

        Returns:
            配置值
        """
        with self._lock:
            if key in self._config:
                return self._config[key].value
            if key in self._defaults:
                return self._defaults[key]
            return default

    def get_typed(self, key: str, type_: type, default: T = None) -> T:
        """
        獲取指定類型的配置值

        Args:
            key: 配置鍵
            type_: 預期類型
            default: 默認值

        Returns:
            配置值
        """
        value = self.get(key, default)

        if value is None:
            return default

        if isinstance(value, type_):
            return value

        # 嘗試轉換
        try:
            return type_(value)
        except (ValueError, TypeError):
            logger.warning(f"無法將配置 {key} 轉換為 {type_.__name__}")
            return default

    def get_int(self, key: str, default: int = 0) -> int:
        """獲取整數配置"""
        return self.get_typed(key, int, default)

    def get_float(self, key: str, default: float = 0.0) -> float:
        """獲取浮點數配置"""
        return self.get_typed(key, float, default)

    def get_bool(self, key: str, default: bool = False) -> bool:
        """獲取布爾配置"""
        value = self.get(key, default)

        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            return value.lower() in ("true", "yes", "1", "on")

        return bool(value)

    def get_str(self, key: str, default: str = "") -> str:
        """獲取字符串配置"""
        return self.get_typed(key, str, default)

    def get_list(self, key: str, default: List = None) -> List:
        """獲取列表配置"""
        value = self.get(key, default or [])

        if isinstance(value, list):
            return value

        if isinstance(value, str):
            return [v.strip() for v in value.split(",")]

        return list(value) if value else []

    def get_dict(self, key: str, default: Dict = None) -> Dict:
        """獲取字典配置"""
        return self.get_typed(key, dict, default or {})

    def get_config_value(self, key: str) -> Optional[ConfigValue]:
        """獲取完整的配置值對象"""
        with self._lock:
            return self._config.get(key)

    def __getitem__(self, key: str) -> Any:
        """支持字典式訪問"""
        return self.get(key)

    def __contains__(self, key: str) -> bool:
        """支持 in 操作符"""
        with self._lock:
            return key in self._config or key in self._defaults

    # ========================================================================
    # 配置設置
    # ========================================================================

    def set(
        self,
        key: str,
        value: Any,
        source: ConfigSource = ConfigSource.REMOTE,
        changed_by: Optional[str] = None,
    ) -> bool:
        """
        設置配置值

        Args:
            key: 配置鍵
            value: 配置值
            source: 配置來源
            changed_by: 變更者

        Returns:
            是否設置成功
        """
        # 驗證
        is_valid, error = self._validate(key, value)
        if not is_valid:
            logger.error(f"配置驗證失敗 [{key}]: {error}")
            return False

        with self._lock:
            old_value = self._config.get(key)
            old_raw_value = old_value.value if old_value else None

            # 創建新配置值
            new_config = ConfigValue(
                value=value,
                source=source,
                version=(old_value.version + 1) if old_value else 1,
            )

            self._config[key] = new_config

            # 記錄變更
            change = ConfigChange(
                key=key,
                old_value=old_raw_value,
                new_value=value,
                source=source,
                changed_by=changed_by,
            )

            # 通知監聽器
            self._notify_change(change)

        logger.info(f"配置更新 [{key}]: {old_raw_value} -> {value}")
        return True

    def set_default(self, key: str, value: Any):
        """設置默認值"""
        with self._lock:
            self._defaults[key] = value

    def set_defaults(self, defaults: Dict[str, Any]):
        """批量設置默認值"""
        with self._lock:
            for key, value in self._flatten_dict(defaults).items():
                self._defaults[key] = value

    def delete(self, key: str) -> bool:
        """刪除配置"""
        with self._lock:
            if key in self._config:
                del self._config[key]
                logger.info(f"配置已刪除: {key}")
                return True
        return False

    # ========================================================================
    # 驗證
    # ========================================================================

    def add_validator(self, validator: ConfigValidator):
        """添加驗證器"""
        self._validators.append(validator)

    def _validate(self, key: str, value: Any) -> tuple[bool, Optional[str]]:
        """驗證配置值"""
        for validator in self._validators:
            is_valid, error = validator.validate(key, value)
            if not is_valid:
                return False, error
        return True, None

    # ========================================================================
    # 變更通知
    # ========================================================================

    def on_change(self, callback: Callable[[ConfigChange], None]):
        """註冊全局變更監聽器"""
        self._change_listeners.append(callback)
        return callback

    def on_key_change(self, key: str, callback: Callable[[str, Any, Any], None]):
        """
        註冊特定鍵的變更監聽器

        Args:
            key: 配置鍵
            callback: 回調函數 (key, old_value, new_value)
        """
        if key not in self._key_listeners:
            self._key_listeners[key] = []
        self._key_listeners[key].append(callback)
        return callback

    def _notify_change(self, change: ConfigChange):
        """通知變更"""
        # 全局監聽器
        for listener in self._change_listeners:
            try:
                listener(change)
            except Exception as e:
                logger.error(f"變更監聽器執行失敗: {e}")

        # 特定鍵監聽器
        if change.key in self._key_listeners:
            for listener in self._key_listeners[change.key]:
                try:
                    listener(change.key, change.old_value, change.new_value)
                except Exception as e:
                    logger.error(f"鍵監聽器執行失敗 [{change.key}]: {e}")

    # ========================================================================
    # 自動重載
    # ========================================================================

    async def start_auto_reload(self):
        """啟動自動重載"""
        if not self.auto_reload or not self.config_file:
            return

        self._stop_event.clear()
        self._reload_task = asyncio.create_task(self._auto_reload_loop())
        logger.info("配置自動重載已啟動")

    async def stop_auto_reload(self):
        """停止自動重載"""
        self._stop_event.set()

        if self._reload_task:
            self._reload_task.cancel()
            try:
                await self._reload_task
            except asyncio.CancelledError:
                pass

        logger.info("配置自動重載已停止")

    async def _auto_reload_loop(self):
        """自動重載循環"""
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(self.reload_interval)

                if self._check_file_changed():
                    logger.info("檢測到配置文件變更，重新加載...")
                    self._load_from_file(self.config_file)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"自動重載失敗: {e}")

    def _check_file_changed(self) -> bool:
        """檢查文件是否變更"""
        if not self.config_file:
            return False

        path = Path(self.config_file)
        if not path.exists():
            return False

        try:
            content = path.read_text(encoding="utf-8")
            new_hash = hashlib.md5(content.encode()).hexdigest()

            if new_hash != self._file_hash:
                self._file_hash = new_hash
                return True

        except Exception as e:
            logger.error(f"檢查配置文件變更失敗: {e}")

        return False

    # ========================================================================
    # 導出和快照
    # ========================================================================

    def get_all(self) -> Dict[str, Any]:
        """獲取所有配置"""
        with self._lock:
            result = dict(self._defaults)
            for key, config_value in self._config.items():
                result[key] = config_value.value
            return result

    def get_all_with_metadata(self) -> Dict[str, Dict[str, Any]]:
        """獲取所有配置及其元數據"""
        with self._lock:
            result = {}
            for key, config_value in self._config.items():
                result[key] = config_value.to_dict()
            return result

    def export_to_dict(self) -> Dict[str, Any]:
        """導出配置為字典"""
        return self.get_all()

    def export_to_json(self, indent: int = 2) -> str:
        """導出配置為 JSON"""
        return json.dumps(self.get_all(), indent=indent, ensure_ascii=False)

    def create_snapshot(self) -> Dict[str, ConfigValue]:
        """創建配置快照"""
        with self._lock:
            return {
                key: ConfigValue(
                    value=cv.value,
                    source=cv.source,
                    updated_at=cv.updated_at,
                    version=cv.version,
                    metadata=cv.metadata.copy(),
                )
                for key, cv in self._config.items()
            }

    def restore_snapshot(self, snapshot: Dict[str, ConfigValue]):
        """恢復配置快照"""
        with self._lock:
            self._config = snapshot
        logger.info(f"已恢復配置快照 ({len(snapshot)} 項)")


# ============================================================================
# 全局實例
# ============================================================================

_config_manager: Optional[DynamicConfigManager] = None


def get_config_manager() -> DynamicConfigManager:
    """獲取全局配置管理器"""
    global _config_manager
    if _config_manager is None:
        _config_manager = DynamicConfigManager()
    return _config_manager


def configure_config_manager(
    config_file: Optional[str] = None,
    auto_reload: bool = False,
    reload_interval: float = 30.0,
    env_prefix: str = "APP_",
) -> DynamicConfigManager:
    """配置全局配置管理器"""
    global _config_manager
    _config_manager = DynamicConfigManager(
        config_file=config_file,
        auto_reload=auto_reload,
        reload_interval=reload_interval,
        env_prefix=env_prefix,
    )
    return _config_manager


# ============================================================================
# FastAPI 整合
# ============================================================================


def setup_config_routes(app, config_manager: Optional[DynamicConfigManager] = None):
    """
    設置配置管理路由

    Args:
        app: FastAPI 應用
        config_manager: 配置管理器實例
    """
    from fastapi import HTTPException
    from pydantic import BaseModel

    manager = config_manager or get_config_manager()

    class ConfigUpdate(BaseModel):
        value: Any

    @app.get("/config")
    async def get_all_config():
        """獲取所有配置"""
        return manager.get_all()

    @app.get("/config/{key:path}")
    async def get_config(key: str):
        """獲取特定配置"""
        value = manager.get_config_value(key)
        if value is None:
            raise HTTPException(status_code=404, detail=f"配置不存在: {key}")
        return value.to_dict()

    @app.put("/config/{key:path}")
    async def update_config(key: str, update: ConfigUpdate):
        """更新配置"""
        success = manager.set(key, update.value, source=ConfigSource.REMOTE)
        if not success:
            raise HTTPException(status_code=400, detail="配置更新失敗")
        return {"message": "配置已更新", "key": key, "value": update.value}

    @app.delete("/config/{key:path}")
    async def delete_config(key: str):
        """刪除配置"""
        success = manager.delete(key)
        if not success:
            raise HTTPException(status_code=404, detail=f"配置不存在: {key}")
        return {"message": "配置已刪除", "key": key}

    logger.info("配置管理路由已設置")
