# FastAPI 速率限制系統

基於 Redis 的分散式速率限制中間件，支援多種限制策略和靈活配置。

## 功能特性

### 1. 三種限制策略

#### 固定窗口 (Fixed Window)
- **特點**: 最簡單、效能最好
- **缺點**: 可能出現突刺（窗口邊界雙倍流量）
- **適用**: 一般 API 限制

```python
rate_limiter = RateLimiter(
    strategy="fixed_window",
    default_limit=60,
    default_window=60,
)
```

#### 滑動窗口 (Sliding Window) ⭐推薦
- **特點**: 平滑限流、精確控制、無突刺
- **要求**: 需要 Redis（存儲時間戳）
- **適用**: 需要精確控制的生產環境

```python
rate_limiter = RateLimiter(
    cache=redis_cache,
    strategy="sliding_window",
    default_limit=60,
    default_window=60,
)
```

#### 令牌桶 (Token Bucket)
- **特點**: 允許突發流量、長期平均速率受限
- **優勢**: 更符合實際使用場景
- **適用**: 需要彈性的場景

```python
rate_limiter = RateLimiter(
    strategy="token_bucket",
    default_limit=60,
    default_window=60,
)
```

### 2. 多種使用方式

#### 方式 1: 全域中間件
```python
from src.medical_chatbot.middleware import RateLimitMiddleware, RateLimiter

app = FastAPI()

rate_limiter = RateLimiter(...)
app.add_middleware(
    RateLimitMiddleware,
    rate_limiter=rate_limiter,
    limit=60,
    window=60,
    exclude_paths=["/health", "/docs"],
)
```

#### 方式 2: 裝飾器（單個端點）
```python
from src.medical_chatbot.middleware import rate_limit

@app.post("/chat")
@rate_limit(rate_limiter, limit=10, window=60)
async def chat(request: Request):
    return {"response": "..."}
```

### 3. 多種限制維度

#### 基於 IP
```python
# 預設方式
@rate_limit(rate_limiter, limit=60, window=60)
```

#### 基於 API Key
```python
def get_api_key_func(request: Request) -> str:
    return f"api_key:{request.headers.get('X-API-Key', 'anonymous')}"

@rate_limit(rate_limiter, limit=100, window=60, key_func=get_api_key_func)
```

#### 基於用戶 ID
```python
def get_user_id_func(request: Request) -> str:
    return f"user:{request.state.user_id}"

@rate_limit(rate_limiter, limit=200, window=60, key_func=get_user_id_func)
```

#### 組合鍵（IP + 路徑）
```python
from src.medical_chatbot.middleware import ip_path_key_func

@rate_limit(rate_limiter, limit=30, window=60, key_func=ip_path_key_func)
```

### 4. 自動降級

當 Redis 不可用時，自動降級為記憶體快取：

```python
rate_limiter = RateLimiter(
    cache=redis_cache,  # 主快取（分散式）
    fallback_cache=MemoryCache(),  # 降級快取（本地）
    strategy="sliding_window",
)
```

### 5. 響應標頭

所有請求都會返回以下標頭：

```
X-RateLimit-Limit: 60          # 限制次數
X-RateLimit-Remaining: 45      # 剩餘次數
X-RateLimit-Reset: 1234567890  # 重置時間戳
```

超限時額外返回：

```
Retry-After: 42                # 重試等待時間（秒）
```

### 6. 錯誤響應

超過限制時返回 `429 Too Many Requests`：

```json
{
  "error": "Rate limit exceeded",
  "message": "請求過於頻繁，請 42 秒後重試",
  "limit": 60,
  "retry_after": 42
}
```

## 使用範例

### 範例 1: 基礎配置

