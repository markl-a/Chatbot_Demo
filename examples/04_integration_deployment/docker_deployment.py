#!/usr/bin/env python3
"""
案例 4.1: Docker 容器化部署示例

這個範例展示如何使用 Docker 部署醫療聊天機器人，包括：
- Dockerfile 生成
- Docker Compose 配置
- 容器健康檢查
- 部署腳本

運行方式:
    python examples/04_integration_deployment/docker_deployment.py
"""

from pathlib import Path
from typing import Dict, Any


class DockerDeployment:
    """Docker 部署助手"""

    def __init__(self, project_root: str = "."):
        """初始化 Docker 部署助手

        Args:
            project_root: 專案根目錄
        """
        self.project_root = Path(project_root)

    def generate_dockerfile(self) -> str:
        """生成 Dockerfile

        Returns:
            Dockerfile 內容
        """
        dockerfile_content = """# 醫療聊天機器人 Dockerfile
FROM python:3.9-slim

# 設置工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \\
    git \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# 複製需求文件
COPY requirements.txt .
COPY setup.py .
COPY README.md .

# 安裝 Python 依賴
RUN pip install --no-cache-dir --upgrade pip && \\
    pip install --no-cache-dir -e .

# 複製應用代碼
COPY src/ ./src/
COPY configs/ ./configs/

# 創建必要的目錄
RUN mkdir -p /app/logs /app/data

# 設置環境變量
ENV PYTHONUNBUFFERED=1
ENV MODEL_CACHE_DIR=/app/models

# 暴露端口
EXPOSE 8000 7860

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# 預設命令：啟動 API 服務
CMD ["python", "-m", "medical_chatbot.api.server"]
"""
        return dockerfile_content

    def generate_docker_compose(self) -> str:
        """生成 docker-compose.yml

        Returns:
            docker-compose.yml 內容
        """
        compose_content = """version: '3.8'

services:
  # API 服務
  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: medical-chatbot-api
    ports:
      - "8000:8000"
    volumes:
      - ./models:/app/models
      - ./logs:/app/logs
      - ./data:/app/data
    environment:
      - MODEL_NAME=taide/TAIDE-LX-7B-Chat
      - DEVICE=cuda
      - LOG_LEVEL=INFO
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  # Gradio 介面服務
  gradio:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: medical-chatbot-gradio
    command: python -m medical_chatbot.api.gradio_app
    ports:
      - "7860:7860"
    volumes:
      - ./models:/app/models
      - ./logs:/app/logs
    environment:
      - MODEL_NAME=taide/TAIDE-LX-7B-Chat
      - DEVICE=cuda
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped
    depends_on:
      - api

  # Nginx 反向代理（可選）
  nginx:
    image: nginx:alpine
    container_name: medical-chatbot-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - api
      - gradio
    restart: unless-stopped

volumes:
  models:
  logs:
  data:
"""
        return compose_content

    def generate_dockerignore(self) -> str:
        """生成 .dockerignore

        Returns:
            .dockerignore 內容
        """
        dockerignore_content = """# Python
__pycache__
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Git
.git/
.gitignore

# Models (will be mounted)
models/

# Logs
logs/
*.log

# Data
data/
*.db

# Testing
.pytest_cache/
.coverage
htmlcov/

# Documentation
docs/_build/

# OS
.DS_Store
Thumbs.db
"""
        return dockerignore_content

    def generate_deployment_script(self) -> str:
        """生成部署腳本

        Returns:
            部署腳本內容
        """
        deploy_script = """#!/bin/bash
# 醫療聊天機器人 Docker 部署腳本

set -e

echo "========================================"
echo "醫療聊天機器人 Docker 部署"
echo "========================================"

# 顏色定義
GREEN='\\033[0;32m'
RED='\\033[0;31m'
NC='\\033[0m' # No Color

# 檢查 Docker 是否安裝
if ! command -v docker &> /dev/null; then
    echo -e "${RED}錯誤: Docker 未安裝${NC}"
    exit 1
fi

# 檢查 Docker Compose 是否安裝
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}錯誤: Docker Compose 未安裝${NC}"
    exit 1
fi

# 創建必要的目錄
echo "創建必要的目錄..."
mkdir -p models logs data

# 建構 Docker 映像
echo -e "${GREEN}建構 Docker 映像...${NC}"
docker-compose build

# 啟動服務
echo -e "${GREEN}啟動服務...${NC}"
docker-compose up -d

# 等待服務就緒
echo "等待服務啟動..."
sleep 10

# 檢查服務狀態
echo -e "${GREEN}檢查服務狀態...${NC}"
docker-compose ps

# 檢查健康狀態
echo "檢查 API 健康狀態..."
for i in {1..30}; do
    if curl -f http://localhost:8000/health &> /dev/null; then
        echo -e "${GREEN}✓ API 服務正常運行${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ API 服務未能正常啟動${NC}"
        docker-compose logs api
        exit 1
    fi
    echo "等待中... ($i/30)"
    sleep 2
done

echo ""
echo "========================================"
echo -e "${GREEN}部署完成！${NC}"
echo "========================================"
echo "API 服務: http://localhost:8000"
echo "Gradio 介面: http://localhost:7860"
echo "API 文檔: http://localhost:8000/docs"
echo ""
echo "查看日誌: docker-compose logs -f"
echo "停止服務: docker-compose down"
echo "========================================"
"""
        return deploy_script

    def save_deployment_files(self):
        """保存所有部署文件"""
        # 創建目錄
        deployment_dir = Path("deployment")
        deployment_dir.mkdir(exist_ok=True)

        # 保存 Dockerfile
        dockerfile_path = deployment_dir / "Dockerfile"
        with open(dockerfile_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_dockerfile())
        print(f"✓ 已生成: {dockerfile_path}")

        # 保存 docker-compose.yml
        compose_path = deployment_dir / "docker-compose.yml"
        with open(compose_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_docker_compose())
        print(f"✓ 已生成: {compose_path}")

        # 保存 .dockerignore
        dockerignore_path = deployment_dir / ".dockerignore"
        with open(dockerignore_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_dockerignore())
        print(f"✓ 已生成: {dockerignore_path}")

        # 保存部署腳本
        deploy_script_path = deployment_dir / "deploy.sh"
        with open(deploy_script_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_deployment_script())

        # 設置執行權限
        deploy_script_path.chmod(0o755)
        print(f"✓ 已生成: {deploy_script_path}")

        return deployment_dir


