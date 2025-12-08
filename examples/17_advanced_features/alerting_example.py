"""
告警系統示範

展示如何使用增強告警功能。
"""

import asyncio
from datetime import timedelta

from medical_chatbot.monitoring import (
    AlertManager,
    AlertSeverity,
    AlertRule,
    LogChannel,
    WebhookChannel,
    SlackChannel,
    CallbackChannel,
    get_alert_manager,
    configure_alert_manager,
)


# ============================================================================
# 基本用法
# ============================================================================


async def basic_example():
    """基本告警示範"""
    print("=" * 60)
    print("基本告警示範")
    print("=" * 60)

    # 創建告警管理器
    manager = AlertManager()

    # 觸發告警
    print("\n觸發告警:")

    alert1 = await manager.fire(
        name="高 CPU 使用率",
        severity=AlertSeverity.WARNING,
        message="CPU 使用率超過 80%",
        source="system_monitor",
        value=85.5,
        threshold=80.0,
        labels={"host": "server-01", "region": "asia"},
    )
    print(f"  告警 ID: {alert1.id}")

    alert2 = await manager.fire(
        name="資料庫連接失敗",
        severity=AlertSeverity.CRITICAL,
        message="無法連接到主資料庫",
        source="database_monitor",
        labels={"database": "primary", "host": "db-01"},
    )
    print(f"  告警 ID: {alert2.id}")

    # 查看活躍告警
    print("\n活躍告警:")
    for alert in manager.get_active_alerts():
        print(f"  [{alert.severity.value}] {alert.name}: {alert.message}")

    # 確認告警
    print("\n確認告警...")
    await manager.acknowledge(
        alert_id=alert1.id,
        acknowledged_by="admin",
        comment="正在調查中",
    )

    # 解除告警
    print("\n解除告警...")
    await manager.resolve(
        name="高 CPU 使用率",
        source="system_monitor",
        labels={"host": "server-01", "region": "asia"},
    )

    # 查看統計
    print("\n告警統計:")
    stats = manager.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")


# ============================================================================
# 多渠道通知
# ============================================================================


async def multi_channel_example():
    """多渠道通知示範"""
    print("\n" + "=" * 60)
    print("多渠道通知示範")
    print("=" * 60)

    manager = AlertManager()

    # 添加日誌渠道（默認已添加）
    # manager.add_channel(LogChannel())

    # 添加回調渠道
    async def custom_handler(alert):
        print(f"  [自定義處理] 收到告警: {alert.name}")
        # 這裡可以執行自定義邏輯，如：
        # - 發送到內部系統
        # - 觸發自動修復
        # - 更新狀態頁面
        return True

    manager.add_channel(CallbackChannel(custom_handler, name="custom"))

    # 添加 Webhook 渠道（示範用）
    # manager.add_channel(WebhookChannel(
    #     url="https://your-webhook-endpoint.com/alerts",
    #     headers={"Authorization": "Bearer your-token"},
    # ))

    # 添加 Slack 渠道（示範用）
    # manager.add_channel(SlackChannel(
    #     webhook_url="https://hooks.slack.com/services/xxx/xxx/xxx",
    #     channel="#alerts",
    # ))

    # 為特定嚴重程度設置渠道
    critical_callback = CallbackChannel(
        lambda alert: print(f"  [緊急] {alert.name} - 已通知值班人員"),
        name="critical_pager",
    )
    manager.add_channel(critical_callback, severities=[AlertSeverity.CRITICAL])

    print("\n觸發不同嚴重程度的告警:")

    await manager.fire(
        name="資訊告警",
        severity=AlertSeverity.INFO,
        message="系統正常運行",
        source="test",
    )

    await manager.fire(
        name="警告告警",
        severity=AlertSeverity.WARNING,
        message="記憶體使用率較高",
        source="test",
    )

    await manager.fire(
        name="緊急告警",
        severity=AlertSeverity.CRITICAL,
        message="服務不可用",
        source="test",
    )


# ============================================================================
# 告警規則
# ============================================================================


