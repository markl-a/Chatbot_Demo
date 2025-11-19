"""
FastAPI 配置整合範例

展示如何在 FastAPI 應用中整合配置管理。
"""
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, Depends
from pydantic import BaseModel

from src.medical_chatbot.config import (
    Settings,
    get_settings,
    setup_config_integration,
    get_database_url,
    get_redis_config,
    get_model_config,
    require_debug_mode,
)


# ============================================================================
# 範例 1: 基本整合
# ============================================================================


def example_1_basic_integration():
    """基本 FastAPI 整合"""
    print("\n" + "=" * 80)
    print("範例 1: 基本 FastAPI 整合")
    print("=" * 80)

    # 創建應用
    app = FastAPI()

    # 設置配置整合
    setup_config_integration(app)

    # 使用配置的端點
    @app.get("/")
    async def root(settings: Settings = Depends(get_settings)):
        return {
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        }

    @app.get("/info")
    async def info(settings: Settings = Depends(get_settings)):
        return {
            "app": {
                "name": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "environment": settings.ENVIRONMENT,
            },
            "model": {
                "name": settings.MODEL_NAME,
                "device": settings.DEVICE,
            },
        }

    print(f"\n應用已創建")
    print(f"  端點: /")
    print(f"  端點: /info")
    print(f"  配置端點: /config/*")
    print(f"\n啟動: uvicorn example_1_basic_integration:app --reload")

    return app


# ============================================================================
# 範例 2: 配置依賴注入
# ============================================================================


def example_2_dependency_injection():
    """配置依賴注入"""
    print("\n" + "=" * 80)
    print("範例 2: 配置依賴注入")
    print("=" * 80)

    app = FastAPI()
    setup_config_integration(app, include_routes=False)

    # 使用資料庫 URL 依賴
    @app.get("/database/url")
    async def get_db_url(url: str = Depends(get_database_url)):
        # 隱藏密碼
        if "@" in url:
            parts = url.split("@")
            if ":" in parts[0]:
                protocol_user = parts[0].rsplit(":", 1)[0]
                url = f"{protocol_user}:***@{parts[1]}"
        return {"database_url": url}

    # 使用 Redis 配置依賴
    @app.get("/redis/config")
    async def get_redis_conf(config: dict = Depends(get_redis_config)):
        # 隱藏密碼
        if config.get("password"):
            config["password"] = "***"
        return config

    # 使用模型配置依賴
    @app.get("/model/config")
    async def get_model_conf(config: dict = Depends(get_model_config)):
        return config

    print(f"\n依賴注入端點:")
    print(f"  GET /database/url")
    print(f"  GET /redis/config")
    print(f"  GET /model/config")

    return app


# ============================================================================
# 範例 3: 環境特定端點
# ============================================================================


def example_3_environment_specific():
    """環境特定端點"""
    print("\n" + "=" * 80)
    print("範例 3: 環境特定端點")
    print("=" * 80)

    app = FastAPI()
    setup_config_integration(app, include_routes=False)

    # 調試專用端點
    @app.get("/debug/config", dependencies=[Depends(require_debug_mode)])
    async def debug_config(settings: Settings = Depends(get_settings)):
        """僅在調試模式可用"""
        return {
            "all_settings": settings.dict(),
        }

    # 健康檢查（所有環境）
    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    # 詳細健康檢查（僅調試模式）
    @app.get("/health/detailed", dependencies=[Depends(require_debug_mode)])
    async def detailed_health(settings: Settings = Depends(get_settings)):
        return {
            "status": "healthy",
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "database": settings.DATABASE_URL,
        }

    print(f"\n環境特定端點:")
    print(f"  GET /health (所有環境)")
    print(f"  GET /health/detailed (僅調試模式)")
    print(f"  GET /debug/config (僅調試模式)")

    return app


# ============================================================================
# 範例 4: 配置驅動的功能
# ============================================================================


def example_4_config_driven_features():
    """配置驅動的功能"""
    print("\n" + "=" * 80)
    print("範例 4: 配置驅動的功能")
    print("=" * 80)

    app = FastAPI()
    setup_config_integration(app, include_routes=False)

    class ChatRequest(BaseModel):
        message: str
        max_length: int = None
        temperature: float = None

    @app.post("/chat")
    async def chat(
        request: ChatRequest,
        settings: Settings = Depends(get_settings),
    ):
        """聊天端點，使用配置的預設值"""

        # 使用配置的預設值
        max_length = request.max_length or settings.MAX_LENGTH
        temperature = request.temperature or settings.TEMPERATURE

        # 檢查限制
        if max_length > settings.MAX_LENGTH:
            max_length = settings.MAX_LENGTH

        return {
            "message": request.message,
            "config": {
                "max_length": max_length,
                "temperature": temperature,
                "model": settings.MODEL_NAME,
                "device": settings.DEVICE,
            },
            "response": f"處理消息: {request.message}",
        }

    @app.get("/limits")
    async def get_limits(settings: Settings = Depends(get_settings)):
        """獲取配置的限制"""
        return {
            "max_length": settings.MAX_LENGTH,
            "max_temperature": 2.0,
            "min_temperature": 0.0,
            "batch_size": settings.BATCH_SIZE,
            "rate_limit": settings.RATE_LIMIT_DEFAULT,
        }

    print(f"\n配置驅動的端點:")
    print(f"  POST /chat")
    print(f"  GET /limits")

    return app


