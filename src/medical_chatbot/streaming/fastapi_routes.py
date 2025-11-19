"""
FastAPI SSE 串流路由

提供 SSE 端點整合。
"""
from typing import Optional, AsyncGenerator
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from loguru import logger

from .sse_streamer import SSEStreamer, StreamEvent, StreamEventType


# ============================================================================
# 請求模型
# ============================================================================


class ChatStreamRequest(BaseModel):
    """聊天串流請求"""

    message: str
    max_length: int = 256
    temperature: float = 0.7
    session_id: Optional[str] = None


class TextStreamRequest(BaseModel):
    """文字串流請求"""

    text: str
    chunk_size: int = 1
    delay: float = 0.05


# ============================================================================
# SSE Response 創建
# ============================================================================


def create_sse_response(
    event_generator: AsyncGenerator[str, None],
    headers: Optional[dict] = None,
) -> StreamingResponse:
    """
    創建 SSE 回覆

    Args:
        event_generator: SSE 事件生成器
        headers: 自訂 headers

    Returns:
        StreamingResponse

    Example:
        ```python
        @app.get("/stream")
        async def stream():
            async def generate():
                for i in range(10):
                    yield f"data: {i}\\n\\n"

            return create_sse_response(generate())
        ```
    """
    default_headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",  # Nginx 禁用緩衝
    }

    if headers:
        default_headers.update(headers)

    return StreamingResponse(
        event_generator,
        media_type="text/event-stream",
        headers=default_headers,
    )


# ============================================================================
# 串流路由創建
# ============================================================================


def create_streaming_router(
    model_generator=None,
    prefix: str = "/stream",
    tags: Optional[list] = None,
) -> APIRouter:
    """
    創建串流路由

    Args:
        model_generator: 模型生成器
        prefix: 路由前綴
        tags: 標籤

    Returns:
        APIRouter

    Example:
        ```python
        from fastapi import FastAPI
        from src.medical_chatbot.streaming import create_streaming_router

        app = FastAPI()
        router = create_streaming_router()
        app.include_router(router)
        ```
    """
    router = APIRouter(prefix=prefix, tags=tags or ["streaming"])
    streamer = SSEStreamer()

    @router.get("/test")
    async def test_stream():
        """
        測試串流端點

        Returns:
            SSE 串流
        """

        async def generate():
            """生成測試數據"""
            test_text = "這是一個測試串流訊息。Hello, this is a streaming test!"

            event_generator = streamer.stream_text(test_text, chunk_size=1, delay=0.05)
            sse_stream = streamer.create_sse_stream(event_generator)

            async for sse_data in sse_stream:
                yield sse_data

        return create_sse_response(generate())

    @router.post("/text")
    async def stream_text(request: TextStreamRequest):
        """
        串流文字

        Args:
            request: 文字串流請求

        Returns:
            SSE 串流
        """

        async def generate():
            event_generator = streamer.stream_text(
                text=request.text,
                chunk_size=request.chunk_size,
                delay=request.delay,
            )
            sse_stream = streamer.create_sse_stream(event_generator)

            async for sse_data in sse_stream:
                yield sse_data

        return create_sse_response(generate())

    @router.post("/chat")
    async def stream_chat(request: ChatStreamRequest):
        """
        串流聊天回覆

        Args:
            request: 聊天串流請求

        Returns:
            SSE 串流
        """
        if not model_generator:
            # 如果沒有模型生成器，返回模擬回覆
            async def generate():
                mock_response = f"您好！您說：「{request.message}」\n這是一個模擬的串流回覆。"

                event_generator = streamer.stream_text(mock_response, chunk_size=1, delay=0.03)
                sse_stream = streamer.create_sse_stream(event_generator)

                async for sse_data in sse_stream:
                    yield sse_data

            return create_sse_response(generate())

        # 使用模型生成器
        async def generate():
            event_generator = streamer.stream_model_generation(
                generator=model_generator,
                prompt=request.message,
                max_length=request.max_length,
                temperature=request.temperature,
            )
            sse_stream = streamer.create_sse_stream(event_generator)

            async for sse_data in sse_stream:
                yield sse_data

        return create_sse_response(generate())

    @router.get("/heartbeat")
    async def stream_with_heartbeat():
        """
        帶心跳的串流

        示範長時間連接的心跳機制。

        Returns:
            SSE 串流
        """
        import asyncio

        async def generate():
            # 創建一個長時間運行的生成器
            async def long_running_generator():
                for i in range(20):
                    yield StreamEvent(
                        event_type=StreamEventType.CHUNK,
                        data={"content": f"訊息 {i + 1}\n", "index": i},
                    )
                    await asyncio.sleep(2)  # 模擬慢速生成

            # 包裝為帶心跳的串流
            event_generator = long_running_generator()
            sse_stream = streamer.create_sse_stream(event_generator, enable_heartbeat=True)

            async for sse_data in sse_stream:
                yield sse_data

        return create_sse_response(generate())

    @router.get("/events")
    async def stream_events():
        """
        事件類型示範

        示範不同的事件類型。

        Returns:
            SSE 串流
        """
        import asyncio

        async def generate():
            # 開始事件
            yield StreamEvent(
                event_type=StreamEventType.START,
                data={"message": "開始處理"},
            ).to_sse_format()

            await asyncio.sleep(0.5)

            # 元數據事件
            yield StreamEvent(
                event_type=StreamEventType.METADATA,
                data={"model": "TAIDE-LX-8B", "temperature": 0.7},
            ).to_sse_format()

            await asyncio.sleep(0.5)

            # Token 事件
            for token in ["Hello", " ", "World", "!"]:
                yield StreamEvent(
                    event_type=StreamEventType.TOKEN,
                    data={"token": token},
                ).to_sse_format()
                await asyncio.sleep(0.3)

            # 結束事件
            yield StreamEvent(
                event_type=StreamEventType.END,
                data={"message": "處理完成"},
            ).to_sse_format()

        return create_sse_response(generate())

    return router


# ============================================================================
# 便捷設置函數
# ============================================================================


def setup_streaming_routes(
    app,
    model_generator=None,
    prefix: str = "/stream",
    tags: Optional[list] = None,
):
    """
    設置串流路由

    Args:
        app: FastAPI 應用
        model_generator: 模型生成器
        prefix: 路由前綴
        tags: 標籤

    Example:
        ```python
        from fastapi import FastAPI
        from src.medical_chatbot.streaming import setup_streaming_routes

        app = FastAPI()
        setup_streaming_routes(app)
        ```
    """
    router = create_streaming_router(
        model_generator=model_generator, prefix=prefix, tags=tags
    )
    app.include_router(router)

    logger.info(f"串流路由已註冊: {prefix}")


# ============================================================================
# 自訂串流端點裝飾器
# ============================================================================


def sse_endpoint(func):
    """
    SSE 端點裝飾器

    自動包裝函數為 SSE 回覆。

    Example:
        ```python
        from src.medical_chatbot.streaming import sse_endpoint

        @app.get("/custom-stream")
        @sse_endpoint
        async def custom_stream():
            for i in range(10):
                yield f"data: Message {i}\\n\\n"
        ```
    """
    from functools import wraps

    @wraps(func)
    async def wrapper(*args, **kwargs):
        generator = func(*args, **kwargs)
        return create_sse_response(generator)

    return wrapper
