"""
動態配置管理示範

展示如何使用動態配置管理功能。
"""

import asyncio
import os
import tempfile
import json
from pathlib import Path

from medical_chatbot.config import (
    DynamicConfigManager,
    ConfigSource,
    TypeValidator,
    RangeValidator,
    EnumValidator,
    get_config_manager,
    configure_config_manager,
)


# ============================================================================
# 基本用法
# ============================================================================


def basic_example():
    """基本配置管理示範"""
    print("=" * 60)
    print("基本配置管理示範")
    print("=" * 60)

    # 創建配置管理器
    config = DynamicConfigManager(env_prefix="APP_")

    # 設置默認值
    config.set_defaults({
        "database": {
            "host": "localhost",
            "port": 5432,
            "pool_size": 10,
        },
        "cache": {
            "enabled": True,
            "ttl": 3600,
        },
        "log_level": "INFO",
    })

    # 獲取配置
    print("\n配置值:")
    print(f"  database.host: {config.get('database.host')}")
    print(f"  database.port: {config.get_int('database.port')}")
    print(f"  cache.enabled: {config.get_bool('cache.enabled')}")
    print(f"  log_level: {config.get_str('log_level')}")

    # 運行時更新配置
    print("\n更新配置...")
    config.set("log_level", "DEBUG", source=ConfigSource.REMOTE)
    config.set("cache.ttl", 7200)

    print(f"  log_level: {config.get('log_level')}")
    print(f"  cache.ttl: {config.get_int('cache.ttl')}")

    # 獲取完整配置
    print("\n所有配置:")
    for key, value in config.get_all().items():
        print(f"  {key}: {value}")


# ============================================================================
# 從文件加載
# ============================================================================


def file_loading_example():
    """從文件加載配置示範"""
    print("\n" + "=" * 60)
    print("從文件加載配置示範")
    print("=" * 60)

    # 創建臨時配置文件
    config_data = {
        "server": {
            "host": "0.0.0.0",
            "port": 8000,
            "workers": 4,
        },
        "model": {
            "name": "medical-chatbot",
            "max_tokens": 512,
            "temperature": 0.7,
        },
        "features": {
            "rag_enabled": True,
            "streaming_enabled": True,
        },
    }

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        delete=False,
    ) as f:
        json.dump(config_data, f)
        config_file = f.name

    try:
        # 從文件加載配置
        config = DynamicConfigManager(
            config_file=config_file,
            auto_reload=False,
        )

        print("\n從文件加載的配置:")
        print(f"  server.host: {config.get('server.host')}")
        print(f"  server.port: {config.get_int('server.port')}")
        print(f"  model.name: {config.get('model.name')}")
        print(f"  model.temperature: {config.get_float('model.temperature')}")
        print(f"  features.rag_enabled: {config.get_bool('features.rag_enabled')}")

    finally:
        os.unlink(config_file)


# ============================================================================
# 配置驗證
# ============================================================================


def validation_example():
    """配置驗證示範"""
    print("\n" + "=" * 60)
    print("配置驗證示範")
    print("=" * 60)

    config = DynamicConfigManager()

    # 添加類型驗證器
    config.add_validator(TypeValidator({
        "port": int,
        "host": str,
        "enabled": bool,
    }))

    # 添加範圍驗證器
    config.add_validator(RangeValidator({
        "port": (1, 65535),
        "max_connections": (1, 1000),
        "temperature": (0.0, 2.0),
    }))

    # 添加枚舉驗證器
    config.add_validator(EnumValidator({
        "log_level": {"DEBUG", "INFO", "WARNING", "ERROR"},
        "environment": {"development", "staging", "production"},
    }))

    # 有效配置
    print("\n設置有效配置:")
    success = config.set("port", 8080)
    print(f"  port=8080: {'成功' if success else '失敗'}")

    success = config.set("log_level", "DEBUG")
    print(f"  log_level=DEBUG: {'成功' if success else '失敗'}")

    success = config.set("temperature", 0.7)
    print(f"  temperature=0.7: {'成功' if success else '失敗'}")

    # 無效配置
    print("\n設置無效配置:")
    success = config.set("port", 70000)  # 超出範圍
    print(f"  port=70000: {'成功' if success else '失敗（超出範圍）'}")

    success = config.set("port", "not_a_number")  # 類型錯誤
    print(f"  port='not_a_number': {'成功' if success else '失敗（類型錯誤）'}")

    success = config.set("log_level", "INVALID")  # 不在枚舉中
    print(f"  log_level=INVALID: {'成功' if success else '失敗（不在枚舉中）'}")


# ============================================================================
# 變更監聽
# ============================================================================


def change_listener_example():
    """變更監聽示範"""
    print("\n" + "=" * 60)
    print("變更監聽示範")
    print("=" * 60)

    config = DynamicConfigManager()

    # 全局變更監聽
    @config.on_change
    def on_any_change(change):
        print(f"  [全局] {change.key}: {change.old_value} -> {change.new_value}")

    # 特定鍵監聽
    @config.on_key_change("log_level")
    def on_log_level_change(key, old_value, new_value):
        print(f"  [日誌級別] 從 {old_value} 變更為 {new_value}")

    @config.on_key_change("max_connections")
    def on_max_connections_change(key, old_value, new_value):
        print(f"  [最大連接數] 從 {old_value} 變更為 {new_value}")
        # 這裡可以觸發連接池重新配置
        print("    -> 觸發連接池重新配置")

    print("\n更新配置觸發監聽器:")
    config.set("log_level", "DEBUG")
    config.set("log_level", "INFO")
    config.set("max_connections", 100)
    config.set("other_config", "value")


