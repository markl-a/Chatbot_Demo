"""
Redis 快取實現

提供基於 Redis 的分散式快取功能。
"""
from typing import Optional, Any, List
import json
import pickle
from datetime import timedelta

import redis
from loguru import logger

from ..utils.exceptions import CacheConnectionException, CacheOperationException


class RedisCache:
    """Redis 快取管理器"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        decode_responses: bool = True,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        retry_on_timeout: bool = True,
        max_connections: int = 50,
    ):
        """
        初始化 Redis 快取

        Args:
            host: Redis 主機地址
            port: Redis 端口
            db: 資料庫編號
            password: 密碼
            decode_responses: 是否自動解碼響應
            socket_timeout: Socket 超時時間
            socket_connect_timeout: 連接超時時間
            retry_on_timeout: 超時時是否重試
            max_connections: 最大連接數
        """
        try:
            # 創建連接池
            self.pool = redis.ConnectionPool(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=decode_responses,
                socket_timeout=socket_timeout,
                socket_connect_timeout=socket_connect_timeout,
                retry_on_timeout=retry_on_timeout,
                max_connections=max_connections,
            )

            # 創建 Redis 客戶端
            self.redis = redis.Redis(connection_pool=self.pool)

            # 測試連接
            self.redis.ping()

            logger.info(f"Redis 連接成功: {host}:{port}/{db}")

        except redis.ConnectionError as e:
            logger.error(f"Redis 連接失敗: {e}")
            raise CacheConnectionException(f"無法連接到 Redis: {str(e)}")

        except Exception as e:
            logger.error(f"Redis 初始化失敗: {e}")
            raise CacheConnectionException(f"Redis 初始化失敗: {str(e)}")

    # ========================================================================
    # 基本操作
    # ========================================================================

    def get(self, key: str) -> Optional[Any]:
        """
        獲取快取值

        Args:
            key: 快取鍵

        Returns:
            快取值，如果不存在則返回 None
        """
        try:
            value = self.redis.get(key)

            if value is None:
                return None

            # 嘗試 JSON 反序列化
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except Exception as e:
            logger.error(f"獲取快取失敗 (key={key}): {e}")
            raise CacheOperationException(f"獲取快取失敗: {str(e)}", operation="get")

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """
        設置快取值

        Args:
            key: 快取鍵
            value: 快取值
            ttl: 過期時間（秒），None 表示永不過期
            nx: 僅當 key 不存在時設置
            xx: 僅當 key 存在時設置

        Returns:
            是否設置成功
        """
        try:
            # 序列化值
            if isinstance(value, (dict, list, tuple)):
                value = json.dumps(value, ensure_ascii=False)
            elif not isinstance(value, (str, bytes, int, float)):
                value = json.dumps(value, ensure_ascii=False)

            # 設置快取
            return self.redis.set(key, value, ex=ttl, nx=nx, xx=xx)

        except Exception as e:
            logger.error(f"設置快取失敗 (key={key}): {e}")
            raise CacheOperationException(f"設置快取失敗: {str(e)}", operation="set")

    def delete(self, *keys: str) -> int:
        """
        刪除快取

        Args:
            *keys: 要刪除的鍵

        Returns:
            成功刪除的數量
        """
        try:
            return self.redis.delete(*keys)

        except Exception as e:
            logger.error(f"刪除快取失敗: {e}")
            raise CacheOperationException(f"刪除快取失敗: {str(e)}", operation="delete")

    def exists(self, *keys: str) -> int:
        """
        檢查鍵是否存在

        Args:
            *keys: 要檢查的鍵

        Returns:
            存在的鍵數量
        """
        try:
            return self.redis.exists(*keys)

        except Exception as e:
            logger.error(f"檢查鍵存在性失敗: {e}")
            raise CacheOperationException(f"檢查失敗: {str(e)}", operation="exists")

    def expire(self, key: str, seconds: int) -> bool:
        """
        設置過期時間

        Args:
            key: 鍵
            seconds: 秒數

        Returns:
            是否設置成功
        """
        try:
            return self.redis.expire(key, seconds)

        except Exception as e:
            logger.error(f"設置過期時間失敗 (key={key}): {e}")
            raise CacheOperationException(f"設置過期失敗: {str(e)}", operation="expire")

    def ttl(self, key: str) -> int:
        """
        獲取剩餘過期時間

        Args:
            key: 鍵

        Returns:
            剩餘秒數，-1 表示永不過期，-2 表示鍵不存在
        """
        try:
            return self.redis.ttl(key)

        except Exception as e:
            logger.error(f"獲取 TTL 失敗 (key={key}): {e}")
            raise CacheOperationException(f"獲取 TTL 失敗: {str(e)}", operation="ttl")

    # ========================================================================
    # 進階操作
    # ========================================================================

    def mget(self, keys: List[str]) -> List[Optional[Any]]:
        """
        批次獲取快取

        Args:
            keys: 鍵列表

        Returns:
            值列表
        """
        try:
            values = self.redis.mget(keys)

            # 反序列化
            result = []
            for value in values:
                if value is None:
                    result.append(None)
                else:
                    try:
                        result.append(json.loads(value))
                    except (json.JSONDecodeError, TypeError):
                        result.append(value)

            return result

        except Exception as e:
            logger.error(f"批次獲取快取失敗: {e}")
            raise CacheOperationException(f"批次獲取失敗: {str(e)}", operation="mget")

    def mset(self, mapping: dict, ttl: Optional[int] = None) -> bool:
        """
        批次設置快取

        Args:
            mapping: 鍵值對字典
            ttl: 過期時間（秒）

        Returns:
            是否設置成功
        """
        try:
            # 序列化值
            serialized = {}
            for key, value in mapping.items():
                if isinstance(value, (dict, list, tuple)):
                    serialized[key] = json.dumps(value, ensure_ascii=False)
                else:
                    serialized[key] = value

            # 批次設置
            result = self.redis.mset(serialized)

            # 設置過期時間
            if ttl:
                pipeline = self.redis.pipeline()
                for key in mapping.keys():
                    pipeline.expire(key, ttl)
                pipeline.execute()

            return result

        except Exception as e:
            logger.error(f"批次設置快取失敗: {e}")
            raise CacheOperationException(f"批次設置失敗: {str(e)}", operation="mset")

    def incr(self, key: str, amount: int = 1) -> int:
        """
        增加計數器

        Args:
            key: 鍵
            amount: 增加量

        Returns:
            增加後的值
        """
        try:
            return self.redis.incrby(key, amount)

        except Exception as e:
            logger.error(f"增加計數器失敗 (key={key}): {e}")
            raise CacheOperationException(f"增加失敗: {str(e)}", operation="incr")

    def decr(self, key: str, amount: int = 1) -> int:
        """
        減少計數器

        Args:
            key: 鍵
            amount: 減少量

        Returns:
            減少後的值
        """
        try:
            return self.redis.decrby(key, amount)

        except Exception as e:
            logger.error(f"減少計數器失敗 (key={key}): {e}")
            raise CacheOperationException(f"減少失敗: {str(e)}", operation="decr")

    # ========================================================================
    # Hash 操作
    # ========================================================================

    def hget(self, name: str, key: str) -> Optional[Any]:
        """獲取 hash 欄位值"""
        try:
            value = self.redis.hget(name, key)

            if value is None:
                return None

            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except Exception as e:
            logger.error(f"獲取 hash 欄位失敗: {e}")
            raise CacheOperationException(f"獲取失敗: {str(e)}", operation="hget")

    def hset(self, name: str, key: str, value: Any) -> int:
        """設置 hash 欄位值"""
        try:
            if isinstance(value, (dict, list, tuple)):
                value = json.dumps(value, ensure_ascii=False)

            return self.redis.hset(name, key, value)

        except Exception as e:
            logger.error(f"設置 hash 欄位失敗: {e}")
            raise CacheOperationException(f"設置失敗: {str(e)}", operation="hset")

    def hgetall(self, name: str) -> dict:
        """獲取 hash 所有欄位"""
        try:
            data = self.redis.hgetall(name)

            # 反序列化
            result = {}
            for key, value in data.items():
                try:
                    result[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    result[key] = value

            return result

        except Exception as e:
            logger.error(f"獲取 hash 所有欄位失敗: {e}")
            raise CacheOperationException(f"獲取失敗: {str(e)}", operation="hgetall")

    # ========================================================================
    # List 操作
    # ========================================================================

    def lpush(self, key: str, *values: Any) -> int:
        """從左側推入列表"""
        try:
            serialized = [
                json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                for v in values
            ]
            return self.redis.lpush(key, *serialized)

        except Exception as e:
            logger.error(f"列表推入失敗: {e}")
            raise CacheOperationException(f"推入失敗: {str(e)}", operation="lpush")

    def rpush(self, key: str, *values: Any) -> int:
        """從右側推入列表"""
        try:
            serialized = [
                json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                for v in values
            ]
            return self.redis.rpush(key, *serialized)

        except Exception as e:
            logger.error(f"列表推入失敗: {e}")
            raise CacheOperationException(f"推入失敗: {str(e)}", operation="rpush")

    def lrange(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """獲取列表範圍"""
        try:
            values = self.redis.lrange(key, start, end)

            # 反序列化
            result = []
            for value in values:
                try:
                    result.append(json.loads(value))
                except (json.JSONDecodeError, TypeError):
                    result.append(value)

            return result

        except Exception as e:
            logger.error(f"獲取列表範圍失敗: {e}")
            raise CacheOperationException(f"獲取失敗: {str(e)}", operation="lrange")

    # ========================================================================
    # 模式匹配和清理
    # ========================================================================

    def keys(self, pattern: str = "*") -> List[str]:
        """
        獲取符合模式的所有鍵

        Args:
            pattern: 模式，支援 * 和 ?

        Returns:
            鍵列表
        """
        try:
            return [key.decode() if isinstance(key, bytes) else key
                    for key in self.redis.keys(pattern)]

        except Exception as e:
            logger.error(f"獲取鍵列表失敗: {e}")
            raise CacheOperationException(f"獲取失敗: {str(e)}", operation="keys")

    def scan_iter(self, match: str = "*", count: int = 100):
        """
        迭代掃描鍵（推薦用於大量鍵）

        Args:
            match: 匹配模式
            count: 每次掃描的數量

        Yields:
            符合模式的鍵
        """
        try:
            for key in self.redis.scan_iter(match=match, count=count):
                yield key.decode() if isinstance(key, bytes) else key

        except Exception as e:
            logger.error(f"掃描鍵失敗: {e}")
            raise CacheOperationException(f"掃描失敗: {str(e)}", operation="scan_iter")

    def delete_pattern(self, pattern: str) -> int:
        """
        刪除符合模式的所有鍵

        Args:
            pattern: 模式

        Returns:
            刪除的鍵數量
        """
        try:
            keys = list(self.scan_iter(match=pattern))

            if keys:
                return self.redis.delete(*keys)

            return 0

        except Exception as e:
            logger.error(f"刪除模式鍵失敗: {e}")
            raise CacheOperationException(f"刪除失敗: {str(e)}", operation="delete_pattern")

    def flushdb(self) -> bool:
        """清空當前資料庫"""
        try:
            return self.redis.flushdb()

        except Exception as e:
            logger.error(f"清空資料庫失敗: {e}")
            raise CacheOperationException(f"清空失敗: {str(e)}", operation="flushdb")

    # ========================================================================
    # 工具方法
    # ========================================================================

    def ping(self) -> bool:
        """測試連接"""
        try:
            return self.redis.ping()

        except Exception as e:
            logger.error(f"Ping 失敗: {e}")
            return False

    def info(self, section: Optional[str] = None) -> dict:
        """獲取 Redis 資訊"""
        try:
            return self.redis.info(section)

        except Exception as e:
            logger.error(f"獲取資訊失敗: {e}")
            raise CacheOperationException(f"獲取資訊失敗: {str(e)}", operation="info")

    def dbsize(self) -> int:
        """獲取鍵數量"""
        try:
            return self.redis.dbsize()

        except Exception as e:
            logger.error(f"獲取資料庫大小失敗: {e}")
            raise CacheOperationException(f"獲取失敗: {str(e)}", operation="dbsize")

    def close(self):
        """關閉連接"""
        try:
            self.redis.close()
            logger.info("Redis 連接已關閉")

        except Exception as e:
            logger.error(f"關閉連接失敗: {e}")