```python
from fastapi import FastAPI, Request
from src.medical_chatbot.cache import RedisCache, MemoryCache
from src.medical_chatbot.middleware import RateLimiter, RateLimitMiddleware

app = FastAPI()

# 創建 Redis 快取
redis_cache = RedisCache(host="localhost", port=6379)

# 創建速率限制器
rate_limiter = RateLimiter(
    cache=redis_cache,
    fallback_cache=MemoryCache(maxsize=10000, ttl=60),
    strategy="sliding_window",
    default_limit=60,
    default_window=60,
)

# 添加中間件
app.add_middleware(
    RateLimitMiddleware,
    rate_limiter=rate_limiter,
    limit=60,
    window=60,
    exclude_paths=["/health"],
)

@app.post("/chat")
async def chat(request: Request):
    return {"response": "..."}
```

### 範例 2: 不同端點不同限制

```python
@app.post("/public/chat")
@rate_limit(rate_limiter, limit=10, window=60)  # 嚴格
async def public_chat(request: Request):
    return {"response": "..."}

@app.post("/authenticated/chat")
@rate_limit(rate_limiter, limit=100, window=60)  # 寬鬆
async def authenticated_chat(request: Request):
    return {"response": "..."}
```

### 範例 3: 生產環境配置

```python
# 生產環境推薦配置
app = FastAPI()

redis_cache = RedisCache(
    host="redis.example.com",
    port=6379,
    password="your-password",
    max_connections=100,
)

rate_limiter = RateLimiter(
    cache=redis_cache,
    fallback_cache=MemoryCache(maxsize=10000, ttl=60),
    strategy="sliding_window",  # 滑動窗口
    default_limit=1000,  # 預設每分鐘 1000 次
    default_window=60,
)

# 全域基礎限制
app.add_middleware(
    RateLimitMiddleware,
    rate_limiter=rate_limiter,
    limit=1000,  # 防止 DDoS
    window=60,
    exclude_paths=["/health", "/metrics"],
)

# 公開端點
@app.post("/api/v1/chat")
@rate_limit(rate_limiter, limit=100, window=60)
async def chat(request: Request):
    pass

# 認證端點（更高配額）
@app.post("/api/v1/authenticated/chat")
@rate_limit(
    rate_limiter,
    limit=500,
    window=60,
    key_func=lambda r: f"api_key:{r.headers.get('X-API-Key')}"
)
async def authenticated_chat(request: Request):
    pass

# 昂貴操作（嚴格限制）
@app.post("/api/v1/generate")
@rate_limit(rate_limiter, limit=10, window=60)
async def generate(request: Request):
    pass
```

## 策略選擇指南

| 策略 | 效能 | 精確度 | 突發支援 | Redis | 推薦場景 |
|------|------|--------|----------|-------|----------|
| **固定窗口** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ | 可選 | 開發環境、一般限制 |
| **滑動窗口** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ | 必須 | 生產環境、精確控制 |
| **令牌桶** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ | 可選 | 需要彈性的場景 |

### 推薦配置

- **開發環境**: Fixed Window + Memory Cache
- **生產環境**: Sliding Window + Redis
- **彈性需求**: Token Bucket + Redis
- **無 Redis**: Fixed Window + Memory Cache

## 測試

### 測試正常請求

```bash
curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "你好"}'
```

### 測試速率限制

```bash
# 快速發送 100 個請求
for i in {1..100}; do
  curl -X POST http://localhost:8000/chat \
       -H "Content-Type: application/json" \
       -d '{"message": "test"}' &
done
```

### 查看響應標頭

```bash
curl -i -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "你好"}'
```

響應：

```
HTTP/1.1 200 OK
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1234567890
...
```

### 測試超限

```bash
# 超過限制後的響應
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1234567890
Retry-After: 42

{
  "error": "Rate limit exceeded",
  "message": "請求過於頻繁，請 42 秒後重試",
  "limit": 60,
  "retry_after": 42
}
```

## 進階用法

### 自訂鍵生成函數

```python
def custom_key_func(request: Request) -> str:
    # 組合多個因素
    ip = request.client.host
    api_key = request.headers.get("X-API-Key", "anonymous")
    path = request.url.path
    return f"{ip}:{api_key}:{path}"

@rate_limit(rate_limiter, key_func=custom_key_func)
```

### 動態限制