# ============================================================================
# 範例 5: 動態配置更新
# ============================================================================


def example_5_dynamic_reload():
    """動態配置重新加載"""
    print("\n" + "=" * 80)
    print("範例 5: 動態配置重新加載")
    print("=" * 80)

    app = FastAPI()
    setup_config_integration(app, include_routes=True)

    # 配置路由已經包含 /config/reload 端點

    print(f"\n動態配置端點:")
    print(f"  POST /config/reload (僅調試模式)")
    print(f"\n使用:")
    print(f"  1. 修改 .env 檔案")
    print(f"  2. 調用 POST /config/reload")
    print(f"  3. 配置將重新加載（僅在調試模式）")

    return app


# ============================================================================
# 範例 6: 完整應用範例
# ============================================================================


def example_6_complete_app():
    """完整應用範例"""
    print("\n" + "=" * 80)
    print("範例 6: 完整應用範例")
    print("=" * 80)

    # 創建應用
    app = FastAPI(
        title="醫療聊天機器人 API",
        description="基於 TAIDE 的醫療問答系統",
        version="1.0.0",
    )

    # 設置配置整合（包含所有配置端點）
    setup_config_integration(app, include_routes=True)

    # 業務端點
    class ChatRequest(BaseModel):
        message: str

    class ChatResponse(BaseModel):
        response: str
        model: str
        generation_time: float

    @app.post("/api/v1/chat", response_model=ChatResponse)
    async def chat(
        request: ChatRequest,
        settings: Settings = Depends(get_settings),
    ):
        """聊天對話"""
        return ChatResponse(
            response=f"回覆: {request.message}",
            model=settings.MODEL_NAME,
            generation_time=0.5,
        )

    @app.get("/api/v1/models")
    async def list_models(settings: Settings = Depends(get_settings)):
        """列出可用模型"""
        return {
            "current_model": settings.MODEL_NAME,
            "available_models": [
                "TAIDE-LX-8B",
                "Breeze-7B",
                "Taiwan-LLM-7B",
            ],
        }

    print(f"\n完整應用端點:")
    print(f"\n業務端點:")
    print(f"  POST /api/v1/chat")
    print(f"  GET  /api/v1/models")
    print(f"\n配置端點:")
    print(f"  GET  /config/info")
    print(f"  GET  /config/database")
    print(f"  GET  /config/redis")
    print(f"  GET  /config/model")
    print(f"  POST /config/reload (調試模式)")

    print(f"\n啟動應用:")
    print(f"  uvicorn example_6_complete_app:app --reload")
    print(f"\n訪問:")
    print(f"  http://localhost:8000/docs - API 文檔")
    print(f"  http://localhost:8000/config/info - 配置資訊")

    return app


# ============================================================================
# 主程序
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("FastAPI 配置整合範例")
    print("=" * 80)

    # 運行範例
    app1 = example_1_basic_integration()
    app2 = example_2_dependency_injection()
    app3 = example_3_environment_specific()
    app4 = example_4_config_driven_features()
    app5 = example_5_dynamic_reload()
    app = example_6_complete_app()

    print("\n" + "=" * 80)
    print("範例完成！")
    print("=" * 80)
    print("""
主要功能:

1. 配置整合
   - setup_config_integration() 一鍵設置
   - 自動註冊配置端點
   - 啟動/關閉事件

2. 依賴注入
   - get_settings() 獲取配置單例
   - get_database_url() 獲取資料庫 URL
   - get_redis_config() 獲取 Redis 配置
   - get_model_config() 獲取模型配置

3. 訪問控制
   - require_debug_mode() 僅調試模式
   - require_production_mode() 僅生產模式
   - require_testing_enabled() 僅測試模式

4. 配置端點
   - GET /config/info - 應用資訊
   - GET /config/database - 資料庫配置
   - GET /config/redis - Redis 配置
   - GET /config/model - 模型配置
   - POST /config/reload - 重新加載配置

5. 最佳實踐
   - 配置單例（lru_cache）
   - 敏感資訊隱藏
   - 環境特定功能
   - 配置驗證

啟動範例:
    # 基本範例
    uvicorn 02_fastapi_config:example_1_basic_integration --reload

    # 完整範例
    uvicorn 02_fastapi_config:example_6_complete_app --reload

環境變數:
    # 設置環境
    export ENVIRONMENT=development
    export DEBUG=true

    # 或使用 .env 檔案
    echo "ENVIRONMENT=development" > .env
    echo "DEBUG=true" >> .env
    """)