def demo_generate_files():
    """示範生成部署文件"""
    print("\n" + "=" * 60)
    print("示範: 生成 Docker 部署文件")
    print("=" * 60)

    deployer = DockerDeployment()

    print("\n正在生成部署文件...")
    deployment_dir = deployer.save_deployment_files()

    print(f"\n部署文件已生成到: {deployment_dir.absolute()}")
    print("\n使用方式:")
    print(f"  1. cd {deployment_dir}")
    print("  2. ./deploy.sh")
    print("\n或手動執行:")
    print("  docker-compose build")
    print("  docker-compose up -d")


def demo_deployment_commands():
    """示範部署命令"""
    print("\n" + "=" * 60)
    print("示範: Docker 部署命令")
    print("=" * 60)

    commands = {
        "建構映像": "docker-compose build",
        "啟動服務": "docker-compose up -d",
        "查看狀態": "docker-compose ps",
        "查看日誌": "docker-compose logs -f",
        "停止服務": "docker-compose down",
        "重啟服務": "docker-compose restart",
        "進入容器": "docker-compose exec api bash",
        "查看資源使用": "docker stats"
    }

    for operation, command in commands.items():
        print(f"\n{operation}:")
        print(f"  $ {command}")


def demo_health_check():
    """示範健康檢查"""
    print("\n" + "=" * 60)
    print("示範: 容器健康檢查")
    print("=" * 60)

    health_checks = """
# 檢查 API 服務健康狀態
curl -f http://localhost:8000/health

# 檢查容器健康狀態
docker-compose ps

# 查看詳細健康檢查日誌
docker inspect --format='{{json .State.Health}}' medical-chatbot-api | jq

# 自動重啟不健康的容器
# 在 docker-compose.yml 中已配置: restart: unless-stopped
"""

    print(health_checks)


def main():
    """主函數"""
    print("""
╔══════════════════════════════════════════════════════════╗
║        醫療聊天機器人 - Docker 部署示例                  ║
╚══════════════════════════════════════════════════════════╝
    """)

    print("\n選擇要運行的示範:")
    print("1. 生成部署文件")
    print("2. 顯示部署命令")
    print("3. 顯示健康檢查方法")
    print("4. 運行所有示範")

    try:
        choice = input("\n請輸入選項 (1-4): ").strip()

        if choice == "1":
            demo_generate_files()
        elif choice == "2":
            demo_deployment_commands()
        elif choice == "3":
            demo_health_check()
        elif choice == "4":
            demo_generate_files()
            demo_deployment_commands()
            demo_health_check()
        else:
            print("無效的選項")

        print("\n" + "=" * 60)
        print("示範完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
