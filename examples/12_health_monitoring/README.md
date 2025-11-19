# 健康檢查系統

完整的健康檢查解決方案，支援組件監控、Kubernetes 整合和自訂檢查。

## 功能特性

### 1. 組件健康檢查
- ✅ 資料庫連接檢查
- ✅ Redis 連接檢查
- ✅ 模型狀態檢查
- ✅ 磁碟空間監控
- ✅ 記憶體使用監控

### 2. 健康狀態
- ✅ HEALTHY - 組件正常運行
- ✅ DEGRADED - 組件降級但可用
- ✅ UNHEALTHY - 組件不健康

### 3. 檢查模式
- ✅ 同步檢查
- ✅ 異步並行檢查
- ✅ 單個組件檢查
- ✅ 全部組件檢查

### 4. FastAPI 整合
- ✅ 健康檢查端點
- ✅ Kubernetes 探針
- ✅ 監控整合
- ✅ 可視化儀表板

## 快速開始

### 基本使用

```python
from src.medical_chatbot.health import HealthChecker

# 創建健康檢查器
health_checker = HealthChecker()

# 檢查所有組件
results = health_checker.check_all()

# 生成健康報告
report = health_checker.get_health_report()
print(report)
```

### FastAPI 整合

```python
from fastapi import FastAPI
from src.medical_chatbot.health import HealthChecker, setup_health_routes

app = FastAPI()

# 創建健康檢查器
health_checker = HealthChecker()

# 設置健康檢查路由
setup_health_routes(app, health_checker)
```

啟動後訪問:
- http://localhost:8000/health - 基本檢查
- http://localhost:8000/health/detailed - 詳細報告
- http://localhost:8000/health/ready - 就緒檢查

## 組件檢查

### 資料庫檢查

檢查資料庫連接、連接池狀態：

```python
from src.medical_chatbot.database import DatabaseManager
from src.medical_chatbot.health import HealthChecker

db_manager = DatabaseManager("sqlite:///./test.db")
health_checker = HealthChecker(database_manager=db_manager)

# 檢查資料庫
db_status = health_checker.check_database()
print(db_status.status)  # HEALTHY/DEGRADED/UNHEALTHY
print(db_status.message)  # 狀態訊息
print(db_status.details)  # 詳細資訊
```

返回資訊：
```json
{
  "name": "database",
  "status": "healthy",
  "message": "資料庫連接正常",
  "response_time": 0.05,
  "details": {
    "url": "localhost/medical_chatbot",
    "pool_size": 5,
    "checked_out": 2
  }
}
```

### Redis 檢查

檢查 Redis 連接、記憶體使用：

```python
from src.medical_chatbot.cache import RedisCache
from src.medical_chatbot.health import HealthChecker

redis_cache = RedisCache(host="localhost", port=6379)
health_checker = HealthChecker(redis_cache=redis_cache)

# 檢查 Redis
redis_status = health_checker.check_redis()
```

返回資訊：
```json
{
  "name": "redis",
  "status": "healthy",
  "message": "Redis 連接正常",
  "response_time": 0.01,
  "details": {
    "version": "7.0.0",
    "used_memory": "2.5M",
    "connected_clients": 10,
    "uptime_days": 30
  }
}
```

### 模型檢查

檢查模型加載狀態和生成能力：

```python
from src.medical_chatbot.model import ModelGenerator
from src.medical_chatbot.health import HealthChecker

model = ModelGenerator()
health_checker = HealthChecker(model_generator=model)

# 檢查模型
model_status = health_checker.check_model()
```

返回資訊：
```json
{
  "name": "model",
  "status": "healthy",
  "message": "模型運行正常",
  "response_time": 0.5,
  "details": {
    "model_name": "TAIDE-LX-8B",
    "device": "cuda"
  }
}
```

### 磁碟空間檢查

監控磁碟空間使用：

```python
health_checker = HealthChecker()

# 檢查磁碟空間
disk_status = health_checker.check_disk_space()
```

