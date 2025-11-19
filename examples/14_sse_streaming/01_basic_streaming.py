"""
基本 SSE 串流範例

展示如何使用 SSE 串流功能。
"""
import sys
from pathlib import Path
import asyncio

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.medical_chatbot.streaming import SSEStreamer, StreamEvent, StreamEventType


async def example_1_basic_text_stream():
    """基本文字串流"""
    print("\n" + "=" * 80)
    print("範例 1: 基本文字串流")
    print("=" * 80)

    streamer = SSEStreamer()
    text = "這是一個測試訊息，將會逐字顯示。"

    print(f"\n原始文字: {text}")
    print(f"\n串流輸出:")

    async for event in streamer.stream_text(text, chunk_size=1, delay=0.05):
        if event.event_type == StreamEventType.CHUNK:
            print(event.data["content"], end="", flush=True)
        elif event.event_type == StreamEventType.END:
            print(f"\n\n✓ {event.data['message']}")


async def example_2_sse_format():
    """SSE 格式輸出"""
    print("\n" + "=" * 80)
    print("範例 2: SSE 格式輸出")
    print("=" * 80)

    streamer = SSEStreamer()
    text = "Hello World!"

    print(f"\nSSE 格式串流:")
    print("-" * 40)

    event_generator = streamer.stream_text(text, chunk_size=2, delay=0.1)
    sse_stream = streamer.create_sse_stream(event_generator, enable_heartbeat=False)

    async for sse_data in sse_stream:
        print(sse_data, end="")


async def example_3_tokens_stream():
    """Token 串流"""
    print("\n" + "=" * 80)
    print("範例 3: Token 串流")
    print("=" * 80)

    streamer = SSEStreamer()
    tokens = ["你好", "，", "這是", "一個", "token", "串流", "範例", "。"]

    print(f"\nTokens: {tokens}")
    print(f"\n串流輸出:")

    async for event in streamer.stream_tokens(tokens, delay=0.2):
        if event.event_type == StreamEventType.TOKEN:
            print(event.data["token"], end="", flush=True)
        elif event.event_type == StreamEventType.END:
            print(f"\n\n✓ {event.data['message']}")


async def example_4_with_metadata():
    """帶元數據的串流"""
    print("\n" + "=" * 80)
    print("範例 4: 帶元數據的串流")
    print("=" * 80)

    streamer = SSEStreamer()

    async def content_gen():
        """內容生成器"""
        for word in ["Hello", "World", "SSE", "Streaming"]:
            yield word + " "
            await asyncio.sleep(0.2)

    metadata = {
        "model": "TAIDE-LX-8B",
        "temperature": 0.7,
        "timestamp": "2024-01-01T12:00:00",
    }

    print(f"\n元數據: {metadata}")
    print(f"\n串流輸出:")

    async for event in streamer.stream_with_metadata(content_gen(), metadata):
        if event.event_type == StreamEventType.METADATA:
            print(f"\n[元數據] {event.data}")
        elif event.event_type == StreamEventType.CHUNK:
            print(event.data["content"], end="", flush=True)
        elif event.event_type == StreamEventType.END:
            print(f"\n\n✓ {event.data['message']}")


async def example_5_error_handling():
    """錯誤處理"""
    print("\n" + "=" * 80)
    print("範例 5: 錯誤處理")
    print("=" * 80)

    streamer = SSEStreamer()

    async def error_generator():
        """會拋出錯誤的生成器"""
        yield StreamEvent(
            event_type=StreamEventType.START, data={"message": "開始處理"}
        )

        yield StreamEvent(
            event_type=StreamEventType.CHUNK, data={"content": "處理中..."}
        )

        # 模擬錯誤
        raise ValueError("模擬的錯誤")

    print(f"\n串流輸出（帶錯誤處理）:")

    async for event in streamer.stream_with_error_handling(error_generator()):
        if event.event_type == StreamEventType.CHUNK:
            print(event.data["content"])
        elif event.event_type == StreamEventType.ERROR:
            print(f"\n✗ 錯誤: {event.data['error']}")
        elif event.event_type == StreamEventType.END:
            print(f"✓ {event.data['message']}")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("SSE 串流範例")
    print("=" * 80)

    # 運行範例
    asyncio.run(example_1_basic_text_stream())
    asyncio.run(example_2_sse_format())
    asyncio.run(example_3_tokens_stream())
    asyncio.run(example_4_with_metadata())
    asyncio.run(example_5_error_handling())

    print("\n" + "=" * 80)
    print("範例完成！")
    print("=" * 80)
