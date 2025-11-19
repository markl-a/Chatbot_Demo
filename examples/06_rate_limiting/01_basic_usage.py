"""
速率限制基本使用範例

展示如何在 FastAPI 應用中使用速率限制中間件。
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.medical_chatbot.cache.redis_cache import RedisCache
from src.medical_chatbot.cache.memory_cache import MemoryCache
from src.medical_chatbot.middleware.rate_limiter import RateLimiter, RateLimitStrategy
from src.medical_chatbot.middleware.fastapi_middleware import (
    RateLimitMiddleware,
    rate_limit,
    get_api_key,
    ip_path_key_func,
)


# ============================================================================
# 範例 1: 全域速率限制（中間件）
# ============================================================================


def example_1_global_rate_limit():
    """全域速率限制（所有端點）"""
    print("\n" + "=" * 80)
    print("範例 1: 全域速率限制（中間件）")
    print("=" * 80)

    # 創建 FastAPI 應用
    app = FastAPI(title="醫療聊天機器人 API")

    # 創建 Redis 快取（生產環境推薦）
    try:
        cache = RedisCache(host="localhost", port=6379, db=0)
        print("✓ 使用 Redis 快取（分散式支援）")
    except Exception as e:
        # 降級為記憶體快取
        cache = None
        print(f"✗ Redis 連接失敗: {e}")
        print("✓ 降級為記憶體快取")

    # 創建速率限制器（滑動窗口策略）
    rate_limiter = RateLimiter(
        cache=cache,
        fallback_cache=MemoryCache(maxsize=10000, ttl=60),
        strategy="sliding_window",  # 推薦策略
        default_limit=60,  # 每分鐘 60 次
        default_window=60,  # 60 秒窗口
    )

    # 添加速率限制中間件
    app.add_middleware(
        RateLimitMiddleware,
        rate_limiter=rate_limiter,
        limit=60,  # 每分鐘 60 次
        window=60,  # 60 秒
        exclude_paths=["/health", "/docs", "/openapi.json"],  # 排除這些路徑
    )

    @app.get("/health")
    async def health_check():
        """健康檢查（不受限制）"""
        return {"status": "healthy"}

    @app.post("/chat")
    async def chat(request: Request):
        """聊天端點（受限制）"""
        data = await request.json()
        return {
            "message": "收到您的消息",
            "input": data.get("message"),
            "response": "這是模擬回覆",
        }

    print("""
使用說明:
1. 所有端點（除了 /health, /docs）都受到速率限制
2. 限制為每個 IP 每分鐘 60 次請求
3. 使用滑動窗口策略，平滑限流
4. 超過限制時返回 429 錯誤

測試命令:
    # 正常請求
    curl -X POST http://localhost:8000/chat \\
         -H "Content-Type: application/json" \\
         -d '{"message": "你好"}'

    # 快速發送多個請求（觸發限制）
    for i in {1..100}; do
        curl -X POST http://localhost:8000/chat \\
             -H "Content-Type: application/json" \\
             -d '{"message": "test"}' &
    done

啟動命令:
    uvicorn example_1_global_rate_limit:app --reload
    """)


# ============================================================================
# 範例 2: 裝飾器方式（單個端點）
# ============================================================================


def example_2_decorator_rate_limit():
    """裝飾器方式的速率限制"""
    print("\n" + "=" * 80)
    print("範例 2: 裝飾器方式（單個端點）")
    print("=" * 80)

    app = FastAPI(title="醫療聊天機器人 API")

    # 創建速率限制器
    rate_limiter = RateLimiter(
        fallback_cache=MemoryCache(maxsize=10000, ttl=60),
        strategy="fixed_window",
        default_limit=100,
        default_window=60,
    )

    @app.get("/")
    async def root():
        """首頁（不受限制）"""
        return {"message": "歡迎使用醫療聊天機器人 API"}

    @app.post("/chat")
    @rate_limit(rate_limiter, limit=10, window=60)  # 每分鐘 10 次
    async def chat(request: Request):
        """聊天端點（嚴格限制）"""
        data = await request.json()
        return {"response": f"收到消息: {data.get('message')}"}

    @app.post("/api/generate")
    @rate_limit(rate_limiter, limit=5, window=60)  # 每分鐘 5 次（更嚴格）
    async def generate(request: Request):
        """生成端點（非常嚴格的限制）"""
        data = await request.json()
        return {"generated": "這是生成的內容"}

    print("""