返回資訊：
```json
{
  "name": "disk",
  "status": "healthy",
  "message": "磁碟空間正常: 65.5%",
  "details": {
    "total": "500.00 GB",
    "used": "327.50 GB",
    "free": "172.50 GB",
    "percent": "65.5%"
  }
}
```

狀態判斷：
- 使用率 < 80%: HEALTHY
- 使用率 80-90%: DEGRADED
- 使用率 > 90%: UNHEALTHY

### 記憶體檢查

監控記憶體使用：

```python
health_checker = HealthChecker()

# 檢查記憶體
memory_status = health_checker.check_memory()
```

返回資訊：
```json
{
  "name": "memory",
  "status": "healthy",
  "message": "記憶體使用正常: 45.2%",
  "details": {
    "total": "16.00 GB",
    "available": "8.77 GB",
    "used": "7.23 GB",
    "percent": "45.2%"
  }
}
```

**注意**: 需要安裝 `psutil`:
```bash
pip install psutil
```

## 健康檢查端點

### 基本端點

#### GET /health

基本健康檢查：

```bash
curl http://localhost:8000/health
```

回覆：
```json
{
  "status": "healthy",
  "message": "服務運行正常"
}
```

#### GET /health/ping

Ping 端點（負載均衡器檢查）：

```bash
curl http://localhost:8000/health/ping
```

回覆：
```json
{
  "message": "pong"
}
```

#### GET /health/detailed

詳細健康報告：

```bash
curl http://localhost:8000/health/detailed
```

回覆：
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "checks": {
    "database": {
      "name": "database",
      "status": "healthy",
      "message": "資料庫連接正常",
      "response_time": 0.05,
      "details": {...}
    },
    "redis": {...},
    "model": {...},
    "disk": {...},
    "memory": {...}
  },
  "summary": {
    "total_checks": 5,
    "healthy": 5,
    "degraded": 0,
    "unhealthy": 0
  },
  "response_time": 0.6
}
```

#### GET /health/summary

快速摘要：

```bash
curl http://localhost:8000/health/summary
```

回覆：
```json
{
  "status": "healthy",
  "summary": {
    "total": 5,
    "healthy": 5,
    "degraded": 0,
    "unhealthy": 0
  }
}
```

### Kubernetes 端點

#### GET /health/ready

就緒檢查（Readiness Probe）：

檢查關鍵組件是否就緒。如果不健康返回 503。

```bash
curl http://localhost:8000/health/ready
```

成功回覆（200）：
```json
{
  "ready": true,
  "message": "服務已就緒"
}
```

失敗回覆（503）：
```json
{
  "ready": false,
  "message": "服務未就緒: database, redis",
  "unhealthy_components": ["database", "redis"]
}
```

#### GET /health/live

存活檢查（Liveness Probe）：

輕量級檢查，不檢查外部依賴。

```bash
curl http://localhost:8000/health/live
```

回覆：
```json
{
  "alive": true,
  "message": "服務存活"
}
```

#### GET /healthz

Kubernetes Liveness Probe：

```bash
curl http://localhost:8000/healthz
```

#### GET /readyz

Kubernetes Readiness Probe：

```bash
curl http://localhost:8000/readyz
```

### 組件端點

#### GET /health/component/{component_name}

檢查特定組件：

```bash
# 檢查資料庫
curl http://localhost:8000/health/component/database

# 檢查 Redis
curl http://localhost:8000/health/component/redis

# 檢查模型
curl http://localhost:8000/health/component/model
```

#### GET /health/components

列出所有組件：

```bash
curl http://localhost:8000/health/components
```

回覆：
```json
{
  "components": ["database", "redis", "model", "disk", "memory"],
  "total": 5
}
```

## Kubernetes 整合

### Pod 配置

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: medical-chatbot
spec:
  containers:
  - name: api
    image: medical-chatbot:latest
    ports:
    - containerPort: 8000

    # 存活探針
    livenessProbe:
      httpGet:
        path: /healthz
        port: 8000
      initialDelaySeconds: 30
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3

    # 就緒探針
    readinessProbe:
      httpGet:
        path: /readyz
        port: 8000
      initialDelaySeconds: 5
      periodSeconds: 5
      timeoutSeconds: 3
      successThreshold: 1
      failureThreshold: 3
```

