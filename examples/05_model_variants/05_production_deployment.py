"""
範例：生產環境部署

展示如何在生產環境中部署 RAG 增強的醫療聊天機器人。
"""
from pathlib import Path
import sys
from typing import Optional, Dict, Any
import asyncio

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from medical_chatbot.rag import MedicalEmbedder, MedicalRetriever, RAGGenerator
from medical_chatbot.utils.logger import setup_logger
from medical_chatbot.utils.safety import SafetyFilter

logger = setup_logger()


def example_docker_deployment():
    """Docker 部署配置"""
    print("\n" + "=" * 60)
    print("範例 1: Docker 容器化部署")
    print("=" * 60)

    dockerfile_content = """
# 醫療聊天機器人 Dockerfile (多模型 + RAG)
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

# 安裝 Python 和依賴
RUN apt-get update && apt-get install -y \\
    python3.10 \\
    python3-pip \\
    git \\
    && rm -rf /var/lib/apt/lists/*

# 設置工作目錄
WORKDIR /app

# 複製依賴文件
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip3 install --no-cache-dir -r requirements.txt

# 複製專案文件
COPY . .

# 下載和初始化模型（可選，減少啟動時間）
# RUN python3 -c "from medical_chatbot.rag import MedicalEmbedder; MedicalEmbedder()"

# 暴露端口
EXPOSE 8000 7860

# 設置環境變數
ENV MODEL_NAME="taide/Llama3-TAIDE-LX-8B-Chat-Alpha1"
ENV DEVICE="auto"
ENV USE_RAG="true"

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD python3 -c "import requests; requests.get('http://localhost:8000/health')"

# 啟動命令
CMD ["python3", "-m", "uvicorn", "medical_chatbot.api.server:app", \\
     "--host", "0.0.0.0", "--port", "8000"]
"""

    docker_compose_content = """
# Docker Compose - 完整醫療聊天機器人部署
version: '3.8'

services:
  # 主服務：醫療聊天機器人 API
  medical-chatbot-api:
    build: .
    image: medical-chatbot:latest
    container_name: medical-chatbot-api
    ports:
      - "8000:8000"
    environment:
      - MODEL_NAME=taide/Llama3-TAIDE-LX-8B-Chat-Alpha1
      - USE_RAG=true
      - REDIS_HOST=redis
      - POSTGRES_HOST=postgres
    volumes:
      - ./data:/app/data
      - ./models:/app/models
      - ./logs:/app/logs
      - ./configs:/app/configs
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    depends_on:
      - redis
      - postgres
    networks:
      - medical-network
    restart: unless-stopped

  # Gradio 網頁介面
  medical-chatbot-gradio:
    build: .
    image: medical-chatbot:latest
    container_name: medical-chatbot-gradio
    command: python3 -m medical_chatbot.cli gradio
    ports:
      - "7860:7860"
    environment:
      - MODEL_NAME=taide/Llama3-TAIDE-LX-8B-Chat-Alpha1
    volumes:
      - ./data:/app/data
      - ./models:/app/models
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    networks:
      - medical-network
    restart: unless-stopped

  # Redis 快取服務
  redis:
    image: redis:7-alpine
    container_name: medical-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    networks:
      - medical-network
    restart: unless-stopped

  # PostgreSQL 資料庫
  postgres:
    image: postgres:15-alpine
    container_name: medical-postgres
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=medical_chatbot
      - POSTGRES_USER=medbot
      - POSTGRES_PASSWORD=secure_password_here
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - medical-network
    restart: unless-stopped

  # Prometheus 監控
  prometheus:
    image: prom/prometheus:latest
    container_name: medical-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./configs/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
    networks:
      - medical-network
    restart: unless-stopped

  # Grafana 可視化
  grafana:
    image: grafana/grafana:latest
    container_name: medical-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
    depends_on:
      - prometheus
    networks:
      - medical-network
    restart: unless-stopped

volumes:
  redis-data:
  postgres-data:
  prometheus-data:
  grafana-data:

networks:
  medical-network:
    driver: bridge
"""

    print("\nDockerfile 配置：")
    print(dockerfile_content[:500] + "...\n")

    print("Docker Compose 配置：")
    print(docker_compose_content[:500] + "...\n")

    print("部署步驟：")
    print("1. 構建映像：")
    print("   docker-compose build")
    print("\n2. 啟動服務：")
    print("   docker-compose up -d")
    print("\n3. 查看日誌：")
    print("   docker-compose logs -f medical-chatbot-api")
    print("\n4. 健康檢查：")
    print("   curl http://localhost:8000/health")
    print("\n5. 訪問服務：")
    print("   - API: http://localhost:8000")
    print("   - Gradio: http://localhost:7860")
    print("   - Prometheus: http://localhost:9090")
    print("   - Grafana: http://localhost:3000")

    print("\n✓ Docker 部署範例完成")


