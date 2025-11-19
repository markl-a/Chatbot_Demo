"""
快取管理器

統一 Redis 和記憶體快取的介面，提供多層快取策略。
"""
from typing import Optional, Any, Dict, List, Callable
from enum import Enum
from loguru import logger

from .redis_cache import RedisCache
from .memory_cache import MemoryCache
from ..utils.exceptions import CacheConnectionException


class CacheStrategy(Enum):
    """快取策略"""

    MEMORY_ONLY = "memory_only"  # 僅使用記憶體快取
    REDIS_ONLY = "redis_only"  # 僅使用 Redis
    MULTI_TIER = "multi_tier"  # 多層快取（記憶體 -> Redis）


class CacheManager:
    """統一快取管理器"""

    def __init__(
        self,
        strategy: str = "multi_tier",
        # 記憶體快取設定
        memory_maxsize: int = 1000,
        memory_ttl: int = 300,  # 5 分鐘
        memory_cache_type: str = "ttl",
        # Redis 設定
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None,
        # 其他設定
        auto_fallback: bool = True,  # 自動降級
    ):
        """
        初始化快取管理器

        Args:
            strategy: 快取策略（memory_only/redis_only/multi_tier）
            memory_maxsize: 記憶體快取最大容量
            memory_ttl: 記憶體快取 TTL（秒）
            memory_cache_type: 記憶體快取類型（ttl/lru）
            redis_host: Redis 主機
            redis_port: Redis 端口
            redis_db: Redis 資料庫編號
            redis_password: Redis 密碼
            auto_fallback: 是否自動降級到記憶體快取
        """
        self.strategy = CacheStrategy(strategy)
        self.auto_fallback = auto_fallback

        # 初始化記憶體快取
        self.memory_cache: Optional[MemoryCache] = None
        if self.strategy in [CacheStrategy.MEMORY_ONLY, CacheStrategy.MULTI_TIER]:
            try:
                self.memory_cache = MemoryCache(
                    maxsize=memory_maxsize,
                    ttl=memory_ttl,
                    cache_type=memory_cache_type,
                )
                logger.info(f"記憶體快取已啟用: {memory_cache_type}")
            except Exception as e:
                logger.error(f"記憶體快取初始化失敗: {e}")
                if not auto_fallback:
                    raise

        # 初始化 Redis 快取
        self.redis_cache: Optional[RedisCache] = None
        if self.strategy in [CacheStrategy.REDIS_ONLY, CacheStrategy.MULTI_TIER]:
            try:
                self.redis_cache = RedisCache(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    password=redis_password,
                )
                logger.info(f"Redis 快取已啟用: {redis_host}:{redis_port}")
            except CacheConnectionException as e:
                logger.warning(f"Redis 連接失敗，使用降級策略: {e}")
                if auto_fallback and self.memory_cache:
                    self.strategy = CacheStrategy.MEMORY_ONLY
                    logger.info("已降級為僅使用記憶體快取")
                elif not auto_fallback:
                    raise

        # 統計資訊
        self._total_gets = 0
        self._total_sets = 0
        self._memory_hits = 0
        self._redis_hits = 0
        self._misses = 0

    # ========================================================================
    # 基本操作
    # ========================================================================

    def get(self, key: str, default: Any = None) -> Optional[Any]:
        """
        獲取快取值

        根據策略：
        - MULTI_TIER: 先從記憶體獲取，未命中則從 Redis 獲取並回填記憶體
        - MEMORY_ONLY: 僅從記憶體獲取
        - REDIS_ONLY: 僅從 Redis 獲取

        Args:
            key: 快取鍵
            default: 預設值

        Returns:
            快取值或預設值
        """
        self._total_gets += 1

        try:
            # 多層快取策略
            if self.strategy == CacheStrategy.MULTI_TIER:
                # 1. 先從記憶體獲取
                if self.memory_cache:
                    value = self.memory_cache.get(key)
                    if value is not None:
                        self._memory_hits += 1
                        logger.debug(f"記憶體快取命中: {key}")
                        return value

                # 2. 從 Redis 獲取
                if self.redis_cache:
                    value = self.redis_cache.get(key)
                    if value is not None:
                        self._redis_hits += 1
                        logger.debug(f"Redis 快取命中: {key}")

                        # 回填到記憶體快取
                        if self.memory_cache:
                            self.memory_cache.set(key, value)

                        return value

            # 僅記憶體快取
            elif self.strategy == CacheStrategy.MEMORY_ONLY and self.memory_cache:
                value = self.memory_cache.get(key)
                if value is not None:
                    self._memory_hits += 1
                    return value

            # 僅 Redis 快取
            elif self.strategy == CacheStrategy.REDIS_ONLY and self.redis_cache:
                value = self.redis_cache.get(key)
                if value is not None:
                    self._redis_hits += 1
                    return value

            # 未命中
            self._misses += 1
            return default

        except Exception as e:
            logger.error(f"獲取快取失敗 (key={key}): {e}")
            self._misses += 1
            return default

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        memory_only: bool = False,
    ) -> bool:
        """
        設置快取值

        Args:
            key: 快取鍵
            value: 快取值
            ttl: 過期時間（秒）
            memory_only: 僅設置記憶體快取（用於熱點數據）

        Returns:
            是否設置成功
        """
        self._total_sets += 1
        success = False

        try:
            # 設置記憶體快取
            if self.memory_cache and (
                self.strategy in [CacheStrategy.MEMORY_ONLY, CacheStrategy.MULTI_TIER]
                or memory_only
            ):
                self.memory_cache.set(key, value, ttl=ttl)
                success = True

            # 設置 Redis 快取（除非指定 memory_only）
            if (
                not memory_only
                and self.redis_cache
                and self.strategy in [CacheStrategy.REDIS_ONLY, CacheStrategy.MULTI_TIER]
            ):
                self.redis_cache.set(key, value, ttl=ttl)
                success = True

            return success

        except Exception as e:
            logger.error(f"設置快取失敗 (key={key}): {e}")
            return False

    def delete(self, *keys: str) -> int:
        """
        刪除快取

        Args:
            *keys: 要刪除的鍵

        Returns:
            成功刪除的數量
        """
        deleted = 0

        try:
            # 從記憶體快取刪除
            if self.memory_cache and self.strategy in [
                CacheStrategy.MEMORY_ONLY,
                CacheStrategy.MULTI_TIER,
            ]:
                for key in keys:
                    if self.memory_cache.delete(key):
                        deleted += 1

            # 從 Redis 快取刪除
            if self.redis_cache and self.strategy in [
                CacheStrategy.REDIS_ONLY,
                CacheStrategy.MULTI_TIER,
            ]:
                deleted += self.redis_cache.delete(*keys)

            return deleted

        except Exception as e:
            logger.error(f"刪除快取失敗: {e}")
            return deleted

    def exists(self, key: str) -> bool:
        """
        檢查鍵是否存在

        Args:
            key: 快取鍵

        Returns:
            是否存在
        """
        try:
            # 多層快取：任一層存在即返回 True
            if self.strategy == CacheStrategy.MULTI_TIER:
                if self.memory_cache and self.memory_cache.exists(key):
                    return True
                if self.redis_cache and self.redis_cache.exists(key):
                    return True
                return False

            # 僅記憶體快取
            elif self.strategy == CacheStrategy.MEMORY_ONLY and self.memory_cache:
                return self.memory_cache.exists(key)

            # 僅 Redis 快取
            elif self.strategy == CacheStrategy.REDIS_ONLY and self.redis_cache:
                return self.redis_cache.exists(key) > 0

            return False

        except Exception as e:
            logger.error(f"檢查鍵存在性失敗 (key={key}): {e}")
            return False

    def clear(self, memory: bool = True, redis: bool = True):
        """
        清空快取

        Args:
            memory: 是否清空記憶體快取
            redis: 是否清空 Redis 快取
        """
        try:
            if memory and self.memory_cache:
                self.memory_cache.clear()
                logger.info("記憶體快取已清空")

            if redis and self.redis_cache:
                self.redis_cache.flushdb()
                logger.info("Redis 快取已清空")

        except Exception as e:
            logger.error(f"清空快取失敗: {e}")

    # ========================================================================
    # 批次操作
    # ========================================================================

    def mget(self, keys: List[str]) -> Dict[str, Any]:
        """
        批次獲取快取

        Args:
            keys: 鍵列表

        Returns:
            鍵值對字典
        """
        result = {}

        try:
            # 多層快取策略
            if self.strategy == CacheStrategy.MULTI_TIER:
                remaining_keys = keys.copy()

                # 1. 從記憶體獲取
                if self.memory_cache:
                    memory_result = self.memory_cache.mget(remaining_keys)
                    result.update(memory_result)
                    remaining_keys = [k for k in keys if k not in memory_result]

                # 2. 從 Redis 獲取剩餘的鍵
                if remaining_keys and self.redis_cache:
                    redis_values = self.redis_cache.mget(remaining_keys)
                    for key, value in zip(remaining_keys, redis_values):
                        if value is not None:
                            result[key] = value
                            # 回填到記憶體
                            if self.memory_cache:
                                self.memory_cache.set(key, value)

            # 僅記憶體快取
            elif self.strategy == CacheStrategy.MEMORY_ONLY and self.memory_cache:
                result = self.memory_cache.mget(keys)

            # 僅 Redis 快取
            elif self.strategy == CacheStrategy.REDIS_ONLY and self.redis_cache:
                values = self.redis_cache.mget(keys)
                result = {k: v for k, v in zip(keys, values) if v is not None}

            return result

        except Exception as e:
            logger.error(f"批次獲取快取失敗: {e}")
            return {}

    def mset(self, mapping: dict, ttl: Optional[int] = None) -> bool:
        """
        批次設置快取

        Args:
            mapping: 鍵值對字典
            ttl: 過期時間（秒）

        Returns:
            是否設置成功
        """
        success = False

        try:
            # 設置記憶體快取
            if self.memory_cache and self.strategy in [
                CacheStrategy.MEMORY_ONLY,
                CacheStrategy.MULTI_TIER,
            ]:
                self.memory_cache.mset(mapping)
                success = True

            # 設置 Redis 快取
            if self.redis_cache and self.strategy in [
                CacheStrategy.REDIS_ONLY,
                CacheStrategy.MULTI_TIER,
            ]:
                self.redis_cache.mset(mapping, ttl=ttl)
                success = True

            return success

        except Exception as e:
            logger.error(f"批次設置快取失敗: {e}")
            return False

    # ========================================================================
    # 進階功能
    # ========================================================================

    def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        ttl: Optional[int] = None,
    ) -> Any:
        """
        獲取快取，如果不存在則調用工廠函數生成並快取

        Args:
            key: 快取鍵
            factory: 工廠函數，用於生成值
            ttl: 過期時間（秒）

        Returns:
            快取值或新生成的值

        Example:
            >>> cache_manager.get_or_set(
            ...     "user:123",
            ...     lambda: db.get_user(123),
            ...     ttl=300
            ... )
        """
        # 嘗試獲取
        value = self.get(key)
        if value is not None:
            return value

        # 生成新值
        try:
            value = factory()
            self.set(key, value, ttl=ttl)
            return value

        except Exception as e:
            logger.error(f"工廠函數執行失敗 (key={key}): {e}")
            raise

    def invalidate_pattern(self, pattern: str) -> int:
        """
        使符合模式的所有快取失效

        Args:
            pattern: 模式（支援 * 和 ?）

        Returns:
            失效的快取數量

        Example:
            >>> cache_manager.invalidate_pattern("user:*")
        """
        deleted = 0

        try:
            # Redis 支援模式匹配
            if self.redis_cache and self.strategy in [
                CacheStrategy.REDIS_ONLY,
                CacheStrategy.MULTI_TIER,
            ]:
                deleted = self.redis_cache.delete_pattern(pattern)

            # 記憶體快取需要遍歷所有鍵（性能較差）
            # 這裡簡化處理，僅清空所有記憶體快取
            if self.memory_cache and self.strategy in [
                CacheStrategy.MEMORY_ONLY,
                CacheStrategy.MULTI_TIER,
            ]:
                logger.warning("記憶體快取不支援模式匹配，建議使用 Redis")

            return deleted

        except Exception as e:
            logger.error(f"失效模式快取失敗: {e}")
            return deleted

    def warm_up(self, mapping: dict, ttl: Optional[int] = None):
        """
        快取預熱

        Args:
            mapping: 要預熱的鍵值對字典
            ttl: 過期時間（秒）

        Example:
            >>> cache_manager.warm_up({
            ...     "hot_key_1": value1,
            ...     "hot_key_2": value2,
            ... })
        """
        try:
            self.mset(mapping, ttl=ttl)
            logger.info(f"快取預熱完成: {len(mapping)} 個鍵")

        except Exception as e:
            logger.error(f"快取預熱失敗: {e}")

    # ========================================================================
    # 統計資訊
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """
        獲取統計資訊

        Returns:
            統計資訊字典
        """
        total = self._total_gets
        total_hits = self._memory_hits + self._redis_hits
        hit_rate = total_hits / total if total > 0 else 0.0

        stats = {
            "strategy": self.strategy.value,
            "total_gets": self._total_gets,
            "total_sets": self._total_sets,
            "total_hits": total_hits,
            "memory_hits": self._memory_hits,
            "redis_hits": self._redis_hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.2%}",
        }

        # 記憶體快取統計
        if self.memory_cache:
            memory_stats = self.memory_cache.get_stats()
            stats["memory_cache"] = memory_stats

        # Redis 快取統計
        if self.redis_cache:
            try:
                redis_info = self.redis_cache.info("stats")
                stats["redis_cache"] = {
                    "keys": self.redis_cache.dbsize(),
                    "total_commands": redis_info.get("total_commands_processed", 0),
                    "keyspace_hits": redis_info.get("keyspace_hits", 0),
                    "keyspace_misses": redis_info.get("keyspace_misses", 0),
                }
            except Exception as e:
                logger.error(f"獲取 Redis 統計失敗: {e}")

        return stats

    def reset_stats(self):
        """重置統計資訊"""
        self._total_gets = 0
        self._total_sets = 0
        self._memory_hits = 0
        self._redis_hits = 0
        self._misses = 0

        if self.memory_cache:
            self.memory_cache.reset_stats()

        logger.info("統計資訊已重置")

    # ========================================================================
    # 裝飾器
    # ========================================================================

    def cached(self, ttl: Optional[int] = None, key_prefix: str = ""):
        """
        快取裝飾器

        Args:
            ttl: 過期時間（秒）
            key_prefix: 快取鍵前綴

        Example:
            @cache_manager.cached(ttl=300, key_prefix="user")
            def get_user(user_id: int):
                return db.query(User).filter(User.id == user_id).first()
        """

        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                # 生成快取鍵
                import hashlib
                import json

                key_parts = [key_prefix or func.__name__]

                for arg in args:
                    try:
                        key_parts.append(json.dumps(arg, sort_keys=True))
                    except (TypeError, ValueError):
                        key_parts.append(str(arg))

                for k, v in sorted(kwargs.items()):
                    try:
                        key_parts.append(f"{k}={json.dumps(v, sort_keys=True)}")
                    except (TypeError, ValueError):
                        key_parts.append(f"{k}={v}")

                key_str = ":".join(key_parts)
                cache_key = f"cache:{hashlib.md5(key_str.encode()).hexdigest()}"

                # 使用 get_or_set
                return self.get_or_set(cache_key, lambda: func(*args, **kwargs), ttl=ttl)

            return wrapper

        return decorator

    # ========================================================================
    # 特殊方法
    # ========================================================================

    def __repr__(self) -> str:
        """字串表示"""
        stats = self.get_stats()
        return (
            f"CacheManager(strategy={self.strategy.value}, "
            f"hit_rate={stats['hit_rate']})"
        )

    def close(self):
        """關閉所有連接"""
        if self.redis_cache:
            self.redis_cache.close()
        logger.info("快取管理器已關閉")