使用說明:
1. 不同端點可以設置不同的限制
2. /chat: 每分鐘 10 次
3. /api/generate: 每分鐘 5 次（更嚴格）
4. 使用固定窗口策略

響應標頭:
    X-RateLimit-Limit: 10          # 限制次數
    X-RateLimit-Remaining: 7       # 剩餘次數
    X-RateLimit-Reset: 1234567890  # 重置時間戳
    Retry-After: 42                # 重試等待時間（超限時）
    """)


# ============================================================================
# 範例 3: 基於 API Key 的限制
# ============================================================================


def example_3_api_key_rate_limit():
    """基於 API Key 的速率限制"""
    print("\n" + "=" * 80)
    print("範例 3: 基於 API Key 的速率限制")
    print("=" * 80)

    app = FastAPI(title="醫療聊天機器人 API")

    # 創建速率限制器
    rate_limiter = RateLimiter(
        fallback_cache=MemoryCache(maxsize=10000, ttl=60),
        strategy="token_bucket",
        default_limit=100,
        default_window=60,
    )

    # 自訂鍵生成函數
    def get_rate_limit_key(request: Request) -> str:
        """使用 API Key 作為限制鍵"""
        api_key = request.headers.get("X-API-Key", "anonymous")
        return f"api_key:{api_key}"

    @app.post("/api/chat")
    @rate_limit(rate_limiter, limit=100, window=60, key_func=get_rate_limit_key)
    async def api_chat(request: Request):
        """API 聊天端點（基於 API Key 限制）"""
        data = await request.json()
        api_key = request.headers.get("X-API-Key", "anonymous")

        return {
            "api_key": api_key,
            "message": data.get("message"),
            "response": "這是回覆",
        }

    print("""
使用說明:
1. 使用 API Key 而非 IP 進行限制
2. 不同的 API Key 有獨立的限制配額
3. 使用令牌桶策略，允許突發流量
4. 匿名用戶（無 API Key）共享同一配額

測試命令:
    # 使用 API Key 1
    curl -X POST http://localhost:8000/api/chat \\
         -H "X-API-Key: key-123" \\
         -H "Content-Type: application/json" \\
         -d '{"message": "你好"}'

    # 使用 API Key 2（獨立配額）
    curl -X POST http://localhost:8000/api/chat \\
         -H "X-API-Key: key-456" \\
         -H "Content-Type: application/json" \\
         -d '{"message": "你好"}'

    # 匿名用戶（共享配額）
    curl -X POST http://localhost:8000/api/chat \\
         -H "Content-Type: application/json" \\
         -d '{"message": "你好"}'
    """)


# ============================================================================
# 範例 4: 多層限制（IP + 路徑）
# ============================================================================


def example_4_multi_tier_rate_limit():
    """多層速率限制"""
    print("\n" + "=" * 80)
    print("範例 4: 多層速率限制（IP + 路徑）")
    print("=" * 80)

    app = FastAPI(title="醫療聊天機器人 API")

    # 創建速率限制器
    rate_limiter = RateLimiter(
        fallback_cache=MemoryCache(maxsize=10000, ttl=60),
        strategy="sliding_window",
        default_limit=60,
        default_window=60,
    )

    @app.post("/chat")
    @rate_limit(rate_limiter, limit=30, window=60, key_func=ip_path_key_func)
    async def chat(request: Request):
        """聊天端點（每個 IP 在此路徑每分鐘 30 次）"""
        return {"response": "聊天回覆"}

    @app.post("/search")
    @rate_limit(rate_limiter, limit=60, window=60, key_func=ip_path_key_func)
    async def search(request: Request):
        """搜尋端點（每個 IP 在此路徑每分鐘 60 次）"""
        return {"results": []}

    print("""
使用說明:
1. 不同路徑有獨立的限制配額
2. 同一個 IP 在 /chat 和 /search 有不同的限制
3. 使用 ip_path_key_func 生成組合鍵: "IP:PATH"