def example_kubernetes_deployment():
    """Kubernetes 部署"""
    print("\n" + "=" * 60)
    print("範例 2: Kubernetes 雲端部署")
    print("=" * 60)

    k8s_deployment = """
# Kubernetes Deployment - 醫療聊天機器人
apiVersion: apps/v1
kind: Deployment
metadata:
  name: medical-chatbot-api
  labels:
    app: medical-chatbot
    component: api
spec:
  replicas: 3  # 3 個副本以提供高可用性
  selector:
    matchLabels:
      app: medical-chatbot
      component: api
  template:
    metadata:
      labels:
        app: medical-chatbot
        component: api
    spec:
      containers:
      - name: api
        image: your-registry/medical-chatbot:latest
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: MODEL_NAME
          valueFrom:
            configMapKeyRef:
              name: medical-chatbot-config
              key: model_name
        - name: USE_RAG
          value: "true"
        - name: REDIS_HOST
          value: redis-service
        - name: POSTGRES_HOST
          value: postgres-service
        resources:
          requests:
            memory: "8Gi"
            cpu: "2"
            nvidia.com/gpu: "1"
          limits:
            memory: "16Gi"
            cpu: "4"
            nvidia.com/gpu: "1"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        volumeMounts:
        - name: model-cache
          mountPath: /app/models
        - name: vector-store
          mountPath: /app/data/vector_stores
      volumes:
      - name: model-cache
        persistentVolumeClaim:
          claimName: model-cache-pvc
      - name: vector-store
        persistentVolumeClaim:
          claimName: vector-store-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: medical-chatbot-api-service
spec:
  type: LoadBalancer
  selector:
    app: medical-chatbot
    component: api
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: medical-chatbot-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: medical-chatbot-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
"""

    print("\nKubernetes Deployment 配置：")
    print(k8s_deployment[:500] + "...\n")

    print("部署到 Kubernetes：")
    print("1. 創建 ConfigMap：")
    print("   kubectl create configmap medical-chatbot-config \\")
    print("     --from-literal=model_name=taide/Llama3-TAIDE-LX-8B-Chat-Alpha1")
    print("\n2. 部署應用：")
    print("   kubectl apply -f k8s-deployment.yaml")
    print("\n3. 查看狀態：")
    print("   kubectl get pods -l app=medical-chatbot")
    print("\n4. 查看服務：")
    print("   kubectl get svc medical-chatbot-api-service")
    print("\n5. 水平擴展：")
    print("   kubectl scale deployment medical-chatbot-api --replicas=5")

    print("\n特點：")
    print("- 自動擴展（HPA）根據 CPU/記憶體使用率")
    print("- 健康檢查和自動恢復")
    print("- GPU 資源分配")
    print("- 持久化儲存（模型和向量庫）")

    print("\n✓ Kubernetes 部署範例完成")


