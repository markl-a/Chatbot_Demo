"""
增強告警系統

提供多渠道告警通知、告警聚合和告警管理功能。
"""

import asyncio
import hashlib
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict

from loguru import logger


class AlertSeverity(str, Enum):
    """告警嚴重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertState(str, Enum):
    """告警狀態"""
    FIRING = "firing"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SILENCED = "silenced"


@dataclass
class Alert:
    """告警"""
    id: str
    name: str
    severity: AlertSeverity
    message: str
    source: str
    state: AlertState = AlertState.FIRING
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    value: Optional[float] = None
    threshold: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    fire_count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "id": self.id,
            "name": self.name,
            "severity": self.severity.value,
            "message": self.message,
            "source": self.source,
            "state": self.state.value,
            "labels": self.labels,
            "annotations": self.annotations,
            "value": self.value,
            "threshold": self.threshold,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
            "fire_count": self.fire_count,
        }

    @property
    def fingerprint(self) -> str:
        """生成告警指紋用於去重"""
        key = f"{self.name}:{self.source}:{sorted(self.labels.items())}"
        return hashlib.md5(key.encode()).hexdigest()[:12]


@dataclass
class AlertRule:
    """告警規則"""
    name: str
    condition: Callable[[], bool]
    severity: AlertSeverity
    message_template: str
    source: str = "rule"
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    for_duration: float = 0  # 持續時間（秒）才觸發
    repeat_interval: float = 3600  # 重複通知間隔（秒）
    enabled: bool = True

    # 內部狀態
    _pending_since: Optional[float] = field(default=None, repr=False)
    _last_fired: Optional[float] = field(default=None, repr=False)


class AlertChannel(ABC):
    """告警通知渠道基類"""

    @abstractmethod
    async def send(self, alert: Alert) -> bool:
        """
        發送告警

        Args:
            alert: 告警對象

        Returns:
            是否發送成功
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """獲取渠道名稱"""
        pass


class LogChannel(AlertChannel):
    """日誌渠道"""

    def __init__(self, log_level: str = "warning"):
        self.log_level = log_level

    async def send(self, alert: Alert) -> bool:
        log_func = getattr(logger, self.log_level, logger.warning)
        log_func(
            f"[ALERT] [{alert.severity.value.upper()}] {alert.name}: {alert.message} "
            f"(source: {alert.source}, state: {alert.state.value})"
        )
        return True

    def get_name(self) -> str:
        return "log"


class WebhookChannel(AlertChannel):
    """Webhook 渠道"""

    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 10.0,
    ):
        self.url = url
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout = timeout

    async def send(self, alert: Alert) -> bool:
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.url,
                    json=alert.to_dict(),
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    if response.status < 300:
                        logger.debug(f"Webhook 告警發送成功: {alert.name}")
                        return True
                    else:
                        logger.error(
                            f"Webhook 告警發送失敗: {response.status} - {await response.text()}"
                        )
                        return False

        except ImportError:
            logger.error("需要安裝 aiohttp 才能使用 Webhook 渠道")
            return False
        except Exception as e:
            logger.error(f"Webhook 告警發送失敗: {e}")
            return False

    def get_name(self) -> str:
        return f"webhook:{self.url}"