限制配置:
    - /chat: 每個 IP 每分鐘 30 次
    - /search: 每個 IP 每分鐘 60 次

組合鍵範例:
    192.168.1.1:/chat    → 限制 30/分鐘
    192.168.1.1:/search  → 限制 60/分鐘
    """)


# ============================================================================
# 範例 5: 自訂策略比較
# ============================================================================


def example_5_strategy_comparison():
    """比較不同的速率限制策略"""
    print("\n" + "=" * 80)
    print("範例 5: 速率限制策略比較")
    print("=" * 80)

    app = FastAPI(title="醫療聊天機器人 API")

    # 固定窗口策略
    fixed_limiter = RateLimiter(
        fallback_cache=MemoryCache(maxsize=1000, ttl=60),
        strategy="fixed_window",
        default_limit=10,
        default_window=60,
    )

    # 滑動窗口策略
    sliding_limiter = RateLimiter(
        fallback_cache=MemoryCache(maxsize=1000, ttl=60),
        strategy="sliding_window",
        default_limit=10,
        default_window=60,
    )

    # 令牌桶策略
    bucket_limiter = RateLimiter(
        fallback_cache=MemoryCache(maxsize=1000, ttl=60),
        strategy="token_bucket",
        default_limit=10,
        default_window=60,
    )

    @app.post("/test/fixed")
    @rate_limit(fixed_limiter, limit=10, window=60)
    async def test_fixed(request: Request):
        """固定窗口策略測試"""
        return {"strategy": "fixed_window"}

    @app.post("/test/sliding")
    @rate_limit(sliding_limiter, limit=10, window=60)
    async def test_sliding(request: Request):
        """滑動窗口策略測試"""
        return {"strategy": "sliding_window"}

    @app.post("/test/bucket")
    @rate_limit(bucket_limiter, limit=10, window=60)
    async def test_bucket(request: Request):
        """令牌桶策略測試"""
        return {"strategy": "token_bucket"}

    print("""
策略比較:

1. 固定窗口 (Fixed Window)
   - 最簡單、效能最好
   - 可能出現突刺（窗口邊界雙倍流量）
   - 適合：一般 API 限制

2. 滑動窗口 (Sliding Window)
   - 平滑限流，無突刺
   - 精確控制速率
   - 需要 Redis（存儲時間戳）
   - 適合：需要精確控制的場景

3. 令牌桶 (Token Bucket)
   - 允許突發流量
   - 長期平均速率受限
   - 更符合實際使用
   - 適合：需要彈性的場景

測試命令:
    # 測試固定窗口
    for i in {1..15}; do
        curl -X POST http://localhost:8000/test/fixed
    done

    # 測試滑動窗口
    for i in {1..15}; do
        curl -X POST http://localhost:8000/test/sliding
    done

    # 測試令牌桶
    for i in {1..15}; do
        curl -X POST http://localhost:8000/test/bucket
    done