async def rule_example():
    """告警規則示範"""
    print("\n" + "=" * 60)
    print("告警規則示範")
    print("=" * 60)

    manager = AlertManager()

    # 模擬系統指標
    metrics = {
        "cpu_usage": 75.0,
        "memory_usage": 60.0,
        "error_rate": 0.01,
    }

    # 定義告警規則
    cpu_rule = AlertRule(
        name="高 CPU 使用率",
        condition=lambda: metrics["cpu_usage"] > 80,
        severity=AlertSeverity.WARNING,
        message_template="CPU 使用率過高",
        source="rule_engine",
        labels={"metric": "cpu"},
        for_duration=0,  # 立即觸發
        repeat_interval=60,  # 每分鐘最多重複一次
    )

    memory_rule = AlertRule(
        name="高記憶體使用率",
        condition=lambda: metrics["memory_usage"] > 85,
        severity=AlertSeverity.WARNING,
        message_template="記憶體使用率過高",
        source="rule_engine",
        labels={"metric": "memory"},
    )

    error_rule = AlertRule(
        name="高錯誤率",
        condition=lambda: metrics["error_rate"] > 0.05,
        severity=AlertSeverity.ERROR,
        message_template="錯誤率超過 5%",
        source="rule_engine",
        labels={"metric": "error_rate"},
    )

    # 添加規則
    manager.add_rule(cpu_rule)
    manager.add_rule(memory_rule)
    manager.add_rule(error_rule)

    print("\n初始指標:")
    print(f"  CPU: {metrics['cpu_usage']}%")
    print(f"  Memory: {metrics['memory_usage']}%")
    print(f"  Error Rate: {metrics['error_rate'] * 100}%")

    # 評估規則
    print("\n評估規則（初始狀態）:")
    await manager.evaluate_rules()

    # 更新指標
    print("\n更新指標（模擬問題）:")
    metrics["cpu_usage"] = 90.0
    metrics["error_rate"] = 0.08
    print(f"  CPU: {metrics['cpu_usage']}%")
    print(f"  Error Rate: {metrics['error_rate'] * 100}%")

    # 再次評估
    print("\n評估規則（問題狀態）:")
    await manager.evaluate_rules()

    # 查看活躍告警
    print("\n活躍告警:")
    for alert in manager.get_active_alerts():
        print(f"  [{alert.severity.value}] {alert.name}")

    # 修復問題
    print("\n修復問題...")
    metrics["cpu_usage"] = 50.0
    metrics["error_rate"] = 0.01

    # 評估並自動解除
    await manager.evaluate_rules()

    print("\n修復後活躍告警:")
    alerts = manager.get_active_alerts()
    print(f"  數量: {len(alerts)}")


# ============================================================================
# 告警靜音
# ============================================================================


async def silence_example():
    """告警靜音示範"""
    print("\n" + "=" * 60)
    print("告警靜音示範")
    print("=" * 60)

    manager = AlertManager()

    # 添加靜音規則
    silence_id = manager.add_silence(
        matchers={"severity": "warning", "source": "maintenance"},
        duration=timedelta(hours=1),
        created_by="admin",
        comment="計劃維護期間",
    )
    print(f"\n創建靜音規則: {silence_id}")

    # 觸發被靜音的告警
    print("\n觸發告警（匹配靜音規則）:")
    alert1 = await manager.fire(
        name="維護相關警告",
        severity=AlertSeverity.WARNING,
        message="預期的維護影響",
        source="maintenance",
    )
    print(f"  告警狀態: {alert1.state.value}")

    # 觸發不被靜音的告警
    print("\n觸發告警（不匹配靜音規則）:")
    alert2 = await manager.fire(
        name="真實警告",
        severity=AlertSeverity.WARNING,
        message="需要注意的問題",
        source="production",
    )
    print(f"  告警狀態: {alert2.state.value}")

    # 查看統計
    stats = manager.get_stats()
    print(f"\n靜音的告警數: {stats['silenced_alerts']}")

    # 移除靜音規則
    manager.remove_silence(silence_id)
    print(f"\n已移除靜音規則: {silence_id}")


