"""
FastAPI SSE 串流整合範例

展示如何在 FastAPI 中使用 SSE 串流。
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from src.medical_chatbot.streaming import setup_streaming_routes


def create_basic_app():
    """創建基本應用"""
    print("\n" + "=" * 80)
    print("範例 1: 基本 SSE 串流應用")
    print("=" * 80)

    app = FastAPI(title="SSE 串流範例")

    # 設置串流路由
    setup_streaming_routes(app)

    print(f"\n串流端點:")
    print(f"  GET  /stream/test - 測試串流")
    print(f"  POST /stream/text - 文字串流")
    print(f"  POST /stream/chat - 聊天串流")
    print(f"  GET  /stream/heartbeat - 帶心跳的串流")
    print(f"  GET  /stream/events - 事件類型示範")

    print(f"\n啟動應用:")
    print(f"  uvicorn 02_fastapi_streaming:app --reload")

    print(f"\n測試端點:")
    print(f"  curl http://localhost:8000/stream/test")

    return app


def create_custom_app():
    """創建自訂應用"""
    print("\n" + "=" * 80)
    print("範例 2: 自訂 SSE 端點")
    print("=" * 80)

    from fastapi import Request
    from src.medical_chatbot.streaming import create_sse_response, SSEStreamer
    import asyncio

    app = FastAPI()
    streamer = SSEStreamer()

    @app.get("/custom/countdown")
    async def countdown_stream(count: int = 10):
        """倒數計時串流"""

        async def generate():
            for i in range(count, 0, -1):
                event_data = f"data: {i}\\n\\n"
                yield event_data
                await asyncio.sleep(1)

            yield "data: 完成！\\n\\n"

        return create_sse_response(generate())

    @app.get("/custom/progress")
    async def progress_stream():
        """進度條串流"""

        async def generate():
            from src.medical_chatbot.streaming import StreamEvent, StreamEventType

            for i in range(0, 101, 10):
                yield StreamEvent(
                    event_type=StreamEventType.CHUNK,
                    data={"progress": i, "message": f"處理中... {i}%"},
                ).to_sse_format()
                await asyncio.sleep(0.5)

            yield StreamEvent(
                event_type=StreamEventType.END, data={"message": "處理完成"}
            ).to_sse_format()

        return create_sse_response(generate())

    print(f"\n自訂端點:")
    print(f"  GET /custom/countdown?count=10")
    print(f"  GET /custom/progress")

    return app


def create_chat_app():
    """創建聊天應用"""
    print("\n" + "=" * 80)
    print("範例 3: 聊天串流應用")
    print("=" * 80)

    from fastapi import Request
    from fastapi.responses import HTMLResponse
    from src.medical_chatbot.streaming import setup_streaming_routes

    app = FastAPI()

    # 設置串流路由
    setup_streaming_routes(app)

    # HTML 客戶端
    @app.get("/", response_class=HTMLResponse)
    async def index():
        """聊天界面"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>SSE 聊天串流</title>
            <meta charset="utf-8">
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                }
                #messages {
                    border: 1px solid #ddd;
                    padding: 20px;
                    height: 400px;
                    overflow-y: auto;
                    margin-bottom: 20px;
                    background-color: #f9f9f9;
                }
                .message {
                    margin: 10px 0;
                    padding: 10px;
                    border-radius: 5px;
                }
                .user-message {
                    background-color: #e3f2fd;
                    text-align: right;
                }
                .bot-message {
                    background-color: #fff;
                    border: 1px solid #ddd;
                }
                input {
                    width: 70%;
                    padding: 10px;
                    font-size: 16px;
                }
                button {
                    padding: 10px 20px;
                    font-size: 16px;
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    cursor: pointer;
                }
                button:hover {
                    background-color: #45a049;
                }
            </style>
        </head>
        <body>
            <h1>🤖 SSE 聊天串流示範</h1>
            <div id="messages"></div>
            <input type="text" id="input" placeholder="輸入訊息...">
            <button onclick="sendMessage()">發送</button>

            <script>
                const messagesDiv = document.getElementById('messages');
                const input = document.getElementById('input');

                function addMessage(content, isUser) {
                    const div = document.createElement('div');
                    div.className = 'message ' + (isUser ? 'user-message' : 'bot-message');
                    div.textContent = content;
                    messagesDiv.appendChild(div);
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                    return div;
                }

                function sendMessage() {
                    const message = input.value.trim();
                    if (!message) return;

                    // 顯示用戶訊息
                    addMessage(message, true);
                    input.value = '';

                    // 創建機器人訊息容器
                    const botDiv = addMessage('', false);

                    // 建立 SSE 連接
                    const eventSource = new EventSource(
                        '/stream/chat?message=' + encodeURIComponent(message)
                    );

                    eventSource.addEventListener('start', (e) => {
                        console.log('開始生成:', e.data);
                    });

                    eventSource.addEventListener('chunk', (e) => {
                        const data = JSON.parse(e.data);
                        botDiv.textContent += data.content;
                        messagesDiv.scrollTop = messagesDiv.scrollHeight;
                    });

                    eventSource.addEventListener('token', (e) => {
                        const data = JSON.parse(e.data);
                        botDiv.textContent += data.token;
                        messagesDiv.scrollTop = messagesDiv.scrollHeight;
                    });

                    eventSource.addEventListener('end', (e) => {
                        console.log('生成完成:', e.data);
                        eventSource.close();
                    });

                    eventSource.addEventListener('error', (e) => {
                        console.error('錯誤:', e);
                        eventSource.close();
                    });

                    eventSource.onerror = () => {
                        eventSource.close();
                    };
                }

                // Enter 鍵發送
                input.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        sendMessage();
                    }
                });
            </script>
        </body>
        </html>
        """
        return html

    print(f"\n訪問聊天界面:")
    print(f"  http://localhost:8000")

    return app


if __name__ == "__main__":
    # 創建應用
    app = create_basic_app()
    # app = create_custom_app()
    app = create_chat_app()

    print("\n" + "=" * 80)
    print("使用說明")
    print("=" * 80)
    print("""
1. 啟動應用:
   uvicorn 02_fastapi_streaming:app --reload

2. 測試串流:
   # 測試端點
   curl http://localhost:8000/stream/test

   # 文字串流
   curl -X POST http://localhost:8000/stream/text \\
     -H "Content-Type: application/json" \\
     -d '{"text": "Hello SSE!", "chunk_size": 1, "delay": 0.05}'

   # 聊天串流
   curl -X POST http://localhost:8000/stream/chat \\
     -H "Content-Type: application/json" \\
     -d '{"message": "你好", "max_length": 100}'

3. 訪問聊天界面:
   http://localhost:8000

4. JavaScript 客戶端範例:
   const eventSource = new EventSource('/stream/test');

   eventSource.addEventListener('chunk', (e) => {
       const data = JSON.parse(e.data);
       console.log(data.content);
   });

   eventSource.addEventListener('end', (e) => {
       eventSource.close();
   });
    """)