class SlackChannel(AlertChannel):
    """Slack 渠道"""

    def __init__(
        self,
        webhook_url: str,
        channel: Optional[str] = None,
        username: str = "Alert Bot",
    ):
        self.webhook_url = webhook_url
        self.channel = channel
        self.username = username

    async def send(self, alert: Alert) -> bool:
        try:
            import aiohttp

            # 根據嚴重程度選擇顏色
            color_map = {
                AlertSeverity.INFO: "#36a64f",
                AlertSeverity.WARNING: "#ffcc00",
                AlertSeverity.ERROR: "#ff6600",
                AlertSeverity.CRITICAL: "#ff0000",
            }

            payload = {
                "username": self.username,
                "attachments": [
                    {
                        "color": color_map.get(alert.severity, "#808080"),
                        "title": f"[{alert.severity.value.upper()}] {alert.name}",
                        "text": alert.message,
                        "fields": [
                            {"title": "Source", "value": alert.source, "short": True},
                            {"title": "State", "value": alert.state.value, "short": True},
                        ],
                        "footer": f"Alert ID: {alert.id}",
                        "ts": int(alert.created_at.timestamp()),
                    }
                ],
            }

            if self.channel:
                payload["channel"] = self.channel

            # 添加標籤
            for key, value in alert.labels.items():
                payload["attachments"][0]["fields"].append(
                    {"title": key, "value": value, "short": True}
                )

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10.0),
                ) as response:
                    if response.status == 200:
                        logger.debug(f"Slack 告警發送成功: {alert.name}")
                        return True
                    else:
                        logger.error(f"Slack 告警發送失敗: {response.status}")
                        return False

        except ImportError:
            logger.error("需要安裝 aiohttp 才能使用 Slack 渠道")
            return False
        except Exception as e:
            logger.error(f"Slack 告警發送失敗: {e}")
            return False

    def get_name(self) -> str:
        return "slack"


class EmailChannel(AlertChannel):
    """郵件渠道"""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: List[str],
        use_tls: bool = True,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs
        self.use_tls = use_tls

    async def send(self, alert: Alert) -> bool:
        try:
            import aiosmtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            # 構建郵件
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[{alert.severity.value.upper()}] {alert.name}"
            msg["From"] = self.from_addr
            msg["To"] = ", ".join(self.to_addrs)

            # 純文本內容
            text_content = f"""
告警名稱: {alert.name}
嚴重程度: {alert.severity.value}
狀態: {alert.state.value}
來源: {alert.source}
時間: {alert.created_at.isoformat()}

消息:
{alert.message}

標籤:
{json.dumps(alert.labels, indent=2, ensure_ascii=False)}
            """

            # HTML 內容
            html_content = f"""
<html>
<body>
<h2 style="color: {'#ff0000' if alert.severity == AlertSeverity.CRITICAL else '#ff6600'}">
    [{alert.severity.value.upper()}] {alert.name}
</h2>
<table>
    <tr><td><strong>狀態:</strong></td><td>{alert.state.value}</td></tr>
    <tr><td><strong>來源:</strong></td><td>{alert.source}</td></tr>
    <tr><td><strong>時間:</strong></td><td>{alert.created_at.isoformat()}</td></tr>
</table>
<h3>消息</h3>
<p>{alert.message}</p>
<h3>標籤</h3>
<pre>{json.dumps(alert.labels, indent=2, ensure_ascii=False)}</pre>
</body>
</html>
            """

            msg.attach(MIMEText(text_content, "plain", "utf-8"))
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            # 發送郵件
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.username,
                password=self.password,
                start_tls=self.use_tls,
            )

            logger.debug(f"郵件告警發送成功: {alert.name}")
            return True

        except ImportError:
            logger.error("需要安裝 aiosmtplib 才能使用郵件渠道")
            return False
        except Exception as e:
            logger.error(f"郵件告警發送失敗: {e}")
            return False

    def get_name(self) -> str:
        return "email"


class CallbackChannel(AlertChannel):
    """回調渠道"""

    def __init__(self, callback: Callable[[Alert], bool], name: str = "callback"):
        self.callback = callback
        self.name = name

    async def send(self, alert: Alert) -> bool:
        try:
            if asyncio.iscoroutinefunction(self.callback):
                return await self.callback(alert)
            else:
                return self.callback(alert)
        except Exception as e:
            logger.error(f"回調告警發送失敗: {e}")
            return False

    def get_name(self) -> str:
        return self.name