### Deployment 配置

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: medical-chatbot
spec:
  replicas: 3
  selector:
    matchLabels:
      app: medical-chatbot
  template:
    metadata:
      labels:
        app: medical-chatbot
    spec:
      containers:
      - name: api
        image: medical-chatbot:latest
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Service 配置

```yaml
apiVersion: v1
kind: Service
metadata:
  name: medical-chatbot
spec:
  selector:
    app: medical-chatbot
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer

  # 健康檢查
  healthCheckNodePort: 30000
```

## 自訂健康檢查

### 註冊自訂檢查

```python
from src.medical_chatbot.health import HealthChecker, ComponentStatus, HealthStatus
import time

health_checker = HealthChecker()

def check_external_api() -> ComponentStatus:
    """檢查外部 API"""
    try:
        import requests

        start_time = time.time()
        response = requests.get("https://api.example.com/health", timeout=5)
        response_time = time.time() - start_time

        if response.status_code == 200:
            return ComponentStatus(
                name="external_api",
                status=HealthStatus.HEALTHY,
                message="外部 API 正常",
                response_time=response_time,
            )
        else:
            return ComponentStatus(
                name="external_api",
                status=HealthStatus.DEGRADED,
                message=f"外部 API 回應異常: {response.status_code}",
            )
    except Exception as e:
        return ComponentStatus(
            name="external_api",
            status=HealthStatus.UNHEALTHY,
            message=f"外部 API 檢查失敗: {str(e)}",
        )

# 註冊檢查
health_checker.register_check("external_api", check_external_api)

# 執行檢查
status = health_checker.check_component("external_api")
```

### 取消註冊檢查

```python
health_checker.unregister_check("external_api")
```

## 異步健康檢查

### 異步檢查所有組件

使用異步方式並行檢查，速度更快：

```python
import asyncio

async def check_health():
    health_checker = HealthChecker()

    # 異步檢查所有組件
    results = await health_checker.check_all_async()

    for name, status in results.items():
        print(f"{name}: {status.status.value}")

asyncio.run(check_health())
```

### 異步健康報告

```python
async def get_report():
    health_checker = HealthChecker()

    # 異步生成報告
    report = await health_checker.get_health_report_async()

    print(f"狀態: {report['status']}")
    print(f"時間: {report['response_time']:.4f}s")

asyncio.run(get_report())
```

## 監控整合

### Prometheus

生成 Prometheus 格式的指標：

```python
from fastapi import FastAPI

app = FastAPI()
health_checker = HealthChecker()

@app.get("/metrics")
async def metrics():
    report = health_checker.get_health_report()

    # 生成 Prometheus 指標
    metrics_lines = []

    # 整體健康狀態
    status_value = {"healthy": 1, "degraded": 0.5, "unhealthy": 0}
    overall = status_value.get(report["status"], 0)

    metrics_lines.append(f"# HELP health_status Overall health status")
    metrics_lines.append(f"# TYPE health_status gauge")
    metrics_lines.append(f'health_status{{service="medical_chatbot"}} {overall}')

    # 組件健康狀態
    metrics_lines.append(f"\n# HELP component_health Component health status")
    metrics_lines.append(f"# TYPE component_health gauge")

    for name, check in report["checks"].items():
        value = status_value.get(check["status"], 0)
        metrics_lines.append(f'component_health{{component="{name}"}} {value}')

    return "\n".join(metrics_lines)
```

Prometheus 配置：

```yaml
scrape_configs:
  - job_name: 'medical-chatbot'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### Grafana 儀表板

使用 Prometheus 指標創建 Grafana 儀表板：

```json
{
  "dashboard": {
    "title": "醫療聊天機器人健康監控",
    "panels": [
      {
        "title": "整體健康狀態",
        "targets": [
          {
            "expr": "health_status"
          }
        ]
      },
      {
        "title": "組件健康狀態",
        "targets": [
          {
            "expr": "component_health"
          }
        ]
      }
    ]
  }
}
```

## 健康檢查儀表板

### HTML 儀表板

創建可視化儀表板：

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()
health_checker = HealthChecker()

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    report = health_checker.get_health_report()

    # 生成 HTML（見範例程式碼）
    return html
```

