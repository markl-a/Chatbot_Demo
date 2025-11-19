"""
環境配置載入器

支援多環境配置檔案管理和動態載入。
"""
from typing import Optional, Dict, Any
from pathlib import Path
import os

from loguru import logger


class EnvLoader:
    """環境配置載入器"""

    def __init__(self, base_dir: Optional[str] = None):
        """
        初始化載入器

        Args:
            base_dir: 基礎目錄（預設為專案根目錄）
        """
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.env_files_dir = self.base_dir / "config"

        logger.info(f"環境載入器初始化: base_dir={self.base_dir}")

    # ========================================================================
    # 環境檔案管理
    # ========================================================================

    def get_env_file_path(self, environment: str) -> Path:
        """
        獲取環境配置檔案路徑

        Args:
            environment: 環境名稱（development/testing/staging/production）

        Returns:
            配置檔案路徑
        """
        # 優先級：
        # 1. config/.env.{environment}.local (本地覆蓋，不提交到 git)
        # 2. config/.env.{environment}
        # 3. .env.{environment}.local
        # 4. .env.{environment}
        # 5. .env

        possible_paths = [
            self.env_files_dir / f".env.{environment}.local",
            self.env_files_dir / f".env.{environment}",
            self.base_dir / f".env.{environment}.local",
            self.base_dir / f".env.{environment}",
            self.base_dir / ".env",
        ]

        for path in possible_paths:
            if path.exists():
                logger.info(f"找到環境配置: {path}")
                return path

        # 如果都不存在，返回預設路徑
        default_path = self.base_dir / ".env"
        logger.warning(f"未找到環境配置，使用預設: {default_path}")
        return default_path

    def load_env_file(self, environment: Optional[str] = None) -> Dict[str, str]:
        """
        載入環境配置檔案

        Args:
            environment: 環境名稱（None 時從 ENVIRONMENT 環境變數讀取）

        Returns:
            環境變數字典
        """
        if environment is None:
            environment = os.getenv("ENVIRONMENT", "development")

        env_file = self.get_env_file_path(environment)

        if not env_file.exists():
            logger.warning(f"配置檔案不存在: {env_file}")
            return {}

        env_vars = {}

        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                # 跳過空行和註釋
                if not line or line.startswith("#"):
                    continue

                # 解析 KEY=VALUE
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # 移除引號
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]

                    env_vars[key] = value

        logger.info(f"載入環境配置: {env_file}, 變數數量: {len(env_vars)}")

        return env_vars

    def set_env_vars(self, env_vars: Dict[str, str]):
        """
        設置環境變數

        Args:
            env_vars: 環境變數字典
        """
        for key, value in env_vars.items():
            os.environ[key] = value
            logger.debug(f"設置環境變數: {key}={'***' if 'PASSWORD' in key or 'SECRET' in key else value}")

    # ========================================================================
    # 範本生成
    # ========================================================================

    def create_env_template(
        self,
        output_path: Optional[str] = None,
        environment: str = "development"
    ) -> str:
        """
        創建環境配置範本

        Args:
            output_path: 輸出路徑（預設為 config/.env.{environment}.example）
            environment: 環境名稱

        Returns:
            輸出檔案路徑
        """
        if output_path is None:
            self.env_files_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(self.env_files_dir / f".env.{environment}.example")

        template = self._generate_template(environment)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(template)

        logger.info(f"環境配置範本已創建: {output_path}")

        return output_path

    def _generate_template(self, environment: str) -> str:
        """生成配置範本內容"""
        template = f"""# {environment.upper()} 環境配置
# 此檔案為範本，請複製為 .env.{environment} 並填入實際值

# ============================================================================
# 基本設定
# ============================================================================

APP_NAME=醫療聊天機器人
APP_VERSION=1.0.0
ENVIRONMENT={environment}
DEBUG={str(environment == "development").lower()}

# API 設定
API_HOST=0.0.0.0
API_PORT=8000
API_PREFIX=/api/v1

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]

# ============================================================================
# 資料庫配置
# ============================================================================

# SQLite（開發環境）
# DATABASE_URL=sqlite:///./medical_chatbot.db

# PostgreSQL（生產環境）
# DATABASE_URL=postgresql://user:password@localhost:5432/medical_chatbot

DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10
DATABASE_ECHO={str(environment == "development").lower()}

# ============================================================================
# Redis 配置
# ============================================================================

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
# REDIS_PASSWORD=your-redis-password
REDIS_MAX_CONNECTIONS=50

# ============================================================================
# 快取配置
# ============================================================================

CACHE_STRATEGY=multi_tier
CACHE_MEMORY_SIZE=1000
CACHE_TTL=3600

# ============================================================================
# 速率限制配置
# ============================================================================

RATE_LIMIT_ENABLED=true
RATE_LIMIT_STRATEGY=sliding_window
RATE_LIMIT_DEFAULT=60
RATE_LIMIT_WINDOW=60

# ============================================================================
# 模型配置
# ============================================================================

MODEL_NAME=TAIDE-LX-8B
# MODEL_PATH=/path/to/model
MODEL_DEVICE=cuda
MODEL_MAX_LENGTH=512
MODEL_TEMPERATURE=0.7
MODEL_TOP_P=0.9

# ============================================================================
# 批次推理配置
# ============================================================================

BATCH_SIZE=8
BATCH_MAX_WORKERS=4
BATCH_SAVE_INTERVAL=100

# ============================================================================
# 日誌配置
# ============================================================================

LOG_LEVEL={'DEBUG' if environment == 'development' else 'INFO'}
LOG_FILE=logs/app.log
LOG_ROTATION=500 MB
LOG_RETENTION=10 days

# ============================================================================
# 安全配置
# ============================================================================

# ⚠️ 生產環境務必更改此密鑰！
SECRET_KEY={'your-secret-key-change-in-production' if environment != 'production' else 'CHANGE-THIS-IN-PRODUCTION'}
API_KEY_HEADER=X-API-Key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# ============================================================================
# 監控配置
# ============================================================================

METRICS_ENABLED=true
METRICS_PORT=9090
HEALTH_CHECK_INTERVAL=30

# ============================================================================
# 其他配置
# ============================================================================

TIMEZONE=Asia/Taipei
MAX_REQUEST_SIZE=10485760
UPLOAD_DIR=uploads
"""

        return template

    # ========================================================================
    # 配置驗證
    # ========================================================================

    def validate_required_vars(self, required_vars: list) -> bool:
        """
        驗證必需的環境變數

        Args:
            required_vars: 必需的環境變數列表

        Returns:
            是否全部存在
        """
        missing_vars = []

        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            logger.error(f"缺少必需的環境變數: {', '.join(missing_vars)}")
            return False

        logger.info("所有必需的環境變數已設置")
        return True

    def display_current_env(self, hide_sensitive: bool = True):
        """
        顯示當前環境變數

        Args:
            hide_sensitive: 是否隱藏敏感資訊
        """
        sensitive_keywords = ["PASSWORD", "SECRET", "KEY", "TOKEN"]

        print("\n當前環境變數:")
        print("=" * 80)

        for key, value in sorted(os.environ.items()):
            # 只顯示應用相關的變數
            if not (
                key.startswith("APP_")
                or key.startswith("DATABASE_")
                or key.startswith("REDIS_")
                or key.startswith("MODEL_")
                or key == "ENVIRONMENT"
            ):
                continue

            if hide_sensitive and any(keyword in key for keyword in sensitive_keywords):
                display_value = "***HIDDEN***"
            else:
                display_value = value

            print(f"  {key}: {display_value}")

        print("=" * 80)

    # ========================================================================
    # 批次操作
    # ========================================================================

    def create_all_templates(self):
        """創建所有環境的配置範本"""
        environments = ["development", "testing", "staging", "production"]

        for env in environments:
            self.create_env_template(environment=env)

        logger.info(f"已創建 {len(environments)} 個環境配置範本")

    def switch_environment(self, environment: str):
        """
        切換環境

        Args:
            environment: 目標環境
        """
        logger.info(f"切換環境: {environment}")

        # 載入環境配置
        env_vars = self.load_env_file(environment)

        # 設置環境變數
        self.set_env_vars(env_vars)

        # 更新 ENVIRONMENT 變數
        os.environ["ENVIRONMENT"] = environment

        logger.info(f"環境已切換到: {environment}")


# ============================================================================
# 輔助函數
# ============================================================================

def setup_environment(environment: Optional[str] = None, base_dir: Optional[str] = None):
    """
    設置環境（快捷函數）

    Args:
        environment: 環境名稱
        base_dir: 基礎目錄
    """
    loader = EnvLoader(base_dir=base_dir)

    if environment:
        loader.switch_environment(environment)
    else:
        # 從環境變數或預設讀取
        env = os.getenv("ENVIRONMENT", "development")
        env_vars = loader.load_env_file(env)
        loader.set_env_vars(env_vars)

    return loader