@dataclass
class SilenceRule:
    """靜音規則"""
    id: str
    matchers: Dict[str, str]  # 標籤匹配器
    starts_at: datetime
    ends_at: datetime
    created_by: str
    comment: Optional[str] = None

    def matches(self, alert: Alert) -> bool:
        """檢查告警是否匹配此靜音規則"""
        now = datetime.utcnow()
        if now < self.starts_at or now > self.ends_at:
            return False

        for key, pattern in self.matchers.items():
            if key == "name" and alert.name != pattern:
                return False
            if key == "severity" and alert.severity.value != pattern:
                return False
            if key in alert.labels and alert.labels[key] != pattern:
                return False

        return True


class AlertManager:
    """
    告警管理器

    功能：
    - 多渠道告警通知
    - 告警聚合和去重
    - 告警狀態管理
    - 靜音規則
    - 告警歷史
    """

    def __init__(
        self,
        aggregation_window: float = 60.0,
        max_alerts_per_group: int = 100,
        history_retention: int = 1000,
    ):
        """
        初始化告警管理器

        Args:
            aggregation_window: 聚合窗口（秒）
            max_alerts_per_group: 每組最大告警數
            history_retention: 歷史保留數量
        """
        self.aggregation_window = aggregation_window
        self.max_alerts_per_group = max_alerts_per_group
        self.history_retention = history_retention

        # 渠道
        self._channels: List[AlertChannel] = []
        self._severity_channels: Dict[AlertSeverity, List[AlertChannel]] = defaultdict(list)

        # 告警存儲
        self._active_alerts: Dict[str, Alert] = {}  # fingerprint -> Alert
        self._alert_history: List[Alert] = []
        self._rules: List[AlertRule] = []

        # 靜音規則
        self._silence_rules: List[SilenceRule] = []

        # 聚合
        self._pending_alerts: Dict[str, List[Alert]] = defaultdict(list)
        self._last_aggregation: float = 0

        # 統計
        self._stats = {
            "total_alerts": 0,
            "total_notifications": 0,
            "failed_notifications": 0,
            "silenced_alerts": 0,
            "deduplicated_alerts": 0,
        }

        # 默認添加日誌渠道
        self.add_channel(LogChannel())

        logger.info("告警管理器初始化完成")

    # ========================================================================
    # 渠道管理
    # ========================================================================

    def add_channel(
        self,
        channel: AlertChannel,
        severities: Optional[List[AlertSeverity]] = None,
    ):
        """
        添加通知渠道

        Args:
            channel: 通知渠道
            severities: 僅接收指定嚴重程度的告警（None 表示全部）
        """
        self._channels.append(channel)

        if severities:
            for severity in severities:
                self._severity_channels[severity].append(channel)

        logger.info(f"添加告警渠道: {channel.get_name()}")

    def remove_channel(self, channel_name: str):
        """移除通知渠道"""
        self._channels = [c for c in self._channels if c.get_name() != channel_name]

        for severity in self._severity_channels:
            self._severity_channels[severity] = [
                c for c in self._severity_channels[severity]
                if c.get_name() != channel_name
            ]

        logger.info(f"移除告警渠道: {channel_name}")

    def _get_channels_for_alert(self, alert: Alert) -> List[AlertChannel]:
        """獲取適用於告警的渠道"""
        # 優先使用嚴重程度特定渠道
        if alert.severity in self._severity_channels:
            specific_channels = self._severity_channels[alert.severity]
            if specific_channels:
                return specific_channels

        return self._channels

    # ========================================================================
    # 告警操作
    # ========================================================================

    async def fire(
        self,
        name: str,
        severity: AlertSeverity,
        message: str,
        source: str = "app",
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
        value: Optional[float] = None,
        threshold: Optional[float] = None,
    ) -> Alert:
        """
        觸發告警

        Args:
            name: 告警名稱
            severity: 嚴重程度
            message: 告警消息
            source: 告警來源
            labels: 標籤
            annotations: 註釋
            value: 當前值
            threshold: 閾值

        Returns:
            告警對象
        """
        alert = Alert(
            id=f"{name}-{int(time.time() * 1000)}",
            name=name,
            severity=severity,
            message=message,
            source=source,
            labels=labels or {},
            annotations=annotations or {},
            value=value,
            threshold=threshold,
        )

        self._stats["total_alerts"] += 1

        # 檢查靜音
        if self._is_silenced(alert):
            alert.state = AlertState.SILENCED
            self._stats["silenced_alerts"] += 1
            logger.debug(f"告警被靜音: {name}")
            return alert

        # 檢查去重
        fingerprint = alert.fingerprint
        if fingerprint in self._active_alerts:
            existing = self._active_alerts[fingerprint]
            existing.fire_count += 1
            existing.updated_at = datetime.utcnow()
            self._stats["deduplicated_alerts"] += 1
            logger.debug(f"告警去重: {name} (fire_count: {existing.fire_count})")
            return existing

        # 存儲告警
        self._active_alerts[fingerprint] = alert

        # 發送通知
        await self._notify(alert)

        return alert

    async def resolve(
        self,
        name: str,
        source: str = "app",
        labels: Optional[Dict[str, str]] = None,
    ):
        """
        解除告警

        Args:
            name: 告警名稱
            source: 告警來源
            labels: 標籤
        """
        # 創建臨時告警用於匹配
        temp_alert = Alert(
            id="",
            name=name,
            severity=AlertSeverity.INFO,
            message="",
            source=source,
            labels=labels or {},
        )

        fingerprint = temp_alert.fingerprint

        if fingerprint in self._active_alerts:
            alert = self._active_alerts[fingerprint]
            alert.state = AlertState.RESOLVED
            alert.resolved_at = datetime.utcnow()
            alert.updated_at = datetime.utcnow()

            # 移到歷史
            self._add_to_history(alert)
            del self._active_alerts[fingerprint]

            # 發送解除通知
            await self._notify(alert)

            logger.info(f"告警已解除: {name}")

    async def acknowledge(
        self,
        alert_id: str,
        acknowledged_by: str,
        comment: Optional[str] = None,
    ):
        """
        確認告警

        Args:
            alert_id: 告警 ID
            acknowledged_by: 確認者
            comment: 備註
        """
        for fingerprint, alert in self._active_alerts.items():
            if alert.id == alert_id:
                alert.state = AlertState.ACKNOWLEDGED
                alert.acknowledged_at = datetime.utcnow()
                alert.acknowledged_by = acknowledged_by
                alert.updated_at = datetime.utcnow()

                if comment:
                    alert.annotations["ack_comment"] = comment

                logger.info(f"告警已確認: {alert.name} by {acknowledged_by}")
                return

        logger.warning(f"找不到告警: {alert_id}")

    def _is_silenced(self, alert: Alert) -> bool:
        """檢查告警是否被靜音"""
        for rule in self._silence_rules:
            if rule.matches(alert):
                return True
        return False

    def _add_to_history(self, alert: Alert):
        """添加到歷史"""
        self._alert_history.append(alert)

        # 限制歷史大小
        if len(self._alert_history) > self.history_retention:
            self._alert_history = self._alert_history[-self.history_retention:]

    # ========================================================================
    # 通知
    # ========================================================================

    async def _notify(self, alert: Alert):
        """發送告警通知"""
        channels = self._get_channels_for_alert(alert)

        for channel in channels:
            try:
                success = await channel.send(alert)
                if success:
                    self._stats["total_notifications"] += 1
                else:
                    self._stats["failed_notifications"] += 1
            except Exception as e:
                logger.error(f"發送告警通知失敗 [{channel.get_name()}]: {e}")
                self._stats["failed_notifications"] += 1

    # ========================================================================
    # 規則管理
    # ========================================================================

    def add_rule(self, rule: AlertRule):
        """添加告警規則"""
        self._rules.append(rule)
        logger.info(f"添加告警規則: {rule.name}")

    def remove_rule(self, name: str):
        """移除告警規則"""
        self._rules = [r for r in self._rules if r.name != name]
        logger.info(f"移除告警規則: {name}")

    async def evaluate_rules(self):
        """評估所有告警規則"""
        for rule in self._rules:
            if not rule.enabled:
                continue

            try:
                condition_met = rule.condition()
                now = time.time()

                if condition_met:
                    # 檢查 for_duration
                    if rule._pending_since is None:
                        rule._pending_since = now

                    pending_duration = now - rule._pending_since

                    if pending_duration >= rule.for_duration:
                        # 檢查重複間隔
                        if (
                            rule._last_fired is None
                            or (now - rule._last_fired) >= rule.repeat_interval
                        ):
                            await self.fire(
                                name=rule.name,
                                severity=rule.severity,
                                message=rule.message_template,
                                source=rule.source,
                                labels=rule.labels,
                                annotations=rule.annotations,
                            )
                            rule._last_fired = now
                else:
                    # 條件不滿足，重置 pending
                    if rule._pending_since is not None:
                        rule._pending_since = None
                        # 解除告警
                        await self.resolve(
                            name=rule.name,
                            source=rule.source,
                            labels=rule.labels,
                        )

            except Exception as e:
                logger.error(f"評估告警規則失敗 [{rule.name}]: {e}")

    # ========================================================================
    # 靜音規則管理
    # ========================================================================

    def add_silence(
        self,
        matchers: Dict[str, str],
        duration: timedelta,
        created_by: str,
        comment: Optional[str] = None,
    ) -> str:
        """
        添加靜音規則

        Args:
            matchers: 標籤匹配器
            duration: 持續時間
            created_by: 創建者
            comment: 備註

        Returns:
            靜音規則 ID
        """
        now = datetime.utcnow()
        silence_id = hashlib.md5(
            f"{matchers}{now.isoformat()}".encode()
        ).hexdigest()[:12]

        rule = SilenceRule(
            id=silence_id,
            matchers=matchers,
            starts_at=now,
            ends_at=now + duration,
            created_by=created_by,
            comment=comment,
        )

        self._silence_rules.append(rule)
        logger.info(f"添加靜音規則: {silence_id} (duration: {duration})")

        return silence_id

    def remove_silence(self, silence_id: str):
        """移除靜音規則"""
        self._silence_rules = [r for r in self._silence_rules if r.id != silence_id]
        logger.info(f"移除靜音規則: {silence_id}")

    def cleanup_expired_silences(self):
        """清理過期的靜音規則"""
        now = datetime.utcnow()
        before_count = len(self._silence_rules)
        self._silence_rules = [r for r in self._silence_rules if r.ends_at > now]
        after_count = len(self._silence_rules)

        if before_count != after_count:
            logger.info(f"清理了 {before_count - after_count} 個過期的靜音規則")

    # ========================================================================
    # 查詢
    # ========================================================================

    def get_active_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        source: Optional[str] = None,
    ) -> List[Alert]:
        """
        獲取活躍告警

        Args:
            severity: 過濾嚴重程度
            source: 過濾來源

        Returns:
            告警列表
        """
        alerts = list(self._active_alerts.values())

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        if source:
            alerts = [a for a in alerts if a.source == source]

        return sorted(alerts, key=lambda a: a.created_at, reverse=True)

    def get_alert_history(
        self,
        limit: int = 100,
        severity: Optional[AlertSeverity] = None,
    ) -> List[Alert]:
        """
        獲取告警歷史

        Args:
            limit: 數量限制
            severity: 過濾嚴重程度

        Returns:
            告警列表
        """
        alerts = self._alert_history

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return sorted(alerts, key=lambda a: a.created_at, reverse=True)[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """獲取統計信息"""
        return {
            **self._stats,
            "active_alerts": len(self._active_alerts),
            "history_size": len(self._alert_history),
            "rules_count": len(self._rules),
            "silence_rules_count": len(self._silence_rules),
            "channels_count": len(self._channels),
        }

    # ========================================================================
    # 背景任務
    # ========================================================================

    async def start_rule_evaluation(self, interval: float = 15.0):
        """啟動規則評估背景任務"""
        logger.info(f"啟動告警規則評估 (間隔: {interval}s)")

        while True:
            try:
                await self.evaluate_rules()
                self.cleanup_expired_silences()
            except Exception as e:
                logger.error(f"告警規則評估失敗: {e}")

            await asyncio.sleep(interval)


# ============================================================================
# 全局實例
# ============================================================================

_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """獲取全局告警管理器"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def configure_alert_manager(
    aggregation_window: float = 60.0,
    max_alerts_per_group: int = 100,
    history_retention: int = 1000,
) -> AlertManager:
    """配置全局告警管理器"""
    global _alert_manager
    _alert_manager = AlertManager(
        aggregation_window=aggregation_window,
        max_alerts_per_group=max_alerts_per_group,
        history_retention=history_retention,
    )
    return _alert_manager


# ============================================================================
# FastAPI 整合
# ============================================================================


def setup_alert_routes(app, alert_manager: Optional[AlertManager] = None):
    """
    設置告警管理路由

    Args:
        app: FastAPI 應用
        alert_manager: 告警管理器實例
    """
    from fastapi import HTTPException
    from pydantic import BaseModel
    from typing import Optional as Opt

    manager = alert_manager or get_alert_manager()

    class AlertCreate(BaseModel):
        name: str
        severity: str
        message: str
        source: str = "api"
        labels: Dict[str, str] = {}

    class AcknowledgeRequest(BaseModel):
        acknowledged_by: str
        comment: Opt[str] = None

    class SilenceCreate(BaseModel):
        matchers: Dict[str, str]
        duration_minutes: int
        created_by: str
        comment: Opt[str] = None

    @app.get("/alerts")
    async def list_alerts(severity: Opt[str] = None, source: Opt[str] = None):
        """獲取活躍告警"""
        sev = AlertSeverity(severity) if severity else None
        alerts = manager.get_active_alerts(severity=sev, source=source)
        return [a.to_dict() for a in alerts]

    @app.post("/alerts")
    async def create_alert(alert: AlertCreate):
        """創建告警"""
        try:
            severity = AlertSeverity(alert.severity)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"無效的嚴重程度: {alert.severity}")

        result = await manager.fire(
            name=alert.name,
            severity=severity,
            message=alert.message,
            source=alert.source,
            labels=alert.labels,
        )
        return result.to_dict()

    @app.post("/alerts/{alert_id}/acknowledge")
    async def acknowledge_alert(alert_id: str, request: AcknowledgeRequest):
        """確認告警"""
        await manager.acknowledge(
            alert_id=alert_id,
            acknowledged_by=request.acknowledged_by,
            comment=request.comment,
        )
        return {"message": "告警已確認"}

    @app.get("/alerts/history")
    async def get_history(limit: int = 100, severity: Opt[str] = None):
        """獲取告警歷史"""
        sev = AlertSeverity(severity) if severity else None
        alerts = manager.get_alert_history(limit=limit, severity=sev)
        return [a.to_dict() for a in alerts]

    @app.get("/alerts/stats")
    async def get_stats():
        """獲取告警統計"""
        return manager.get_stats()

    @app.post("/silences")
    async def create_silence(silence: SilenceCreate):
        """創建靜音規則"""
        silence_id = manager.add_silence(
            matchers=silence.matchers,
            duration=timedelta(minutes=silence.duration_minutes),
            created_by=silence.created_by,
            comment=silence.comment,
        )
        return {"id": silence_id, "message": "靜音規則已創建"}

    @app.delete("/silences/{silence_id}")
    async def delete_silence(silence_id: str):
        """刪除靜音規則"""
        manager.remove_silence(silence_id)
        return {"message": "靜音規則已刪除"}

    logger.info("告警管理路由已設置")