訪問: http://localhost:8000/dashboard

特性：
- 實時狀態顯示
- 顏色編碼（綠/黃/紅）
- 自動重新整理
- 詳細組件資訊

## 最佳實踐

### 1. 定期健康檢查

```python
import schedule
import time

def periodic_health_check():
    health_checker = HealthChecker()
    report = health_checker.get_health_report()

    if report["status"] != "healthy":
        # 發送告警
        send_alert(report)

# 每分鐘檢查一次
schedule.every(1).minute.do(periodic_health_check)

while True:
    schedule.run_pending()
    time.sleep(1)
```

### 2. 告警整合

```python
def send_alert(report):
    """發送健康告警"""
    unhealthy = [
        name for name, check in report["checks"].items()
        if check["status"] == "unhealthy"
    ]

    if unhealthy:
        # 發送到 Slack
        send_slack_notification(
            f"⚠️ 健康檢查異常: {', '.join(unhealthy)}"
        )

        # 發送郵件
        send_email_alert(report)
```

### 3. 健康檢查策略

- **Liveness**: 檢查服務是否存活（輕量級）
- **Readiness**: 檢查服務是否就緒（檢查依賴）
- **Startup**: 檢查服務啟動狀態

```python
# Liveness: 簡單檢查
@app.get("/health/live")
async def liveness():
    return {"alive": True}

# Readiness: 檢查依賴
@app.get("/health/ready")
async def readiness():
    results = health_checker.check_all(include=["database", "redis"])

    if any(r.status == HealthStatus.UNHEALTHY for r in results.values()):
        raise HTTPException(status_code=503)

    return {"ready": True}
```

### 4. 快取健康報告

避免頻繁檢查影響性能：

```python
from functools import lru_cache
import time

@lru_cache(maxsize=1)
def cached_health_report(timestamp: int):
    """快取 30 秒的健康報告"""
    health_checker = HealthChecker()
    return health_checker.get_health_report()

@app.get("/health/cached")
async def cached_health():
    # 30 秒快取
    timestamp = int(time.time() / 30)
    return cached_health_report(timestamp)
```

## 常見問題

### Q: 如何設置健康檢查超時？

A: 在 Kubernetes 配置中設置 `timeoutSeconds`:

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8000
  timeoutSeconds: 5  # 5 秒超時
```

### Q: 如何處理間歇性故障？

A: 設置 `failureThreshold` 允許多次失敗：

```yaml
readinessProbe:
  httpGet:
    path: /readyz
    port: 8000
  failureThreshold: 3  # 連續 3 次失敗才標記為不健康
```

### Q: 如何自訂健康檢查邏輯？

A: 使用 `register_check()` 註冊自訂檢查：

```python
def custom_check() -> ComponentStatus:
    # 自訂檢查邏輯
    pass

health_checker.register_check("custom", custom_check)
```

### Q: 健康檢查影響性能嗎？

A:
- 基本檢查（/health, /healthz）非常輕量，幾乎無影響
- 詳細檢查（/health/detailed）會檢查所有組件，建議設置合理的檢查間隔
- 使用異步檢查可以提高性能
- 考慮快取健康報告

## 範例截圖

### 健康檢查回覆

```bash
$ curl http://localhost:8000/health/detailed | jq
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "checks": {
    "database": {
      "status": "healthy",
      "message": "資料庫連接正常",
      "response_time": 0.05
    },
    ...
  },
  "summary": {
    "total_checks": 5,
    "healthy": 5,
    "degraded": 0,
    "unhealthy": 0
  }
}
```

## 參考資源

- [Kubernetes Liveness and Readiness Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [Prometheus Monitoring](https://prometheus.io/docs/introduction/overview/)
- [Health Check API Pattern](https://microservices.io/patterns/observability/health-check-api.html)

## 授權

MIT License