def example_load_balancing():
    """負載平衡配置"""
    print("\n" + "=" * 60)
    print("範例 3: 負載平衡和高可用性")
    print("=" * 60)

    nginx_config = """
# Nginx 負載平衡配置
upstream medical_chatbot_backend {
    # 負載平衡策略：least_conn (最少連接)
    least_conn;

    # 後端服務器
    server chatbot-api-1:8000 weight=3 max_fails=3 fail_timeout=30s;
    server chatbot-api-2:8000 weight=3 max_fails=3 fail_timeout=30s;
    server chatbot-api-3:8000 weight=2 max_fails=3 fail_timeout=30s;

    # 備用服務器
    server chatbot-api-backup:8000 backup;

    # 健康檢查
    keepalive 32;
}

server {
    listen 80;
    server_name medical-chatbot.example.com;

    # SSL 配置（生產環境必需）
    # listen 443 ssl http2;
    # ssl_certificate /etc/nginx/ssl/cert.pem;
    # ssl_certificate_key /etc/nginx/ssl/key.pem;

    # 客戶端最大請求大小
    client_max_body_size 10M;

    # 超時設置
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;

    # API 端點
    location /api/ {
        proxy_pass http://medical_chatbot_backend/;

        # 代理標頭
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 支援
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 靜態文件
    location /static/ {
        alias /var/www/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 健康檢查
    location /health {
        proxy_pass http://medical_chatbot_backend/health;
        access_log off;
    }

    # 速率限制
    location /chat {
        limit_req zone=chat_limit burst=10 nodelay;
        proxy_pass http://medical_chatbot_backend/chat;
    }
}

# 速率限制定義
limit_req_zone $binary_remote_addr zone=chat_limit:10m rate=10r/s;
"""

    print("\nNginx 負載平衡配置：")
    print(nginx_config[:500] + "...\n")

    print("負載平衡策略：")
    print("1. Round Robin (輪詢) - 默認")
    print("2. Least Connections (最少連接) - 推薦用於醫療 API")
    print("3. IP Hash (IP 雜湊) - 保持會話親和性")
    print("4. Weighted (加權) - 不同服務器性能")

    print("\n高可用性配置：")
    print("- 多個後端服務器")
    print("- 備用服務器（backup）")
    print("- 健康檢查和故障轉移")
    print("- 速率限制保護")

    print("\n✓ 負載平衡範例完成")


def example_caching_strategy():
    """快取策略"""
    print("\n" + "=" * 60)
    print("範例 4: 多層快取策略")
    print("=" * 60)

    print("\n快取層級架構：\n")

    print("第 1 層：應用內快取 (LRU Cache)")
    print("- 快取熱門查詢結果")
    print("- TTL: 5 分鐘")
    print("- 大小: 1000 個項目")

    lru_cache_example = """
from functools import lru_cache
from cachetools import TTLCache
import time

class ApplicationCache:
    def __init__(self):
        # TTL 快取：5 分鐘過期
        self.cache = TTLCache(maxsize=1000, ttl=300)

    def get(self, key):
        return self.cache.get(key)

    def set(self, key, value):
        self.cache[key] = value

    @lru_cache(maxsize=100)
    def get_embedding(self, text):
        # 嵌入向量快取
        # 實際實現...
        pass
"""

    print("\n第 2 層：Redis 分散式快取")
    print("- 快取 RAG 檢索結果")
    print("- TTL: 1 小時")
    print("- 多服務器共享")

    redis_cache_example = """
import redis
import json

class RedisCache:
    def __init__(self, host='localhost', port=6379):
        self.redis = redis.Redis(
            host=host,
            port=port,
            decode_responses=True
        )

    def cache_rag_results(self, query, results, ttl=3600):
        key = f"rag:{hash(query)}"
        self.redis.setex(
            key,
            ttl,
            json.dumps(results)
        )

    def get_rag_results(self, query):
        key = f"rag:{hash(query)}"
        data = self.redis.get(key)
        return json.loads(data) if data else None

    def invalidate_pattern(self, pattern):
        # 清除符合模式的快取
        for key in self.redis.scan_iter(match=pattern):
            self.redis.delete(key)
"""

    print("\n第 3 層：CDN 快取")
    print("- 快取靜態內容和 API 響應")
    print("- 全球分發")
    print("- Edge 快取")

    print("\n快取策略建議：")
    print("1. 查詢結果：快取常見醫療問題的回答")
    print("2. RAG 檢索：快取向量檢索結果")
    print("3. 嵌入向量：快取文本嵌入")
    print("4. 模型輸出：快取確定性回答")

    print("\n快取失效策略：")
    print("- 時間過期（TTL）")
    print("- 主動失效（知識庫更新時）")
    print("- LRU 淘汰（記憶體不足時）")

    print("\n✓ 快取策略範例完成")


