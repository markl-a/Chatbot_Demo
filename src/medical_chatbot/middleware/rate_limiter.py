"""
速率限制器

實現多種速率限制策略，支援分散式環境。
"""
from typing import Optional, Tuple
from enum import Enum
from datetime import datetime, timedelta
import time
import math

from loguru import logger

from ..cache.redis_cache import RedisCache
from ..cache.memory_cache import MemoryCache
from ..utils.exceptions import RateLimitException


class RateLimitStrategy(Enum):
    """速率限制策略"""

    FIXED_WINDOW = "fixed_window"  # 固定窗口
    SLIDING_WINDOW = "sliding_window"  # 滑動窗口
    TOKEN_BUCKET = "token_bucket"  # 令牌桶


class RateLimiter:
    """速率限制器"""

    def __init__(
        self,
        cache: Optional[RedisCache] = None,
        fallback_cache: Optional[MemoryCache] = None,
        strategy: str = "sliding_window",
        default_limit: int = 60,  # 預設每分鐘 60 次
        default_window: int = 60,  # 預設窗口 60 秒
    ):
        """
        初始化速率限制器

        Args:
            cache: Redis 快取（用於分散式限制）
            fallback_cache: 記憶體快取（Redis 不可用時降級）
            strategy: 限制策略
            default_limit: 預設限制次數
            default_window: 預設時間窗口（秒）
        """
        self.cache = cache
        self.fallback_cache = fallback_cache
        self.strategy = RateLimitStrategy(strategy)
        self.default_limit = default_limit
        self.default_window = default_window

        # 如果沒有提供快取，創建記憶體快取
        if not self.cache and not self.fallback_cache:
            self.fallback_cache = MemoryCache(maxsize=10000, ttl=default_window)
            logger.warning("未提供快取實例，使用記憶體快取（不支援分散式）")

        logger.info(
            f"速率限制器初始化: strategy={strategy}, "
            f"limit={default_limit}/{default_window}s"
        )

    # ========================================================================
    # 核心方法
    # ========================================================================

    def check_limit(
        self,
        key: str,
        limit: Optional[int] = None,
        window: Optional[int] = None,
    ) -> Tuple[bool, dict]:
        """
        檢查是否超過速率限制

        Args:
            key: 限制鍵（如 IP、用戶 ID、API Key）
            limit: 限制次數（None 使用預設值）
            window: 時間窗口（秒，None 使用預設值）

        Returns:
            (是否允許, 限制資訊字典)
            限制資訊包括: allowed, limit, remaining, reset_time

        Raises:
            RateLimitException: 超過限制時拋出
        """
        limit = limit or self.default_limit
        window = window or self.default_window

        # 根據策略選擇方法
        if self.strategy == RateLimitStrategy.FIXED_WINDOW:
            return self._check_fixed_window(key, limit, window)
        elif self.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return self._check_sliding_window(key, limit, window)
        elif self.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return self._check_token_bucket(key, limit, window)
        else:
            raise ValueError(f"不支援的策略: {self.strategy}")

    def reset(self, key: str):
        """
        重置限制計數

        Args:
            key: 限制鍵
        """
        try:
            if self.cache:
                self.cache.delete(f"ratelimit:{key}*")
            if self.fallback_cache:
                self.fallback_cache.delete(f"ratelimit:{key}")

            logger.info(f"重置速率限制: {key}")

        except Exception as e:
            logger.error(f"重置速率限制失敗 (key={key}): {e}")

    # ========================================================================
    # 固定窗口策略
    # ========================================================================

    def _check_fixed_window(
        self, key: str, limit: int, window: int
    ) -> Tuple[bool, dict]:
        """
        固定窗口策略

        特點：
        - 簡單高效
        - 可能出現突刺（窗口邊界雙倍流量）

        實現：
        - 使用當前時間窗口作為鍵後綴
        - 計數器在窗口結束時過期
        """
        # 計算當前窗口
        now = int(time.time())
        window_key = now // window
        cache_key = f"ratelimit:fixed:{key}:{window_key}"

        try:
            # 優先使用 Redis
            if self.cache:
                count = self.cache.incr(cache_key)

                # 設置過期時間（窗口結束）
                if count == 1:
                    self.cache.expire(cache_key, window)

            # 降級使用記憶體快取
            elif self.fallback_cache:
                count = self.fallback_cache.get(cache_key, 0)
                count += 1
                self.fallback_cache.set(cache_key, count, ttl=window)

            else:
                raise ValueError("沒有可用的快取")

            # 計算重置時間
            reset_time = (window_key + 1) * window

            # 檢查是否超限
            allowed = count <= limit
            remaining = max(0, limit - count)

            info = {
                "allowed": allowed,
                "limit": limit,
                "remaining": remaining,
                "reset_time": reset_time,
                "retry_after": reset_time - now if not allowed else 0,
            }

            if not allowed:
                logger.warning(
                    f"速率限制超限: key={key}, count={count}/{limit}, "
                    f"retry_after={info['retry_after']}s"
                )

            return allowed, info

        except Exception as e:
            logger.error(f"固定窗口檢查失敗: {e}")
            # 失敗時允許請求（容錯）
            return True, {
                "allowed": True,
                "limit": limit,
                "remaining": limit,
                "reset_time": now + window,
                "retry_after": 0,
            }

    # ========================================================================
    # 滑動窗口策略
    # ========================================================================

    def _check_sliding_window(
        self, key: str, limit: int, window: int
    ) -> Tuple[bool, dict]:
        """
        滑動窗口策略（推薦）

        特點：
        - 平滑限流，無突刺
        - 精確控制速率
        - Redis 原生支援（ZSET）

        實現：
        - 使用 Redis Sorted Set 存儲時間戳
        - score 為時間戳，member 為唯一 ID
        - 定期清理過期記錄
        """
        cache_key = f"ratelimit:sliding:{key}"
        now = time.time()
        window_start = now - window

        try:
            # 僅支援 Redis（記憶體快取不適合此策略）
            if not self.cache:
                logger.warning("滑動窗口策略需要 Redis，降級為固定窗口")
                return self._check_fixed_window(key, limit, window)

            # 使用 Redis Pipeline 提升效能
            pipe = self.cache.redis.pipeline()

            # 1. 移除過期記錄
            pipe.zremrangebyscore(cache_key, 0, window_start)

            # 2. 計算當前窗口內的請求數
            pipe.zcard(cache_key)

            # 3. 添加當前請求
            pipe.zadd(cache_key, {f"{now}": now})

            # 4. 設置過期時間
            pipe.expire(cache_key, window)

            # 執行
            results = pipe.execute()
            count = results[1] + 1  # 加上當前請求

            # 計算重置時間（最早的請求過期時間）
            earliest = self.cache.redis.zrange(cache_key, 0, 0, withscores=True)
            if earliest:
                reset_time = int(earliest[0][1]) + window
            else:
                reset_time = int(now) + window

            # 檢查是否超限
            allowed = count <= limit
            remaining = max(0, limit - count)

            info = {
                "allowed": allowed,
                "limit": limit,
                "remaining": remaining,
                "reset_time": reset_time,
                "retry_after": max(0, int(reset_time - now)) if not allowed else 0,
            }

            if not allowed:
                # 超限時移除當前請求
                self.cache.redis.zrem(cache_key, f"{now}")

                logger.warning(
                    f"速率限制超限: key={key}, count={count}/{limit}, "
                    f"retry_after={info['retry_after']}s"
                )

            return allowed, info

        except Exception as e:
            logger.error(f"滑動窗口檢查失敗: {e}")
            # 失敗時允許請求（容錯）
            return True, {
                "allowed": True,
                "limit": limit,
                "remaining": limit,
                "reset_time": int(now) + window,
                "retry_after": 0,
            }

    # ========================================================================
    # 令牌桶策略
    # ========================================================================

    def _check_token_bucket(
        self, key: str, limit: int, window: int
    ) -> Tuple[bool, dict]:
        """
        令牌桶策略

        特點：
        - 允許突發流量
        - 長期平均速率受限
        - 更符合實際使用場景

        實現：
        - 桶容量 = limit
        - 填充速率 = limit / window
        - 使用 Redis Hash 存儲狀態
        """
        cache_key = f"ratelimit:bucket:{key}"
        now = time.time()

        try:
            # 優先使用 Redis
            if self.cache:
                # 獲取桶狀態
                bucket_data = self.cache.hgetall(cache_key)

                if bucket_data:
                    tokens = float(bucket_data.get("tokens", limit))
                    last_refill = float(bucket_data.get("last_refill", now))
                else:
                    tokens = float(limit)
                    last_refill = now

                # 計算新增令牌數
                time_passed = now - last_refill
                refill_rate = limit / window  # 每秒填充的令牌數
                new_tokens = time_passed * refill_rate

                # 更新令牌數（不超過容量）
                tokens = min(limit, tokens + new_tokens)

                # 嘗試消費 1 個令牌
                allowed = tokens >= 1.0
                if allowed:
                    tokens -= 1.0

                # 更新狀態
                self.cache.redis.hset(
                    cache_key,
                    mapping={
                        "tokens": str(tokens),
                        "last_refill": str(now),
                    },
                )
                self.cache.expire(cache_key, window * 2)  # 保留更長時間

            # 降級使用記憶體快取
            elif self.fallback_cache:
                bucket_data = self.fallback_cache.get(cache_key, {})

                tokens = bucket_data.get("tokens", limit)
                last_refill = bucket_data.get("last_refill", now)

                time_passed = now - last_refill
                refill_rate = limit / window
                new_tokens = time_passed * refill_rate

                tokens = min(limit, tokens + new_tokens)

                allowed = tokens >= 1.0
                if allowed:
                    tokens -= 1.0

                self.fallback_cache.set(
                    cache_key,
                    {"tokens": tokens, "last_refill": now},
                    ttl=window * 2,
                )

            else:
                raise ValueError("沒有可用的快取")

            # 計算剩餘令牌和重置時間
            remaining = int(tokens)
            time_to_refill = (1.0 - (tokens % 1.0)) / refill_rate if tokens < limit else 0
            reset_time = int(now + time_to_refill)

            info = {
                "allowed": allowed,
                "limit": limit,
                "remaining": remaining,
                "reset_time": reset_time,
                "retry_after": int(time_to_refill) if not allowed else 0,
            }

            if not allowed:
                logger.warning(
                    f"速率限制超限: key={key}, tokens={tokens:.2f}/{limit}, "
                    f"retry_after={info['retry_after']}s"
                )

            return allowed, info

        except Exception as e:
            logger.error(f"令牌桶檢查失敗: {e}")
            # 失敗時允許請求（容錯）
            return True, {
                "allowed": True,
                "limit": limit,
                "remaining": limit,
                "reset_time": int(now) + window,
                "retry_after": 0,
            }

    # ========================================================================
    # 工具方法
    # ========================================================================

    def get_stats(self, key: str) -> dict:
        """
        獲取限制統計

        Args:
            key: 限制鍵

        Returns:
            統計資訊字典
        """
        try:
            stats = {"key": key, "strategy": self.strategy.value}

            if self.strategy == RateLimitStrategy.FIXED_WINDOW:
                # 獲取當前窗口計數
                now = int(time.time())
                window_key = now // self.default_window
                cache_key = f"ratelimit:fixed:{key}:{window_key}"

                if self.cache:
                    count = int(self.cache.get(cache_key) or 0)
                elif self.fallback_cache:
                    count = self.fallback_cache.get(cache_key, 0)
                else:
                    count = 0

                stats["current_count"] = count

            elif self.strategy == RateLimitStrategy.SLIDING_WINDOW:
                # 獲取窗口內請求數
                cache_key = f"ratelimit:sliding:{key}"

                if self.cache:
                    count = self.cache.redis.zcard(cache_key)
                else:
                    count = 0

                stats["current_count"] = count

            elif self.strategy == RateLimitStrategy.TOKEN_BUCKET:
                # 獲取令牌桶狀態
                cache_key = f"ratelimit:bucket:{key}"

                if self.cache:
                    bucket_data = self.cache.hgetall(cache_key)
                    stats["tokens"] = float(bucket_data.get("tokens", self.default_limit))
                elif self.fallback_cache:
                    bucket_data = self.fallback_cache.get(cache_key, {})
                    stats["tokens"] = bucket_data.get("tokens", self.default_limit)
                else:
                    stats["tokens"] = self.default_limit

            return stats

        except Exception as e:
            logger.error(f"獲取限制統計失敗: {e}")
            return {"key": key, "strategy": self.strategy.value, "error": str(e)}
