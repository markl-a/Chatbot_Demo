# 進階功能示範

本目錄包含 Medical Chatbot v0.3.0 新增的進階功能示範。

## 新增功能

### 1. WebSocket 實時通信
- 雙向即時通訊
- 房間/群組功能
- 串流回覆支援
- 心跳檢測

### 2. JWT 認證系統
- 訪問令牌和刷新令牌
- 角色權限管理 (RBAC)
- 密碼安全處理
- 中間件整合

### 3. OpenTelemetry 分佈式追蹤
- 請求鏈路追蹤
- 多種導出器支援 (Console, OTLP, Jaeger)
- 自動追蹤中間件
- 上下文傳播

### 4. Grafana 監控儀表板
- 預設儀表板配置
- Prometheus 指標收集
- 告警規則
- 完整的 docker-compose 配置

### 5. 彈性模式
- 斷路器 (Circuit Breaker)
- 重試機制 (Retry with Exponential Backoff)
- 超時處理 (Timeout)

## 快速開始

### 安裝依賴

```bash
# 安裝所有依賴
pip install -e ".[all]"

# 或分別安裝
pip install -e ".[api,auth,tracing]"
```

### 運行示範

```bash
# WebSocket 示範
python websocket_example.py

# JWT 認證示範
python auth_example.py

# 分佈式追蹤示範
python tracing_example.py

# 斷路器示範
python circuit_breaker_example.py
```

## 監控設置

### 啟動監控堆疊

```bash
cd monitoring
docker-compose -f docker-compose.monitoring.yml up -d
```

### 訪問服務

- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- Jaeger: http://localhost:16686
- Alertmanager: http://localhost:9093

## 相關文檔

- [WebSocket API 文檔](../../docs/websocket_api.md)
- [認證 API 文檔](../../docs/auth_api.md)
- [追蹤配置指南](../../docs/tracing_guide.md)
- [監控設置指南](../../docs/monitoring_guide.md)