def example_monitoring_and_alerting():
    """監控和告警"""
    print("\n" + "=" * 60)
    print("範例 5: 監控和告警系統")
    print("=" * 60)

    prometheus_config = """
# Prometheus 配置
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  # 醫療聊天機器人 API
  - job_name: 'medical-chatbot-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'

  # Redis
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  # PostgreSQL
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  # Node Exporter（系統指標）
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']

# 告警規則
rule_files:
  - 'alert_rules.yml'

# Alertmanager 配置
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
"""

    alert_rules = """
# 告警規則
groups:
  - name: medical_chatbot_alerts
    interval: 30s
    rules:
      # API 響應時間過長
      - alert: HighAPILatency
        expr: histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API 響應時間過長"
          description: "95% 請求響應時間超過 2 秒"

      # API 錯誤率過高
      - alert: HighErrorRate
        expr: rate(api_errors_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "API 錯誤率過高"
          description: "錯誤率超過 5%"

      # 記憶體使用過高
      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "記憶體使用率過高"
          description: "記憶體使用超過 90%"

      # GPU 使用率過高
      - alert: HighGPUUsage
        expr: nvidia_gpu_utilization > 95
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "GPU 使用率持續過高"

      # RAG 檢索失敗率
      - alert: RAGRetrievalFailure
        expr: rate(rag_retrieval_failures_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "RAG 檢索失敗率過高"
"""

    print("\nPrometheus 配置：")
    print(prometheus_config[:400] + "...\n")

    print("監控指標：")
    print("1. 請求指標")
    print("   - 總請求數、錯誤率、響應時間")
    print("   - P50/P95/P99 延遲")
    print("\n2. 系統指標")
    print("   - CPU、記憶體、GPU 使用率")
    print("   - 磁碟 I/O、網路流量")
    print("\n3. 業務指標")
    print("   - RAG 檢索成功率")
    print("   - 緊急情況檢測次數")
    print("   - 用戶滿意度評分")

    print("\n告警通知：")
    print("- Slack 整合")
    print("- Email 通知")
    print("- PagerDuty（緊急）")
    print("- Webhook（自定義）")

    print("\n✓ 監控告警範例完成")


def example_security_best_practices():
    """安全最佳實踐"""
    print("\n" + "=" * 60)
    print("範例 6: 安全最佳實踐")
    print("=" * 60)

    print("\n安全措施：\n")

    print("1. API 認證和授權")
    api_auth_example = """
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    # 驗證 JWT token
    if not is_valid_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    return get_user_from_token(token)

@app.post("/chat")
async def chat(request: ChatRequest, user = Depends(verify_token)):
    # 已驗證的用戶才能訪問
    ...
"""

    print("2. 速率限制")
    rate_limit_example = """
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/chat")
@limiter.limit("10/minute")  # 每分鐘最多 10 次
async def chat(request: Request, chat_request: ChatRequest):
    ...
"""

    print("3. 輸入驗證和消毒")
    print("   - XSS 防護")
    print("   - SQL 注入防護")
    print("   - 命令注入防護")

    print("\n4. HTTPS 強制")
    print("   - TLS 1.3")
    print("   - 強加密套件")
    print("   - HSTS 標頭")

    print("\n5. 資料加密")
    print("   - 傳輸加密（HTTPS）")
    print("   - 儲存加密（數據庫）")
    print("   - 密鑰管理（KMS）")

    print("\n6. 審計日誌")
    print("   - 所有 API 請求")
    print("   - 認證事件")
    print("   - 資料訪問")

    print("\n7. 依賴安全")
    print("   - 定期更新依賴")
    print("   - 漏洞掃描（Snyk, Dependabot）")
    print("   - 最小權限原則")

    print("\n✓ 安全最佳實踐範例完成")


def main():
    """執行所有範例"""
    print("\n" + "=" * 60)
    print("生產環境部署範例")
    print("=" * 60)

    try:
        example_docker_deployment()
        example_kubernetes_deployment()
        example_load_balancing()
        example_caching_strategy()
        example_monitoring_and_alerting()
        example_security_best_practices()

        print("\n" + "=" * 60)
        print("所有生產部署範例完成！")
        print("=" * 60)

        print("\n生產環境檢查清單：")
        print("✓ 容器化部署（Docker/Kubernetes）")
        print("✓ 負載平衡和高可用性")
        print("✓ 多層快取策略")
        print("✓ 監控和告警系統")
        print("✓ 安全措施和合規性")
        print("✓ 備份和災難恢復")
        print("✓ 文檔和運維手冊")

    except Exception as e:
        logger.error(f"執行範例時發生錯誤: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
