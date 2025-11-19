"""
審計日誌記錄器

記錄和追蹤系統中的重要操作和事件。
"""
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field, asdict
import json
from pathlib import Path

from loguru import logger


# ============================================================================
# 審計等級和類型
# ============================================================================


class AuditLevel(Enum):
    """審計等級"""

    INFO = "info"  # 一般資訊
    WARNING = "warning"  # 警告
    ERROR = "error"  # 錯誤
    CRITICAL = "critical"  # 嚴重
    SECURITY = "security"  # 安全事件


class AuditEventType(Enum):
    """審計事件類型"""

    # 用戶操作
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_REGISTER = "user.register"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"

    # API 操作
    API_CALL = "api.call"
    API_ERROR = "api.error"
    API_TIMEOUT = "api.timeout"

    # 資料操作
    DATA_CREATE = "data.create"
    DATA_READ = "data.read"
    DATA_UPDATE = "data.update"
    DATA_DELETE = "data.delete"

    # 安全事件
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    AUTH_DENIED = "auth.denied"
    PERMISSION_DENIED = "permission.denied"

    # 系統事件
    SYSTEM_START = "system.start"
    SYSTEM_STOP = "system.stop"
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"

    # 模型操作
    MODEL_LOAD = "model.load"
    MODEL_GENERATE = "model.generate"
    MODEL_ERROR = "model.error"

    # 自訂事件
    CUSTOM = "custom"


# ============================================================================
# 審計事件
# ============================================================================


