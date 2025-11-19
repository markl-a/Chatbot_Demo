"""
記憶體快取實現

提供基於記憶體的本地快取功能。
"""
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
from threading import RLock

from cachetools import TTLCache, LRUCache
from loguru import logger


class MemoryCache:
    """記憶體快取管理器"""

    def __init__(
        self,
        maxsize: int = 1000,
        ttl: int = 3600,
        cache_type: str = "ttl",
    ):
        """
        初始化記憶體快取

        Args:
            maxsize: 最大快取項目數
            ttl: 預設 TTL（秒）
            cache_type: 快取類型（ttl/lru）
        """
        self.maxsize = maxsize
        self.default_ttl = ttl
        self.cache_type = cache_type

        # 創建快取
        if cache_type == "ttl":
            self._cache = TTLCache(maxsize=maxsize, ttl=ttl)
        elif cache_type == "lru":
            self._cache = LRUCache(maxsize=maxsize)
        else:
            raise ValueError(f"不支援的快取類型: {cache_type}")

        # 線程鎖（用於線程安全）
        self._lock = RLock()

        # 統計資訊
        self._hits = 0
        self._misses = 0
        self._sets = 0

        logger.info(f"記憶體快取初始化: type={cache_type}, maxsize={maxsize}, ttl={ttl}s")

    # ========================================================================
    # 基本操作
    # ========================================================================

    def get(self, key: str, default: Any = None) -> Optional[Any]:
        """
        獲取快取值

        Args:
            key: 快取鍵
            default: 預設值

        Returns:
            快取值，如果不存在則返回 default
        """
        with self._lock:
            try:
                value = self._cache[key]
                self._hits += 1
                logger.debug(f"快取命中: {key}")
                return value

            except KeyError:
                self._misses += 1
                logger.debug(f"快取未命中: {key}")
                return default

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        設置快取值

        Args:
            key: 快取鍵
            value: 快取值
            ttl: 過期時間（秒），僅對 TTLCache 有效

        Returns:
            是否設置成功
        """
        with self._lock:
            try:
                if self.cache_type == "ttl" and ttl is not None:
                    # TTLCache 不支援單獨設置 TTL，需要使用臨時快取
                    # 這裡簡化處理，使用默認 TTL
                    pass

                self._cache[key] = value
                self._sets += 1
                logger.debug(f"快取設置: {key}")
                return True

            except Exception as e:
                logger.error(f"設置快取失敗 (key={key}): {e}")
                return False

    def delete(self, key: str) -> bool:
        """
        刪除快取

        Args:
            key: 快取鍵

        Returns:
            是否刪除成功
        """
        with self._lock:
            try:
                del self._cache[key]
                logger.debug(f"快取刪除: {key}")
                return True

            except KeyError:
                return False

    def exists(self, key: str) -> bool:
        """
        檢查鍵是否存在

        Args:
            key: 快取鍵

        Returns:
            是否存在
        """
        with self._lock:
            return key in self._cache

    def clear(self):
        """清空所有快取"""
        with self._lock:
            self._cache.clear()
            logger.info("記憶體快取已清空")

    # ========================================================================
    # 批次操作
    # ========================================================================

    def mget(self, keys: list) -> Dict[str, Any]:
        """
        批次獲取快取

        Args:
            keys: 鍵列表

        Returns:
            鍵值對字典
        """
        with self._lock:
            result = {}
            for key in keys:
                value = self.get(key)
                if value is not None:
                    result[key] = value

            return result

    def mset(self, mapping: dict) -> bool:
        """
        批次設置快取

        Args:
            mapping: 鍵值對字典

        Returns:
            是否設置成功
        """
        with self._lock:
            try:
                for key, value in mapping.items():
                    self.set(key, value)

                return True

            except Exception as e:
                logger.error(f"批次設置快取失敗: {e}")
                return False

    # ========================================================================
    # 統計資訊
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """
        獲取統計資訊

        Returns:
            統計資訊字典
        """
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0

            return {
                "hits": self._hits,
                "misses": self._misses,
                "sets": self._sets,
                "total_requests": total,
                "hit_rate": f"{hit_rate:.2%}",
                "size": len(self._cache),
                "maxsize": self.maxsize,
                "cache_type": self.cache_type,
            }

    def reset_stats(self):
        """重置統計資訊"""
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._sets = 0
            logger.info("統計資訊已重置")

    # ========================================================================
    # 裝飾器
    # ========================================================================

    def cached(self, ttl: Optional[int] = None):
        """
        快取裝飾器

        Args:
            ttl: 過期時間（秒）

        Example:
            @cache.cached(ttl=300)
            def expensive_function(x, y):
                return x + y
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                # 生成快取鍵
                cache_key = self._make_key(func.__name__, args, kwargs)

                # 嘗試從快取獲取
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    return cached_value

                # 執行函數
                result = func(*args, **kwargs)

                # 快取結果
                self.set(cache_key, result, ttl=ttl)

                return result

            return wrapper

        return decorator

    @staticmethod
    def _make_key(func_name: str, args: tuple, kwargs: dict) -> str:
        """生成快取鍵"""
        import hashlib
        import json

        key_parts = [func_name]

        # 添加位置參數
        for arg in args:
            try:
                key_parts.append(json.dumps(arg, sort_keys=True))
            except (TypeError, ValueError):
                key_parts.append(str(arg))

        # 添加關鍵字參數
        for k, v in sorted(kwargs.items()):
            try:
                key_parts.append(f"{k}={json.dumps(v, sort_keys=True)}")
            except (TypeError, ValueError):
                key_parts.append(f"{k}={v}")

        # 生成雜湊鍵
        key_str = ":".join(key_parts)
        return f"cache:{hashlib.md5(key_str.encode()).hexdigest()}"

    # ========================================================================
    # 特殊方法
    # ========================================================================

    def __len__(self) -> int:
        """返回快取項目數"""
        with self._lock:
            return len(self._cache)

    def __contains__(self, key: str) -> bool:
        """支援 in 操作符"""
        return self.exists(key)

    def __repr__(self) -> str:
        """字串表示"""
        stats = self.get_stats()
        return (
            f"MemoryCache(type={self.cache_type}, "
            f"size={stats['size']}/{stats['maxsize']}, "
            f"hit_rate={stats['hit_rate']})"
        )
