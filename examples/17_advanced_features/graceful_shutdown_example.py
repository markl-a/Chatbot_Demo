"""
優雅關閉示範

展示如何實現服務的優雅關閉功能。
"""

import asyncio
import signal
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn

from medical_chatbot.api import (
    GracefulShutdownManager,
    setup_graceful_shutdown,
    graceful_lifespan,
)


# ============================================================================
# 基本用法
# ============================================================================


def basic_example():
    """基本優雅關閉示範"""
    print("=" * 60)
    print("基本優雅關閉示範")
    print("=" * 60)

    app = FastAPI(title="優雅關閉示範")

    # 設置優雅關閉
    shutdown_manager = setup_graceful_shutdown(
        app,
        shutdown_timeout=30.0,  # 關閉超時
        drain_timeout=10.0,     # 排空超時
    )

    # 註冊清理回調
    @shutdown_manager.register_cleanup
    def cleanup_database():
        """清理資料庫連接"""
        print("  清理資料庫連接...")

    @shutdown_manager.register_cleanup
    async def cleanup_cache():
        """清理快取連接"""
        print("  清理快取連接...")
        await asyncio.sleep(0.5)

    @shutdown_manager.register_cleanup
    def cleanup_external_services():
        """清理外部服務連接"""
        print("  清理外部服務連接...")

    # 添加端點
    @app.get("/")
    async def root():
        return {"status": "running"}

    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "shutdown_state": shutdown_manager.state.value,
            "active_requests": shutdown_manager.active_requests,
        }

    print("""
應用已設置完成！

功能：
- 接收 SIGTERM/SIGINT 信號後觸發優雅關閉
- 停止接受新請求
- 等待現有請求完成
- 執行清理回調
- 最後關閉服務

端點：
- GET /shutdown/status - 查看關閉狀態
- GET /health - 健康檢查
""")

    return app


# ============================================================================
# 完整生命週期管理
# ============================================================================


def lifespan_example():
    """生命週期管理示範"""
    print("\n" + "=" * 60)
    print("生命週期管理示範")
    print("=" * 60)

    shutdown_manager = GracefulShutdownManager(
        shutdown_timeout=30.0,
        drain_timeout=10.0,
    )

    # 啟動回調
    async def on_startup():
        print("  應用啟動中...")
        print("  初始化資料庫連接...")
        print("  載入模型...")
        print("  啟動完成！")

    # 使用 lifespan 上下文管理器
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with graceful_lifespan(app, shutdown_manager, on_startup):
            yield

    app = FastAPI(title="生命週期示範", lifespan=lifespan)

    # 添加中間件
    from medical_chatbot.api.graceful_shutdown import GracefulShutdownMiddleware
    app.add_middleware(GracefulShutdownMiddleware, shutdown_manager=shutdown_manager)

    # 註冊清理任務
    shutdown_manager.register_cleanup("資料庫連接池", lambda: print("  關閉資料庫連接池"))
    shutdown_manager.register_cleanup("Redis 連接", lambda: print("  關閉 Redis 連接"))
    shutdown_manager.register_cleanup("WebSocket 連接", lambda: print("  關閉 WebSocket 連接"))

    @app.get("/")
    async def root():
        return {"status": "running"}

    print("""
應用已設置完成！

使用 lifespan 提供完整的生命週期管理：
- 啟動時執行初始化
- 關閉時執行清理
- 自動處理請求排空
""")

    return app


# ============================================================================
# 手動觸發關閉
# ============================================================================


async def manual_shutdown_example():
    """手動觸發關閉示範"""
    print("\n" + "=" * 60)
    print("手動觸發關閉示範")
    print("=" * 60)

    manager = GracefulShutdownManager(
        shutdown_timeout=10.0,
        drain_timeout=5.0,
    )

    # 註冊清理任務
    manager.register_cleanup("任務1", lambda: print("  執行清理任務 1"))
    manager.register_cleanup("任務2", lambda: print("  執行清理任務 2"))

    # 模擬活躍請求
    async def simulate_request():
        if await manager.track_request_start():
            print("  請求開始處理...")
            await asyncio.sleep(2)
            await manager.track_request_end()
            print("  請求處理完成")
        else:
            print("  請求被拒絕（服務正在關閉）")

    # 啟動模擬請求
    request_task = asyncio.create_task(simulate_request())

    # 稍後觸發關閉
    await asyncio.sleep(0.5)
    print("\n觸發關閉...")
    manager.trigger_shutdown(reason="manual_test")

    # 嘗試新請求（應該被拒絕）
    print("\n嘗試新請求...")
    await simulate_request()

    # 等待請求完成
    await request_task

    # 執行優雅關閉
    await manager.graceful_shutdown()

    # 顯示統計
    print("\n關閉統計:")
    stats = manager.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")


# ============================================================================
# 帶回調的關閉
# ============================================================================


async def callback_example():
    """回調示範"""
    print("\n" + "=" * 60)
    print("關閉回調示範")
    print("=" * 60)

    manager = GracefulShutdownManager()

    # 關閉前回調
    @manager.on_pre_shutdown
    def pre_shutdown():
        print("  [PRE] 準備關閉...")
        print("  [PRE] 停止接收新連接")
        print("  [PRE] 發送關閉通知給客戶端")

    @manager.on_pre_shutdown
    async def pre_shutdown_async():
        print("  [PRE] 異步準備工作...")
        await asyncio.sleep(0.2)

    # 關閉後回調
    @manager.on_post_shutdown
    def post_shutdown():
        print("  [POST] 關閉完成後的清理...")
        print("  [POST] 發送監控指標")
        print("  [POST] 記錄日誌")

    # 清理任務
    manager.register_cleanup("模型卸載", lambda: print("  [CLEANUP] 卸載 ML 模型"))
    manager.register_cleanup("連接池關閉", lambda: print("  [CLEANUP] 關閉連接池"))

    # 執行關閉
    manager.trigger_shutdown(reason="callback_test")
    await manager.graceful_shutdown()


# ============================================================================
# 主程序
# ============================================================================


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Medical Chatbot 優雅關閉示範")
    print("=" * 60 + "\n")

    # 基本示範
    app = basic_example()

    # 生命週期示範
    lifespan_app = lifespan_example()

    # 運行異步示範
    print("\n" + "=" * 60)
    print("運行異步示範...")
    print("=" * 60)
    asyncio.run(manual_shutdown_example())
    asyncio.run(callback_example())

    print("\n" + "=" * 60)
    print("示範完成！")
    print("=" * 60)
    print("""
要運行完整的 FastAPI 應用，請取消下面的註釋：
# uvicorn.run(app, host="0.0.0.0", port=8000)
""")
