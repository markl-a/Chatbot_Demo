# Prometheus 監控整合

完整的 Prometheus 指標收集和導出功能。

## 功能特性

- ✅ HTTP 請求指標（計數、延遲、大小）
- ✅ 模型推理指標（計數、延遲、Token 速度）
- ✅ 資料庫指標（連接池、查詢）
- ✅ 快取指標（命中率、大小）
- ✅ 健康狀態指標
- ✅ 錯誤追蹤
- ✅ FastAPI 自動整合

## 快速開始

### 設置監控

```python
from fastapi import FastAPI
from src.medical_chatbot.monitoring import setup_prometheus_metrics

app = FastAPI()
setup_prometheus_metrics(app)
```

訪問: http://localhost:8000/metrics

### 追蹤推理

```python
from src.medical_chatbot.monitoring import get_metrics

metrics = get_metrics()

# 追蹤模型推理
metrics.track_inference(
    model_name="TAIDE-LX-8B",
    duration=1.5,
    tokens=100,
    success=True,
)
```

### 追蹤快取

```python
# 快取命中
metrics.track_cache_hit(cache_type="redis")

# 快取未命中
metrics.track_cache_miss(cache_type="redis")
```

## 指標類型

### HTTP 指標

- `http_requests_total` - 總請求數
- `http_request_duration_seconds` - 請求延遲
- `http_request_size_bytes` - 請求大小
- `http_response_size_bytes` - 回覆大小

### 模型指標

- `model_inferences_total` - 總推理數
- `model_inference_duration_seconds` - 推理延遲
- `model_tokens_per_second` - Token 生成速度

### 快取指標

- `cache_hits_total` - 快取命中數
- `cache_misses_total` - 快取未命中數
- `cache_size_bytes` - 快取大小

### 健康指標

- `health_status` - 健康狀態（1=健康, 0.5=降級, 0=不健康）
- `errors_total` - 錯誤總數

## Prometheus 配置

```yaml
scrape_configs:
  - job_name: 'medical-chatbot'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

## Grafana 儀表板

### 查詢範例

```promql
# HTTP 請求速率
rate(http_requests_total[5m])

# 平均延遲
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])

# 模型推理速度
rate(model_tokens_per_second_sum[5m]) / rate(model_tokens_per_second_count[5m])

# 快取命中率
rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m]))
```

## 告警規則

```yaml
groups:
  - name: medical_chatbot
    rules:
      - alert: HighErrorRate
        expr: rate(errors_total[5m]) > 0.05
        for: 5m
        annotations:
          summary: "錯誤率過高"

      - alert: SlowInference
        expr: rate(model_inference_duration_seconds_sum[5m]) / rate(model_inference_duration_seconds_count[5m]) > 5
        for: 5m
        annotations:
          summary: "推理速度過慢"
```

## 授權

MIT License