```python
def dynamic_key_func(request: Request) -> str:
    api_key = request.headers.get("X-API-Key")

    # 根據 API Key 類型返回不同前綴
    if api_key and api_key.startswith("premium-"):
        return f"premium:{api_key}"  # 高級用戶
    else:
        return f"free:{api_key or 'anonymous'}"  # 免費用戶

@rate_limit(
    rate_limiter,
    limit=100,  # 高級用戶可以有更高的限制
    window=60,
    key_func=dynamic_key_func
)
```

### 統計資訊

```python
# 獲取限制統計
stats = rate_limiter.get_stats("192.168.1.1")
print(stats)
# {
#   "key": "192.168.1.1",
#   "strategy": "sliding_window",
#   "current_count": 45
# }

# 重置限制
rate_limiter.reset("192.168.1.1")
```

## 效能優化

### 1. 使用 Redis Pipeline

滑動窗口策略內部已使用 Pipeline 優化：

```python
# 自動使用 Pipeline（內部實現）
pipe = redis.pipeline()
pipe.zremrangebyscore(...)
pipe.zcard(...)
pipe.zadd(...)
pipe.expire(...)
results = pipe.execute()
```

### 2. 連接池配置

```python
redis_cache = RedisCache(
    host="localhost",
    port=6379,
    max_connections=100,  # 調整連接池大小
    socket_timeout=5,
    socket_connect_timeout=5,
)
```

### 3. 記憶體快取優化

```python
memory_cache = MemoryCache(
    maxsize=10000,  # 調整快取大小
    ttl=60,
    cache_type="lru",  # 使用 LRU 策略
)
```

## 監控和日誌

### 日誌輸出

```
INFO  | 速率限制器初始化: strategy=sliding_window, limit=60/60s
INFO  | Redis 快取連接成功: localhost:6379/0
WARN  | 速率限制超限: key=192.168.1.1, count=61/60, retry_after=15s
```

### 監控指標

建議監控以下指標：

- 總請求數
- 被限制的請求數
- 不同策略的效能
- Redis 連接狀態

## 故障處理

### 容錯設計

速率限制器採用容錯設計：

1. **Redis 故障**: 自動降級為記憶體快取
2. **限制器錯誤**: 允許請求通過（可用性優先）
3. **鍵生成錯誤**: 使用降級鍵（如 "unknown"）

### 降級示例

```python
rate_limiter = RateLimiter(
    cache=redis_cache,  # 主快取
    fallback_cache=MemoryCache(),  # 降級快取
    strategy="sliding_window",
)

# Redis 故障時自動切換到記憶體快取
# 日誌: WARNING | Redis 連接失敗，使用降級策略
```

## 完整範例

查看 `01_basic_usage.py` 獲取完整的使用範例：

- 範例 1: 全域速率限制（中間件）
- 範例 2: 裝飾器方式（單個端點）
- 範例 3: 基於 API Key 的限制
- 範例 4: 多層限制（IP + 路徑）
- 範例 5: 策略比較
- 範例 6: 生產環境完整配置

## 常見問題

### Q: 如何為不同用戶設置不同限制？

A: 使用自訂鍵生成函數：

```python
def user_type_key(request: Request) -> str:
    user_type = request.state.user_type  # 從認證中間件獲取
    user_id = request.state.user_id

    # 根據用戶類型返回不同前綴
    return f"{user_type}:{user_id}"

# 然後在裝飾器中使用
@rate_limit(rate_limiter, limit=100, window=60, key_func=user_type_key)
```

### Q: 如何在多個服務器間共享限制？

A: 使用 Redis 作為共享快取：

```python
redis_cache = RedisCache(host="shared-redis.example.com")
rate_limiter = RateLimiter(cache=redis_cache, strategy="sliding_window")
```

### Q: 如何處理突發流量？

A: 使用令牌桶策略：

```python
rate_limiter = RateLimiter(
    strategy="token_bucket",  # 允許突發
    default_limit=100,
    default_window=60,
)
```

### Q: 如何查看當前限制狀態？

A: 使用 get_stats 方法：

```python
stats = rate_limiter.get_stats("user:123")
print(f"當前請求數: {stats['current_count']}")
```

## 授權

MIT License