# ============================================================================
# 環境變量覆蓋
# ============================================================================


def environment_override_example():
    """環境變量覆蓋示範"""
    print("\n" + "=" * 60)
    print("環境變量覆蓋示範")
    print("=" * 60)

    # 設置環境變量
    os.environ["MYAPP_DATABASE_HOST"] = "production-db.example.com"
    os.environ["MYAPP_DATABASE_PORT"] = "5433"
    os.environ["MYAPP_DEBUG"] = "false"
    os.environ["MYAPP_FEATURES"] = '["feature1", "feature2"]'

    try:
        config = DynamicConfigManager(env_prefix="MYAPP_")

        # 設置默認值（會被環境變量覆蓋）
        config.set_defaults({
            "database_host": "localhost",
            "database_port": 5432,
            "debug": True,
        })

        print("\n配置（環境變量優先）:")
        print(f"  database_host: {config.get('database_host')}")
        print(f"  database_port: {config.get_int('database_port')}")
        print(f"  debug: {config.get_bool('debug')}")
        print(f"  features: {config.get_list('features')}")

        # 嘗試覆蓋環境變量設置（不會成功）
        config.set("database_host", "override-db.example.com")
        print(f"\n嘗試覆蓋後 database_host: {config.get('database_host')}")
        print("  （環境變量優先級最高，無法被覆蓋）")

    finally:
        # 清理環境變量
        del os.environ["MYAPP_DATABASE_HOST"]
        del os.environ["MYAPP_DATABASE_PORT"]
        del os.environ["MYAPP_DEBUG"]
        del os.environ["MYAPP_FEATURES"]


# ============================================================================
# 配置快照
# ============================================================================


def snapshot_example():
    """配置快照示範"""
    print("\n" + "=" * 60)
    print("配置快照示範")
    print("=" * 60)

    config = DynamicConfigManager()

    # 設置初始配置
    config.set("feature_a", True)
    config.set("feature_b", False)
    config.set("max_items", 100)

    print("\n初始配置:")
    for key, value in config.get_all().items():
        print(f"  {key}: {value}")

    # 創建快照
    snapshot = config.create_snapshot()
    print("\n已創建配置快照")

    # 修改配置
    config.set("feature_a", False)
    config.set("feature_b", True)
    config.set("max_items", 200)

    print("\n修改後配置:")
    for key, value in config.get_all().items():
        print(f"  {key}: {value}")

    # 恢復快照
    config.restore_snapshot(snapshot)

    print("\n恢復快照後:")
    for key, value in config.get_all().items():
        print(f"  {key}: {value}")


# ============================================================================
# 自動重載
# ============================================================================


async def auto_reload_example():
    """自動重載示範"""
    print("\n" + "=" * 60)
    print("自動重載示範")
    print("=" * 60)

    # 創建臨時配置文件
    config_data = {"version": 1, "setting": "initial"}

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        delete=False,
    ) as f:
        json.dump(config_data, f)
        config_file = f.name

    try:
        # 創建帶自動重載的配置管理器
        config = DynamicConfigManager(
            config_file=config_file,
            auto_reload=True,
            reload_interval=2.0,  # 2 秒檢查一次
        )

        # 監聽變更
        @config.on_change
        def on_change(change):
            print(f"  配置變更: {change.key} -> {change.new_value}")

        print(f"\n初始配置: version={config.get('version')}, setting={config.get('setting')}")

        # 啟動自動重載
        await config.start_auto_reload()

        print("\n模擬文件更新...")
        await asyncio.sleep(1)

        # 更新文件
        new_config = {"version": 2, "setting": "updated", "new_key": "new_value"}
        with open(config_file, "w") as f:
            json.dump(new_config, f)

        print("等待自動重載...")
        await asyncio.sleep(3)

        print(f"\n重載後配置: version={config.get('version')}, setting={config.get('setting')}")

        # 停止自動重載
        await config.stop_auto_reload()

    finally:
        os.unlink(config_file)


# ============================================================================
# FastAPI 整合
# ============================================================================


def fastapi_example():
    """FastAPI 整合示範"""
    print("\n" + "=" * 60)
    print("FastAPI 整合示範")
    print("=" * 60)

    from fastapi import FastAPI
    from medical_chatbot.config.dynamic_config import setup_config_routes

    app = FastAPI(title="動態配置示範")

    # 配置全局配置管理器
    config = configure_config_manager(
        auto_reload=False,
        env_prefix="APP_",
    )

    # 設置默認配置
    config.set_defaults({
        "api": {
            "rate_limit": 100,
            "timeout": 30,
        },
        "model": {
            "max_tokens": 512,
        },
    })

    # 設置配置路由
    setup_config_routes(app, config)

    print("""
應用已設置完成！

配置 API 端點：
- GET /config - 獲取所有配置
- GET /config/{key} - 獲取特定配置
- PUT /config/{key} - 更新配置
- DELETE /config/{key} - 刪除配置

使用示例：
curl http://localhost:8000/config
curl http://localhost:8000/config/api.rate_limit
curl -X PUT http://localhost:8000/config/api.rate_limit -d '{"value": 200}'
""")

    return app


# ============================================================================
# 主程序
# ============================================================================


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Medical Chatbot 動態配置管理示範")
    print("=" * 60 + "\n")

    basic_example()
    file_loading_example()
    validation_example()
    change_listener_example()
    environment_override_example()
    snapshot_example()

    # 運行異步示範
    asyncio.run(auto_reload_example())

    # FastAPI 整合
    app = fastapi_example()

    print("\n" + "=" * 60)
    print("示範完成！")
    print("=" * 60)