推薦:
    - 生產環境: sliding_window + Redis
    - 開發環境: fixed_window + Memory Cache
    - 彈性需求: token_bucket
    """)


# ============================================================================
# 範例 6: 完整的生產環境配置
# ============================================================================


def example_6_production_config():
    """生產環境完整配置"""
    print("\n" + "=" * 80)
    print("範例 6: 生產環境完整配置")
    print("=" * 80)

    app = FastAPI(
        title="醫療聊天機器人 API",
        version="1.0.0",
        description="基於 TAIDE 的醫療問答系統",
    )

    # 創建 Redis 快取（生產環境）
    try:
        redis_cache = RedisCache(
            host="redis.example.com",  # 生產環境 Redis
            port=6379,
            db=0,
            password="your-redis-password",
            max_connections=100,
        )
        print("✓ Redis 快取連接成功")
    except Exception as e:
        redis_cache = None
        print(f"✗ Redis 連接失敗: {e}")

    # 創建速率限制器（滑動窗口 + Redis）
    rate_limiter = RateLimiter(
        cache=redis_cache,
        fallback_cache=MemoryCache(maxsize=10000, ttl=60),
        strategy="sliding_window",
        default_limit=1000,  # 預設每分鐘 1000 次
        default_window=60,
    )

    # 全域中間件（基礎限制）
    app.add_middleware(
        RateLimitMiddleware,
        rate_limiter=rate_limiter,
        limit=1000,  # 每個 IP 每分鐘 1000 次
        window=60,
        exclude_paths=[
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        ],
    )

    # 健康檢查（不受限制）
    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    # 公開端點（寬鬆限制）
    @app.post("/api/v1/chat")
    @rate_limit(rate_limiter, limit=100, window=60)
    async def public_chat(request: Request):
        """公開聊天端點"""
        return {"response": "公開回覆"}

    # 認證端點（基於 API Key，更高配額）
    @app.post("/api/v1/authenticated/chat")
    @rate_limit(
        rate_limiter,
        limit=500,  # 認證用戶有更高配額
        window=60,
        key_func=lambda r: f"api_key:{get_api_key(r)}",
    )
    async def authenticated_chat(request: Request):
        """認證聊天端點（需要 API Key）"""
        api_key = request.headers.get("X-API-Key")
        return {"api_key": api_key, "response": "認證回覆"}

    # 昂貴操作（非常嚴格的限制）
    @app.post("/api/v1/generate")
    @rate_limit(
        rate_limiter,
        limit=10,  # 每分鐘只允許 10 次
        window=60,
        key_func=lambda r: f"api_key:{get_api_key(r)}",
    )
    async def generate(request: Request):
        """生成端點（昂貴操作）"""
        return {"generated": "生成內容"}

    # 管理端點（非常嚴格）
    @app.post("/api/v1/admin/reset")
    @rate_limit(
        rate_limiter,
        limit=5,  # 每分鐘只允許 5 次
        window=60,
        key_func=lambda r: f"admin:{get_api_key(r)}",
    )
    async def admin_reset(request: Request):
        """管理端點"""
        return {"message": "重置成功"}

    print("""
生產環境配置:

1. 基礎設施
   - Redis: 分散式快取（多實例共享限制）
   - 策略: 滑動窗口（精確控制）
   - 降級: 記憶體快取（Redis 故障時）

2. 限制層級
   - 全域限制: 1000/分鐘（防止 DDoS）
   - 公開端點: 100/分鐘
   - 認證端點: 500/分鐘（更高配額）
   - 昂貴操作: 10/分鐘
   - 管理端點: 5/分鐘

3. 鍵策略
   - 公開端點: 基於 IP
   - 認證端點: 基於 API Key
   - 管理端點: 基於 API Key（獨立前綴）

4. 排除路徑
   - /health (健康檢查)
   - /metrics (監控指標)
   - /docs (API 文檔)

5. 響應標頭
   X-RateLimit-Limit: 限制次數
   X-RateLimit-Remaining: 剩餘次數
   X-RateLimit-Reset: 重置時間
   Retry-After: 重試等待時間

6. 錯誤處理
   - 429 Too Many Requests
   - 包含 retry_after 資訊
   - 容錯設計（限制器故障時允許請求）
    """)


# ============================================================================
# 主程序
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("FastAPI 速率限制使用範例")
    print("=" * 80)

    # 運行所有範例
    example_1_global_rate_limit()
    example_2_decorator_rate_limit()
    example_3_api_key_rate_limit()
    example_4_multi_tier_rate_limit()
    example_5_strategy_comparison()
    example_6_production_config()

    print("\n" + "=" * 80)
    print("範例說明完畢！")
    print("=" * 80)
    print("""
快速開始:

1. 啟動 Redis（可選，用於分散式限制）
   docker run -d -p 6379:6379 redis:alpine

2. 選擇一個範例啟動
   uvicorn 01_basic_usage:example_1_global_rate_limit --reload

3. 測試 API
   curl -X POST http://localhost:8000/chat \\
        -H "Content-Type: application/json" \\
        -d '{"message": "你好"}'

4. 查看響應標頭
   curl -i -X POST http://localhost:8000/chat \\
        -H "Content-Type: application/json" \\
        -d '{"message": "你好"}'

推薦配置:
    - 開發: Fixed Window + Memory Cache
    - 生產: Sliding Window + Redis
    - 彈性: Token Bucket
    """)