@dataclass
class AuditEvent:
    """審計事件"""

    # 基本資訊
    event_type: AuditEventType
    level: AuditLevel
    message: str

    # 上下文資訊
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # 操作資訊
    resource: Optional[str] = None  # 資源名稱
    action: Optional[str] = None  # 操作動作
    result: Optional[str] = None  # 操作結果（success/failure）

    # 額外資料
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 時間戳記
    timestamp: datetime = field(default_factory=datetime.now)

    # 事件 ID
    event_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["level"] = self.level.value
        data["timestamp"] = self.timestamp.isoformat()
        return data

    def to_json(self) -> str:
        """轉換為 JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ============================================================================
# 審計日誌記錄器
# ============================================================================


class AuditLogger:
    """審計日誌記錄器"""

    def __init__(
        self,
        log_file: Optional[str] = None,
        log_to_console: bool = True,
        log_to_database: bool = False,
        database_manager=None,
    ):
        """
        初始化審計日誌記錄器

        Args:
            log_file: 日誌檔案路徑
            log_to_console: 是否輸出到控制台
            log_to_database: 是否儲存到資料庫
            database_manager: 資料庫管理器
        """
        self.log_to_console = log_to_console
        self.log_to_database = log_to_database
        self.database_manager = database_manager

        # 設置檔案日誌
        self.log_file = log_file
        if self.log_file:
            self._setup_file_logging()

        # 事件緩衝區（用於批次寫入）
        self.event_buffer: List[AuditEvent] = []
        self.buffer_size = 100

        logger.info("審計日誌記錄器初始化完成")

    def _setup_file_logging(self):
        """設置檔案日誌"""
        log_path = Path(self.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # 配置 loguru
        logger.add(
            self.log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
            rotation="100 MB",  # 100MB 輪換
            retention="30 days",  # 保留 30 天
            compression="zip",  # 壓縮舊日誌
            serialize=True,  # JSON 格式
        )

        logger.info(f"審計日誌檔案: {self.log_file}")

    # ========================================================================
    # 記錄事件
    # ========================================================================

    def log(
        self,
        event_type: AuditEventType,
        message: str,
        level: AuditLevel = AuditLevel.INFO,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        result: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> AuditEvent:
        """
        記錄審計事件

        Args:
            event_type: 事件類型
            message: 事件訊息
            level: 審計等級
            user_id: 用戶 ID
            session_id: 會話 ID
            ip_address: IP 地址
            resource: 資源名稱
            action: 操作動作
            result: 操作結果
            metadata: 額外資料
            **kwargs: 其他參數

        Returns:
            審計事件
        """
        # 創建審計事件
        event = AuditEvent(
            event_type=event_type,
            level=level,
            message=message,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            resource=resource,
            action=action,
            result=result,
            metadata=metadata or {},
            **kwargs,
        )

        # 記錄到各個目標
        self._log_to_console(event)
        self._log_to_file(event)
        self._log_to_database(event)
        self._add_to_buffer(event)

        return event

    def _log_to_console(self, event: AuditEvent):
        """記錄到控制台"""
        if not self.log_to_console:
            return

        # 根據等級使用不同的日誌方法
        log_method = {
            AuditLevel.INFO: logger.info,
            AuditLevel.WARNING: logger.warning,
            AuditLevel.ERROR: logger.error,
            AuditLevel.CRITICAL: logger.critical,
            AuditLevel.SECURITY: logger.warning,
        }.get(event.level, logger.info)

        log_method(f"[AUDIT] {event.event_type.value} | {event.message}")

    def _log_to_file(self, event: AuditEvent):
        """記錄到檔案"""
        if not self.log_file:
            return

        # loguru 會自動處理
        pass

    def _log_to_database(self, event: AuditEvent):
        """記錄到資料庫"""
        if not self.log_to_database or not self.database_manager:
            return

        try:
            # 這裡需要資料庫模型
            # 暫時跳過
            pass
        except Exception as e:
            logger.error(f"審計日誌寫入資料庫失敗: {e}")

    def _add_to_buffer(self, event: AuditEvent):
        """添加到緩衝區"""
        self.event_buffer.append(event)

        # 達到緩衝區大小時批次寫入
        if len(self.event_buffer) >= self.buffer_size:
            self.flush_buffer()

    def flush_buffer(self):
        """刷新緩衝區"""
        if not self.event_buffer:
            return

        logger.info(f"刷新審計日誌緩衝區: {len(self.event_buffer)} 個事件")
        self.event_buffer.clear()

    # ========================================================================
    # 便捷方法
    # ========================================================================

    def log_user_login(
        self, user_id: str, ip_address: Optional[str] = None, success: bool = True
    ):
        """記錄用戶登入"""
        return self.log(
            event_type=AuditEventType.USER_LOGIN,
            message=f"用戶登入: {user_id}",
            level=AuditLevel.SECURITY if success else AuditLevel.WARNING,
            user_id=user_id,
            ip_address=ip_address,
            action="login",
            result="success" if success else "failure",
        )

    def log_user_logout(self, user_id: str, session_id: Optional[str] = None):
        """記錄用戶登出"""
        return self.log(
            event_type=AuditEventType.USER_LOGOUT,
            message=f"用戶登出: {user_id}",
            level=AuditLevel.INFO,
            user_id=user_id,
            session_id=session_id,
            action="logout",
            result="success",
        )

    def log_api_call(
        self,
        endpoint: str,
        method: str,
        user_id: Optional[str] = None,
        status_code: int = 200,
        response_time: Optional[float] = None,
    ):
        """記錄 API 調用"""
        level = AuditLevel.INFO if status_code < 400 else AuditLevel.ERROR

        return self.log(
            event_type=AuditEventType.API_CALL,
            message=f"{method} {endpoint} - {status_code}",
            level=level,
            user_id=user_id,
            resource=endpoint,
            action=method,
            result="success" if status_code < 400 else "error",
            metadata={
                "status_code": status_code,
                "response_time": response_time,
            },
        )

    def log_data_operation(
        self,
        operation: str,  # create/read/update/delete
        resource: str,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
    ):
        """記錄資料操作"""
        event_type_map = {
            "create": AuditEventType.DATA_CREATE,
            "read": AuditEventType.DATA_READ,
            "update": AuditEventType.DATA_UPDATE,
            "delete": AuditEventType.DATA_DELETE,
        }

        event_type = event_type_map.get(operation, AuditEventType.CUSTOM)

        return self.log(
            event_type=event_type,
            message=f"{operation.upper()} {resource}" + (f" ({resource_id})" if resource_id else ""),
            level=AuditLevel.INFO,
            user_id=user_id,
            resource=resource,
            action=operation,
            result="success",
            metadata={
                "resource_id": resource_id,
                "changes": changes,
            },
        )

    def log_auth_failure(
        self, user_id: Optional[str] = None, ip_address: Optional[str] = None, reason: str = ""
    ):
        """記錄認證失敗"""
        return self.log(
            event_type=AuditEventType.AUTH_FAILURE,
            message=f"認證失敗: {reason}",
            level=AuditLevel.SECURITY,
            user_id=user_id,
            ip_address=ip_address,
            action="authenticate",
            result="failure",
            metadata={"reason": reason},
        )

    def log_permission_denied(
        self, user_id: str, resource: str, action: str, reason: str = ""
    ):
        """記錄權限拒絕"""
        return self.log(
            event_type=AuditEventType.PERMISSION_DENIED,
            message=f"權限拒絕: {user_id} 嘗試 {action} {resource}",
            level=AuditLevel.WARNING,
            user_id=user_id,
            resource=resource,
            action=action,
            result="denied",
            metadata={"reason": reason},
        )

    def log_model_operation(
        self,
        operation: str,
        model_name: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """記錄模型操作"""
        event_type_map = {
            "load": AuditEventType.MODEL_LOAD,
            "generate": AuditEventType.MODEL_GENERATE,
            "error": AuditEventType.MODEL_ERROR,
        }

        event_type = event_type_map.get(operation, AuditEventType.CUSTOM)
        level = AuditLevel.ERROR if operation == "error" else AuditLevel.INFO

        return self.log(
            event_type=event_type,
            message=f"模型操作: {operation} - {model_name}",
            level=level,
            user_id=user_id,
            resource=model_name,
            action=operation,
            metadata=metadata or {},
        )

    def log_system_event(
        self,
        event: str,
        level: AuditLevel = AuditLevel.INFO,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """記錄系統事件"""
        event_type_map = {
            "start": AuditEventType.SYSTEM_START,
            "stop": AuditEventType.SYSTEM_STOP,
            "error": AuditEventType.SYSTEM_ERROR,
            "warning": AuditEventType.SYSTEM_WARNING,
        }

        event_type = event_type_map.get(event, AuditEventType.CUSTOM)

        return self.log(
            event_type=event_type,
            message=f"系統事件: {event}",
            level=level,
            action=event,
            metadata=metadata or {},
        )

    # ========================================================================
    # 查詢和分析
    # ========================================================================

    def get_events_by_user(self, user_id: str) -> List[AuditEvent]:
        """獲取特定用戶的審計事件"""
        return [event for event in self.event_buffer if event.user_id == user_id]

    def get_events_by_type(self, event_type: AuditEventType) -> List[AuditEvent]:
        """獲取特定類型的審計事件"""
        return [event for event in self.event_buffer if event.event_type == event_type]

    def get_events_by_level(self, level: AuditLevel) -> List[AuditEvent]:
        """獲取特定等級的審計事件"""
        return [event for event in self.event_buffer if event.level == level]

    def get_security_events(self) -> List[AuditEvent]:
        """獲取安全相關事件"""
        return self.get_events_by_level(AuditLevel.SECURITY)

    def get_failed_operations(self) -> List[AuditEvent]:
        """獲取失敗的操作"""
        return [
            event
            for event in self.event_buffer
            if event.result in ["failure", "error", "denied"]
        ]

    # ========================================================================
    # 報告生成
    # ========================================================================

    def generate_summary(self) -> Dict[str, Any]:
        """生成審計摘要"""
        events = self.event_buffer

        # 按類型統計
        by_type = {}
        for event in events:
            event_type = event.event_type.value
            by_type[event_type] = by_type.get(event_type, 0) + 1

        # 按等級統計
        by_level = {}
        for event in events:
            level = event.level.value
            by_level[level] = by_level.get(level, 0) + 1

        # 按結果統計
        by_result = {}
        for event in events:
            if event.result:
                by_result[event.result] = by_result.get(event.result, 0) + 1

        return {
            "total_events": len(events),
            "by_type": by_type,
            "by_level": by_level,
            "by_result": by_result,
            "security_events": len(self.get_security_events()),
            "failed_operations": len(self.get_failed_operations()),
        }

    def export_events(
        self, file_path: str, format: str = "json", filter_func=None
    ):
        """
        導出審計事件

        Args:
            file_path: 導出檔案路徑
            format: 導出格式（json/csv）
            filter_func: 過濾函數
        """
        events = self.event_buffer

        if filter_func:
            events = [e for e in events if filter_func(e)]

        output_path = Path(file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    [e.to_dict() for e in events],
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        elif format == "csv":
            import csv

            with open(output_path, "w", encoding="utf-8", newline="") as f:
                if events:
                    writer = csv.DictWriter(f, fieldnames=events[0].to_dict().keys())
                    writer.writeheader()
                    for event in events:
                        writer.writerow(event.to_dict())

        logger.info(f"審計事件已導出: {output_path} ({len(events)} 個事件)")

    def __del__(self):
        """析構時刷新緩衝區"""
        self.flush_buffer()