# ============================================================================
# 告警去重
# ============================================================================


async def deduplication_example():
    """告警去重示範"""
    print("\n" + "=" * 60)
    print("告警去重示範")
    print("=" * 60)

    manager = AlertManager()

    # 多次觸發相同告警
    print("\n觸發相同告警多次:")
    for i in range(5):
        alert = await manager.fire(
            name="相同告警",
            severity=AlertSeverity.WARNING,
            message="重複發生的問題",
            source="test",
            labels={"instance": "server-01"},
        )
        print(f"  第 {i + 1} 次: fire_count = {alert.fire_count}")

    # 查看統計
    stats = manager.get_stats()
    print(f"\n去重的告警數: {stats['deduplicated_alerts']}")
    print(f"活躍告警數: {stats['active_alerts']}")


# ============================================================================
# FastAPI 整合
# ============================================================================


def fastapi_example():
    """FastAPI 整合示範"""
    print("\n" + "=" * 60)
    print("FastAPI 整合示範")
    print("=" * 60)

    from fastapi import FastAPI
    from medical_chatbot.monitoring.alerting import setup_alert_routes

    app = FastAPI(title="告警系統示範")

    # 配置告警管理器
    manager = configure_alert_manager(
        aggregation_window=60.0,
        history_retention=1000,
    )

    # 添加自定義渠道
    manager.add_channel(CallbackChannel(
        lambda alert: print(f"[ALERT] {alert.name}"),
        name="console",
    ))

    # 設置路由
    setup_alert_routes(app, manager)

    print("""
應用已設置完成！

告警 API 端點：
- GET /alerts - 獲取活躍告警
- POST /alerts - 創建告警
- POST /alerts/{id}/acknowledge - 確認告警
- GET /alerts/history - 獲取告警歷史
- GET /alerts/stats - 獲取統計信息
- POST /silences - 創建靜音規則
- DELETE /silences/{id} - 刪除靜音規則

使用示例：
curl http://localhost:8000/alerts
curl -X POST http://localhost:8000/alerts -d '{"name": "test", "severity": "warning", "message": "test alert"}'
""")

    return app


# ============================================================================
# 背景規則評估
# ============================================================================


async def background_evaluation_example():
    """背景規則評估示範"""
    print("\n" + "=" * 60)
    print("背景規則評估示範")
    print("=" * 60)

    manager = AlertManager()

    # 模擬變化的指標
    current_value = [50]  # 使用列表以便在閉包中修改

    rule = AlertRule(
        name="動態指標監控",
        condition=lambda: current_value[0] > 80,
        severity=AlertSeverity.WARNING,
        message_template="指標超過閾值",
        source="dynamic_monitor",
    )

    manager.add_rule(rule)

    print("\n模擬指標變化（5 秒內）:")

    async def simulate_metrics():
        """模擬指標變化"""
        values = [50, 70, 85, 90, 60]
        for v in values:
            current_value[0] = v
            print(f"  當前值: {v}")
            await asyncio.sleep(1)

    async def evaluate_rules():
        """定期評估規則"""
        for _ in range(5):
            await manager.evaluate_rules()
            await asyncio.sleep(1)

    # 並行運行
    await asyncio.gather(simulate_metrics(), evaluate_rules())

    print("\n最終活躍告警:")
    for alert in manager.get_active_alerts():
        print(f"  {alert.name}: {alert.state.value}")


# ============================================================================
# 主程序
# ============================================================================


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Medical Chatbot 告警系統示範")
    print("=" * 60 + "\n")

    async def main():
        await basic_example()
        await multi_channel_example()
        await rule_example()
        await silence_example()
        await deduplication_example()
        await background_evaluation_example()

    asyncio.run(main())

    # FastAPI 整合
    app = fastapi_example()

    print("\n" + "=" * 60)
    print("示範完成！")
    print("=" * 60)
