"""
SSE 串流器

實現 Server-Sent Events 串流功能。
"""
from typing import AsyncGenerator, Optional, Dict, Any, Callable
from enum import Enum
from dataclasses import dataclass, asdict
import json
import asyncio
import time

from loguru import logger


# ============================================================================
# 串流事件類型
# ============================================================================


class StreamEventType(Enum):
    """串流事件類型"""

    START = "start"  # 開始生成
    TOKEN = "token"  # 文字 token
    CHUNK = "chunk"  # 文字片段
    METADATA = "metadata"  # 元數據
    ERROR = "error"  # 錯誤
    END = "end"  # 結束生成
    HEARTBEAT = "heartbeat"  # 心跳


# ============================================================================
# 串流事件
# ============================================================================


@dataclass
class StreamEvent:
    """串流事件"""

    event_type: StreamEventType
    data: Any
    id: Optional[str] = None
    retry: Optional[int] = None

    def to_sse_format(self) -> str:
        """
        轉換為 SSE 格式

        Returns:
            SSE 格式字符串
        """
        lines = []

        # 事件 ID
        if self.id:
            lines.append(f"id: {self.id}")

        # 重試時間
        if self.retry:
            lines.append(f"retry: {self.retry}")

        # 事件類型
        lines.append(f"event: {self.event_type.value}")

        # 數據（JSON 格式）
        if isinstance(self.data, (dict, list)):
            data_str = json.dumps(self.data, ensure_ascii=False)
        else:
            data_str = str(self.data)

        lines.append(f"data: {data_str}")

        # SSE 格式要求空行結尾
        lines.append("")
        lines.append("")

        return "\n".join(lines)


# ============================================================================
# SSE 串流器
# ============================================================================


