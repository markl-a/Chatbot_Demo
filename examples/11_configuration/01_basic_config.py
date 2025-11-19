"""
基本配置管理範例

展示如何使用配置管理系統。
"""
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.medical_chatbot.config import Settings, EnvLoader


# ============================================================================
# 範例 1: 基本配置加載
# ============================================================================


def example_1_basic_settings():
    """基本配置加載"""
    print("\n" + "=" * 80)
    print("範例 1: 基本配置加載")
    print("=" * 80)

    # 創建配置
    settings = Settings()

    print(f"\n應用配置:")
    print(f"  名稱: {settings.APP_NAME}")
    print(f"  版本: {settings.APP_VERSION}")
    print(f"  環境: {settings.ENVIRONMENT}")
    print(f"  調試模式: {settings.DEBUG}")

    print(f"\n資料庫配置:")
    print(f"  URL: {settings.DATABASE_URL}")
    print(f"  連接池大小: {settings.DATABASE_POOL_SIZE}")

    print(f"\nRedis 配置:")
    print(f"  主機: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    print(f"  資料庫: {settings.REDIS_DB}")

    print(f"\n模型配置:")
    print(f"  名稱: {settings.MODEL_NAME}")
    print(f"  設備: {settings.DEVICE}")
    print(f"  最大長度: {settings.MAX_LENGTH}")


# ============================================================================
# 範例 2: 環境變數加載
# ============================================================================


def example_2_env_loading():
    """環境變數加載"""
    print("\n" + "=" * 80)
    print("範例 2: 環境變數加載")
    print("=" * 80)

    # 創建環境加載器
    loader = EnvLoader()

    print(f"\n環境檔案目錄: {loader.env_files_dir}")

    # 檢查環境檔案
    for env in ["development", "staging", "production"]:
        env_file = loader.get_env_file_path(env)
        exists = env_file.exists()
        print(f"  {env}: {env_file} ({'存在' if exists else '不存在'})")

    # 加載開發環境配置
    print(f"\n加載開發環境配置...")
    dev_env = loader.load_env("development")

    print(f"  變數數量: {len(dev_env)}")
    print(f"  範例變數:")
    for key in list(dev_env.keys())[:5]:
        value = dev_env[key]
        # 隱藏敏感資訊
        if any(keyword in key.lower() for keyword in ["password", "secret", "key"]):
            value = "***"
        print(f"    {key} = {value}")


# ============================================================================
# 範例 3: 環境檔案模板生成
# ============================================================================


def example_3_template_generation():
    """環境檔案模板生成"""
    print("\n" + "=" * 80)
    print("範例 3: 環境檔案模板生成")
    print("=" * 80)

    loader = EnvLoader()

    # 生成開發環境模板
    print(f"\n生成開發環境模板...")
    dev_template = loader.generate_env_template("development")
    print(f"  檔案: {dev_template}")

    # 讀取並顯示前幾行
    with open(dev_template, "r", encoding="utf-8") as f:
        lines = f.readlines()[:20]

    print(f"\n模板內容（前 20 行）:")
    for line in lines:
        print(f"  {line.rstrip()}")


# ============================================================================
# 範例 4: 多環境配置
# ============================================================================


def example_4_multi_environment():
    """多環境配置"""
    print("\n" + "=" * 80)
    print("範例 4: 多環境配置")
    print("=" * 80)

    import os

    environments = ["development", "staging", "production"]

    for env in environments:
        print(f"\n{env.upper()} 環境:")

        # 設置環境變數
        os.environ["ENVIRONMENT"] = env

        # 重新創建配置
        settings = Settings()

        print(f"  環境: {settings.ENVIRONMENT}")
        print(f"  調試: {settings.DEBUG}")
        print(f"  測試: {settings.TESTING}")
        print(f"  資料庫: {settings.DATABASE_URL}")

    # 恢復環境變數
    if "ENVIRONMENT" in os.environ:
        del os.environ["ENVIRONMENT"]


# ============================================================================
# 範例 5: 配置驗證
# ============================================================================


def example_5_validation():
    """配置驗證"""
    print("\n" + "=" * 80)
    print("範例 5: 配置驗證")
    print("=" * 80)

    import os
    from pydantic import ValidationError

    # 測試無效配置
    test_cases = [
        {
            "name": "無效的端口號",
            "env": {"API_PORT": "-1"},
            "should_fail": True,
        },
        {
            "name": "無效的資料庫連接池大小",
            "env": {"DATABASE_POOL_SIZE": "0"},
            "should_fail": True,
        },
        {
            "name": "無效的 Redis 連接數",
            "env": {"REDIS_MAX_CONNECTIONS": "0"},
            "should_fail": True,
        },
        {
            "name": "有效的配置",
            "env": {"API_PORT": "8080"},
            "should_fail": False,
        },
    ]

    for test in test_cases:
        print(f"\n測試: {test['name']}")

        # 設置環境變數
        original_values = {}
        for key, value in test["env"].items():
            original_values[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            settings = Settings()
            if test["should_fail"]:
                print(f"  ❌ 預期失敗但成功: {test['env']}")
            else:
                print(f"  ✓ 驗證通過")
        except ValidationError as e:
            if test["should_fail"]:
                print(f"  ✓ 如預期失敗: {e.errors()[0]['msg']}")
            else:
                print(f"  ❌ 不應該失敗: {e}")
        except ValueError as e:
            if test["should_fail"]:
                print(f"  ✓ 如預期失敗: {str(e)}")
            else:
                print(f"  ❌ 不應該失敗: {e}")

        # 恢復環境變數
        for key, value in original_values.items():
            if value is None:
                if key in os.environ:
                    del os.environ[key]
            else:
                os.environ[key] = value


# ============================================================================
# 範例 6: 配置訪問模式
# ============================================================================


def example_6_access_patterns():
    """配置訪問模式"""
    print("\n" + "=" * 80)
    print("範例 6: 配置訪問模式")
    print("=" * 80)

    settings = Settings()

    print(f"\n1. 直接訪問:")
    print(f"  資料庫 URL: {settings.DATABASE_URL}")

    print(f"\n2. 獲取資料庫配置字典:")
    db_config = {
        "url": settings.DATABASE_URL,
        "pool_size": settings.DATABASE_POOL_SIZE,
        "max_overflow": settings.DATABASE_MAX_OVERFLOW,
        "echo": settings.DATABASE_ECHO,
    }
    print(f"  {db_config}")

    print(f"\n3. 獲取 Redis 配置字典:")
    redis_config = {
        "host": settings.REDIS_HOST,
        "port": settings.REDIS_PORT,
        "db": settings.REDIS_DB,
        "password": settings.REDIS_PASSWORD,
        "max_connections": settings.REDIS_MAX_CONNECTIONS,
    }
    print(f"  host: {redis_config['host']}")
    print(f"  port: {redis_config['port']}")
    print(f"  db: {redis_config['db']}")

    print(f"\n4. 獲取模型配置字典:")
    model_config = {
        "name": settings.MODEL_NAME,
        "device": settings.DEVICE,
        "max_length": settings.MAX_LENGTH,
        "temperature": settings.TEMPERATURE,
        "top_k": settings.TOP_K,
        "top_p": settings.TOP_P,
    }
    for key, value in model_config.items():
        print(f"  {key}: {value}")


# ============================================================================
# 主程序
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("配置管理範例")
    print("=" * 80)

    # 運行範例
    example_1_basic_settings()
    example_2_env_loading()
    example_3_template_generation()
    example_4_multi_environment()
    example_5_validation()
    example_6_access_patterns()

    print("\n" + "=" * 80)
    print("範例完成！")
    print("=" * 80)
    print("""
主要功能:

1. 配置加載
   - 自動從環境變數加載
   - 支援 .env 檔案
   - 提供預設值

2. 環境管理
   - 開發、測試、生產環境
   - 環境特定配置檔案
   - 環境變數優先級

3. 配置驗證
   - Pydantic 自動驗證
   - 類型檢查
   - 範圍限制

4. 模板生成
   - 自動生成 .env 模板
   - 包含所有配置選項
   - 附帶說明文檔

5. FastAPI 整合
   - 依賴注入
   - 配置端點
   - 啟動事件

使用建議:
    - 開發環境: 使用 .env.development
    - 生產環境: 使用環境變數或 .env.production
    - 敏感資訊: 永遠不要提交到版本控制
    - 模板: 可以提交 .env.example 作為參考
    """)
