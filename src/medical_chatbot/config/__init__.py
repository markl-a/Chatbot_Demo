"""
配置管理模組

提供環境配置管理、配置驗證和熱載入功能。
"""
from .config import Settings, get_settings
from .env_loader import EnvLoader
from .fastapi_integration import (
    get_settings,
    get_database_url,
    get_redis_config,
    get_model_config,
    get_rate_limit_config,
    require_production_mode,
    require_debug_mode,
    require_testing_enabled,
    setup_config_routes,
    setup_startup_events,
    setup_shutdown_events,
    setup_config_integration,
)
from .dynamic_config import (
    DynamicConfigManager,
    ConfigValue,
    ConfigChange,
    ConfigSource,
    ConfigValidator,
    TypeValidator,
    RangeValidator,
    EnumValidator,
    get_config_manager,
    configure_config_manager,
    setup_config_routes as setup_dynamic_config_routes,
)

__all__ = [
    # 配置類
    "Settings",
    "get_settings",
    "EnvLoader",
    # FastAPI 依賴
    "get_database_url",
    "get_redis_config",
    "get_model_config",
    "get_rate_limit_config",
    # 訪問控制
    "require_production_mode",
    "require_debug_mode",
    "require_testing_enabled",
    # FastAPI 整合
    "setup_config_routes",
    "setup_startup_events",
    "setup_shutdown_events",
    "setup_config_integration",
    # 動態配置
    "DynamicConfigManager",
    "ConfigValue",
    "ConfigChange",
    "ConfigSource",
    "ConfigValidator",
    "TypeValidator",
    "RangeValidator",
    "EnumValidator",
    "get_config_manager",
    "configure_config_manager",
    "setup_dynamic_config_routes",
]