class SSEStreamer:
    """SSE 串流器"""

    def __init__(
        self,
        heartbeat_interval: float = 30.0,
        enable_heartbeat: bool = True,
    ):
        """
        初始化 SSE 串流器

        Args:
            heartbeat_interval: 心跳間隔（秒）
            enable_heartbeat: 是否啟用心跳
        """
        self.heartbeat_interval = heartbeat_interval
        self.enable_heartbeat = enable_heartbeat

        logger.info("SSE 串流器初始化完成")

    # ========================================================================
    # 基本串流方法
    # ========================================================================

    async def stream_text(
        self,
        text: str,
        chunk_size: int = 1,
        delay: float = 0.05,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        串流文字

        Args:
            text: 要串流的文字
            chunk_size: 每次發送的字元數
            delay: 每個片段之間的延遲（秒）

        Yields:
            串流事件
        """
        # 發送開始事件
        yield StreamEvent(
            event_type=StreamEventType.START,
            data={"message": "開始生成", "total_length": len(text)},
        )

        # 逐片段發送文字
        for i in range(0, len(text), chunk_size):
            chunk = text[i : i + chunk_size]

            yield StreamEvent(
                event_type=StreamEventType.CHUNK,
                data={"content": chunk, "index": i},
            )

            # 延遲
            if delay > 0:
                await asyncio.sleep(delay)

        # 發送結束事件
        yield StreamEvent(
            event_type=StreamEventType.END,
            data={"message": "生成完成", "total_length": len(text)},
        )

    async def stream_tokens(
        self,
        tokens: list,
        delay: float = 0.05,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        串流 tokens

        Args:
            tokens: token 列表
            delay: 每個 token 之間的延遲（秒）

        Yields:
            串流事件
        """
        # 發送開始事件
        yield StreamEvent(
            event_type=StreamEventType.START,
            data={"message": "開始生成", "total_tokens": len(tokens)},
        )

        # 逐個發送 token
        for idx, token in enumerate(tokens):
            yield StreamEvent(
                event_type=StreamEventType.TOKEN,
                data={"token": token, "index": idx},
            )

            # 延遲
            if delay > 0:
                await asyncio.sleep(delay)

        # 發送結束事件
        yield StreamEvent(
            event_type=StreamEventType.END,
            data={"message": "生成完成", "total_tokens": len(tokens)},
        )

    # ========================================================================
    # 模型生成串流
    # ========================================================================

    async def stream_model_generation(
        self,
        generator,
        prompt: str,
        max_length: int = 256,
        temperature: float = 0.7,
        **kwargs,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        串流模型生成

        Args:
            generator: 模型生成器（需要支援串流）
            prompt: 提示文字
            max_length: 最大長度
            temperature: 溫度參數
            **kwargs: 其他生成參數

        Yields:
            串流事件
        """
        start_time = time.time()

        # 發送開始事件
        yield StreamEvent(
            event_type=StreamEventType.START,
            data={
                "message": "開始生成",
                "prompt": prompt,
                "max_length": max_length,
                "temperature": temperature,
            },
        )

        try:
            # 檢查生成器是否支援串流
            if hasattr(generator, "generate_stream"):
                # 使用串流生成
                async for token in generator.generate_stream(
                    prompt=prompt,
                    max_length=max_length,
                    temperature=temperature,
                    **kwargs,
                ):
                    yield StreamEvent(
                        event_type=StreamEventType.TOKEN,
                        data={"token": token},
                    )

            elif hasattr(generator, "generate"):
                # 模擬串流（非真正的串流）
                response = generator.generate(
                    prompt=prompt,
                    max_length=max_length,
                    temperature=temperature,
                    **kwargs,
                )

                # 逐字元發送
                async for event in self.stream_text(response, chunk_size=1, delay=0.02):
                    if event.event_type == StreamEventType.CHUNK:
                        yield StreamEvent(
                            event_type=StreamEventType.TOKEN,
                            data={"token": event.data["content"]},
                        )

            else:
                raise ValueError("生成器不支援 generate 或 generate_stream 方法")

        except Exception as e:
            logger.error(f"串流生成錯誤: {e}")

            # 發送錯誤事件
            yield StreamEvent(
                event_type=StreamEventType.ERROR,
                data={"error": str(e), "error_type": type(e).__name__},
            )

        # 計算生成時間
        generation_time = time.time() - start_time

        # 發送結束事件
        yield StreamEvent(
            event_type=StreamEventType.END,
            data={
                "message": "生成完成",
                "generation_time": generation_time,
            },
        )

    # ========================================================================
    # 帶元數據的串流
    # ========================================================================

    async def stream_with_metadata(
        self,
        content_generator: AsyncGenerator[str, None],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        帶元數據的串流

        Args:
            content_generator: 內容生成器
            metadata: 元數據

        Yields:
            串流事件
        """
        # 發送開始事件
        yield StreamEvent(
            event_type=StreamEventType.START,
            data={"message": "開始生成"},
        )

        # 發送元數據（如果有）
        if metadata:
            yield StreamEvent(
                event_type=StreamEventType.METADATA,
                data=metadata,
            )

        # 串流內容
        async for content in content_generator:
            yield StreamEvent(
                event_type=StreamEventType.CHUNK,
                data={"content": content},
            )

        # 發送結束事件
        yield StreamEvent(
            event_type=StreamEventType.END,
            data={"message": "生成完成"},
        )

    # ========================================================================
    # 帶心跳的串流
    # ========================================================================

    async def stream_with_heartbeat(
        self,
        content_generator: AsyncGenerator[StreamEvent, None],
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        帶心跳的串流

        定期發送心跳事件以保持連接。

        Args:
            content_generator: 內容生成器

        Yields:
            串流事件
        """
        last_heartbeat = time.time()

        async for event in content_generator:
            # 發送內容事件
            yield event

            # 檢查是否需要發送心跳
            if self.enable_heartbeat:
                current_time = time.time()
                if current_time - last_heartbeat > self.heartbeat_interval:
                    yield StreamEvent(
                        event_type=StreamEventType.HEARTBEAT,
                        data={"timestamp": current_time},
                    )
                    last_heartbeat = current_time

    # ========================================================================
    # 錯誤處理
    # ========================================================================

    async def stream_with_error_handling(
        self,
        content_generator: AsyncGenerator[StreamEvent, None],
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        帶錯誤處理的串流

        Args:
            content_generator: 內容生成器

        Yields:
            串流事件
        """
        try:
            async for event in content_generator:
                yield event

        except asyncio.CancelledError:
            logger.warning("串流被取消")
            yield StreamEvent(
                event_type=StreamEventType.ERROR,
                data={"error": "串流被取消", "error_type": "CancelledError"},
            )

        except Exception as e:
            logger.error(f"串流錯誤: {e}")
            yield StreamEvent(
                event_type=StreamEventType.ERROR,
                data={"error": str(e), "error_type": type(e).__name__},
            )

        finally:
            # 確保發送結束事件
            yield StreamEvent(
                event_type=StreamEventType.END,
                data={"message": "串流結束"},
            )

    # ========================================================================
    # 便捷方法
    # ========================================================================

    async def create_sse_stream(
        self,
        content_generator: AsyncGenerator[StreamEvent, None],
        enable_heartbeat: bool = None,
    ) -> AsyncGenerator[str, None]:
        """
        創建 SSE 串流

        將事件生成器轉換為 SSE 格式的字符串串流。

        Args:
            content_generator: 內容生成器
            enable_heartbeat: 是否啟用心跳（None 使用預設值）

        Yields:
            SSE 格式的字符串
        """
        if enable_heartbeat is None:
            enable_heartbeat = self.enable_heartbeat

        # 添加心跳（如果啟用）
        if enable_heartbeat:
            generator = self.stream_with_heartbeat(content_generator)
        else:
            generator = content_generator

        # 添加錯誤處理
        generator = self.stream_with_error_handling(generator)

        # 轉換為 SSE 格式
        async for event in generator:
            yield event.to_sse_format()

    # ========================================================================
    # 自訂生成器包裝
    # ========================================================================

    async def wrap_generator(
        self,
        generator_func: Callable,
        *args,
        **kwargs,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        包裝自訂生成器

        Args:
            generator_func: 生成器函數
            *args: 位置參數
            **kwargs: 關鍵字參數

        Yields:
            串流事件
        """
        # 發送開始事件
        yield StreamEvent(
            event_type=StreamEventType.START,
            data={"message": "開始生成"},
        )

        try:
            # 執行生成器函數
            result = generator_func(*args, **kwargs)

            # 處理同步或異步生成器
            if hasattr(result, "__aiter__"):
                # 異步生成器
                async for item in result:
                    yield StreamEvent(
                        event_type=StreamEventType.CHUNK,
                        data={"content": item},
                    )
            elif hasattr(result, "__iter__"):
                # 同步生成器
                for item in result:
                    yield StreamEvent(
                        event_type=StreamEventType.CHUNK,
                        data={"content": item},
                    )
                    await asyncio.sleep(0)  # 讓出控制權
            else:
                # 單一結果
                yield StreamEvent(
                    event_type=StreamEventType.CHUNK,
                    data={"content": result},
                )

        except Exception as e:
            logger.error(f"生成器執行錯誤: {e}")
            yield StreamEvent(
                event_type=StreamEventType.ERROR,
                data={"error": str(e)},
            )

        # 發送結束事件
        yield StreamEvent(
            event_type=StreamEventType.END,
            data={"message": "生成完成"},
        )


# ============================================================================
# 便捷函數
# ============================================================================


async def create_text_stream(
    text: str,
    chunk_size: int = 1,
    delay: float = 0.05,
) -> AsyncGenerator[str, None]:
    """
    創建簡單的文字串流

    Args:
        text: 要串流的文字
        chunk_size: 每次發送的字元數
        delay: 延遲（秒）

    Yields:
        SSE 格式的字符串
    """
    streamer = SSEStreamer()
    event_generator = streamer.stream_text(text, chunk_size, delay)
    sse_stream = streamer.create_sse_stream(event_generator, enable_heartbeat=False)

    async for sse_data in sse_stream:
        yield sse_data
