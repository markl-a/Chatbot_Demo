# SSE 串流回覆系統

完整的 Server-Sent Events (SSE) 串流解決方案，支援實時文字生成和聊天回覆。

## 功能特性

- ✅ SSE 事件串流（start, token, chunk, metadata, error, end, heartbeat）
- ✅ 文字逐字串流
- ✅ Token 串流
- ✅ 模型生成串流
- ✅ 帶元數據的串流
- ✅ 心跳機制（保持長連接）
- ✅ 錯誤處理
- ✅ FastAPI 整合

## 快速開始

### 基本使用

```python
from src.medical_chatbot.streaming import SSEStreamer

streamer = SSEStreamer()

# 串流文字
async for event in streamer.stream_text("Hello World!", chunk_size=1, delay=0.05):
    if event.event_type == StreamEventType.CHUNK:
        print(event.data["content"], end="", flush=True)
```

### FastAPI 整合

```python
from fastapi import FastAPI
from src.medical_chatbot.streaming import setup_streaming_routes

app = FastAPI()
setup_streaming_routes(app)
```

啟動後可訪問：
- `GET /stream/test` - 測試串流
- `POST /stream/text` - 文字串流
- `POST /stream/chat` - 聊天串流

## SSE 事件類型

### 事件類型

- **START**: 開始生成
- **TOKEN**: 單個 token
- **CHUNK**: 文字片段
- **METADATA**: 元數據
- **ERROR**: 錯誤
- **END**: 結束生成
- **HEARTBEAT**: 心跳（保持連接）

### 事件格式

```
event: chunk
data: {"content": "Hello", "index": 0}

event: chunk
data: {"content": " World", "index": 6}

event: end
data: {"message": "生成完成"}

```

## 使用範例

### 1. 基本文字串流

```python
from src.medical_chatbot.streaming import SSEStreamer

async def example():
    streamer = SSEStreamer()
    text = "這是一個測試訊息。"

    async for event in streamer.stream_text(text, chunk_size=1, delay=0.05):
        if event.event_type == StreamEventType.CHUNK:
            print(event.data["content"], end="", flush=True)
```

### 2. Token 串流

```python
streamer = SSEStreamer()
tokens = ["你好", "，", "世界", "！"]

async for event in streamer.stream_tokens(tokens, delay=0.1):
    if event.event_type == StreamEventType.TOKEN:
        print(event.data["token"], end="")
```

### 3. SSE 格式串流

```python
streamer = SSEStreamer()

event_generator = streamer.stream_text("Hello", chunk_size=1, delay=0.05)
sse_stream = streamer.create_sse_stream(event_generator)

async for sse_data in sse_stream:
    # sse_data 是 SSE 格式的字符串
    print(sse_data, end="")
```

### 4. FastAPI 端點

```python
from fastapi import FastAPI
from src.medical_chatbot.streaming import create_sse_response, SSEStreamer

app = FastAPI()
streamer = SSEStreamer()

@app.get("/stream/hello")
async def stream_hello():
    async def generate():
        event_generator = streamer.stream_text("Hello World!")
        sse_stream = streamer.create_sse_stream(event_generator)

        async for sse_data in sse_stream:
            yield sse_data

    return create_sse_response(generate())
```

### 5. 自訂 SSE 端點

```python
from src.medical_chatbot.streaming import sse_endpoint

@app.get("/countdown")
@sse_endpoint
async def countdown():
    for i in range(10, 0, -1):
        yield f"data: {i}\\n\\n"
        await asyncio.sleep(1)
    yield "data: 完成！\\n\\n"
```

## JavaScript 客戶端

### 基本連接

```javascript
const eventSource = new EventSource('/stream/test');

// 監聽事件
eventSource.addEventListener('chunk', (e) => {
    const data = JSON.parse(e.data);
    console.log(data.content);
});

eventSource.addEventListener('end', (e) => {
    console.log('完成');
    eventSource.close();
});

eventSource.onerror = (e) => {
    console.error('錯誤', e);
    eventSource.close();
};
```

### POST 請求串流

```javascript
// 注意: EventSource 不支援 POST，需要用 fetch + ReadableStream

async function streamChat(message) {
    const response = await fetch('/stream/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message})
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
        const {done, value} = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        console.log(text);
    }
}
```

### 完整聊天客戶端

```html
<!DOCTYPE html>
<html>
<head>
    <title>SSE 聊天</title>
</head>
<body>
    <div id="messages"></div>
    <input type="text" id="input">
    <button onclick="sendMessage()">發送</button>

    <script>
        function sendMessage() {
            const message = document.getElementById('input').value;
            const messagesDiv = document.getElementById('messages');

            // 顯示訊息容器
            const botDiv = document.createElement('div');
            messagesDiv.appendChild(botDiv);

            // 建立 SSE 連接
            const eventSource = new EventSource(
                '/stream/chat?message=' + encodeURIComponent(message)
            );

            eventSource.addEventListener('chunk', (e) => {
                const data = JSON.parse(e.data);
                botDiv.textContent += data.content;
            });

            eventSource.addEventListener('token', (e) => {
                const data = JSON.parse(e.data);
                botDiv.textContent += data.token;
            });

            eventSource.addEventListener('end', (e) => {
                eventSource.close();
            });
        }
    </script>
</body>
</html>
```

## FastAPI 路由

### 測試端點

```bash
# 測試串流
curl http://localhost:8000/stream/test

# 文字串流
curl -X POST http://localhost:8000/stream/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello SSE!", "chunk_size": 1, "delay": 0.05}'

# 聊天串流
curl -X POST http://localhost:8000/stream/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好", "max_length": 100}'

# 心跳串流
curl http://localhost:8000/stream/heartbeat

# 事件示範
curl http://localhost:8000/stream/events
```

### 回覆範例

```
event: start
data: {"message": "開始生成"}

event: chunk
data: {"content": "H", "index": 0}

event: chunk
data: {"content": "e", "index": 1}

event: chunk
data: {"content": "l", "index": 2}

event: chunk
data: {"content": "l", "index": 3}

event: chunk
data: {"content": "o", "index": 4}

event: end
data: {"message": "生成完成", "total_length": 5}
```

## 心跳機制

對於長時間連接，使用心跳保持連接活躍：

```python
streamer = SSEStreamer(heartbeat_interval=30.0, enable_heartbeat=True)

event_generator = streamer.stream_text("...")
sse_stream = streamer.create_sse_stream(event_generator, enable_heartbeat=True)
```

心跳事件：
```
event: heartbeat
data: {"timestamp": 1704096000.0}
```

## 錯誤處理

```python
streamer = SSEStreamer()

async def error_generator():
    yield StreamEvent(event_type=StreamEventType.START, data={})
    raise ValueError("錯誤")

# 自動捕獲錯誤並發送錯誤事件
async for event in streamer.stream_with_error_handling(error_generator()):
    if event.event_type == StreamEventType.ERROR:
        print(f"錯誤: {event.data['error']}")
```

錯誤事件：
```
event: error
data: {"error": "錯誤訊息", "error_type": "ValueError"}

event: end
data: {"message": "串流結束"}
```

## 模型生成串流

### 支援串流的模型

如果模型支援 `generate_stream` 方法：

```python
class StreamingModel:
    async def generate_stream(self, prompt, max_length, temperature):
        """逐 token 生成"""
        for token in self.tokenize_and_generate(prompt):
            yield token
            await asyncio.sleep(0.01)

# 使用
streamer = SSEStreamer()
async for event in streamer.stream_model_generation(
    generator=model,
    prompt="你好",
    max_length=100
):
    if event.event_type == StreamEventType.TOKEN:
        print(event.data["token"], end="")
```

### 不支援串流的模型

自動模擬串流：

```python
class NormalModel:
    def generate(self, prompt, max_length, temperature):
        """一次性生成完整回覆"""
        return "完整的回覆文字"

# 自動逐字元串流
streamer = SSEStreamer()
async for event in streamer.stream_model_generation(
    generator=model,
    prompt="你好"
):
    # 自動將完整回覆轉換為逐字元串流
    pass
```

## 最佳實踐

### 1. 設置合理的 chunk_size 和 delay

```python
# 快速串流（適合短文字）
streamer.stream_text(text, chunk_size=1, delay=0.02)

# 中速串流（適合長文字）
streamer.stream_text(text, chunk_size=2, delay=0.05)

# 慢速串流（演示效果）
streamer.stream_text(text, chunk_size=1, delay=0.1)
```

### 2. 啟用心跳（長連接）

```python
# 啟用心跳，每 30 秒發送一次
streamer = SSEStreamer(heartbeat_interval=30.0, enable_heartbeat=True)
```

### 3. 添加元數據

```python
metadata = {
    "model": "TAIDE-LX-8B",
    "temperature": 0.7,
    "max_length": 256,
}

async for event in streamer.stream_with_metadata(content_gen(), metadata):
    # 客戶端可以獲取元數據
    pass
```

### 4. 錯誤處理

```python
# 總是包裝錯誤處理
event_generator = streamer.stream_text(...)
safe_generator = streamer.stream_with_error_handling(event_generator)

async for event in safe_generator:
    if event.event_type == StreamEventType.ERROR:
        # 處理錯誤
        pass
```

### 5. 設置正確的 headers

```python
from src.medical_chatbot.streaming import create_sse_response

headers = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",  # Nginx 禁用緩衝
}

return create_sse_response(generator, headers=headers)
```

## 常見問題

### Q: SSE 和 WebSocket 的區別？

A:
- **SSE**: 單向（服務器到客戶端），基於 HTTP，更簡單
- **WebSocket**: 雙向，獨立協議，更複雜但更靈活
- **SSE 適用於**: 實時通知、進度更新、聊天機器人回覆
- **WebSocket 適用於**: 雙向通訊、遊戲、協作編輯

### Q: 如何處理客戶端斷線？

A:
```python
async def generate():
    try:
        async for event in event_generator:
            yield event.to_sse_format()
    except asyncio.CancelledError:
        # 客戶端已斷線
        logger.info("客戶端斷線")
```

### Q: 如何在 Nginx 後面使用？

A: 禁用緩衝：
```nginx
location /stream {
    proxy_pass http://backend;
    proxy_buffering off;
    proxy_cache off;
    proxy_set_header Connection '';
    proxy_http_version 1.1;
    chunked_transfer_encoding off;
}
```

### Q: 瀏覽器兼容性？

A: SSE 支援所有現代瀏覽器：
- ✅ Chrome/Edge
- ✅ Firefox
- ✅ Safari
- ✅ Opera
- ❌ IE（不支援）

### Q: 如何限制並發連接數？

A:
```python
from fastapi import HTTPException
import asyncio

# 全局連接計數器
active_connections = 0
MAX_CONNECTIONS = 100

@app.get("/stream")
async def stream():
    global active_connections

    if active_connections >= MAX_CONNECTIONS:
        raise HTTPException(status_code=503, detail="Too many connections")

    active_connections += 1
    try:
        # 串流邏輯
        yield ...
    finally:
        active_connections -= 1
```

## 性能優化

### 1. 使用異步生成器

```python
# 好的做法
async def generate():
    for item in items:
        yield item
        await asyncio.sleep(0)  # 讓出控制權

# 避免阻塞
```

### 2. 批次發送

```python
# 減少網絡開銷
streamer.stream_text(text, chunk_size=5, delay=0.05)
```

### 3. 設置合理的心跳間隔

```python
# 不要太頻繁
streamer = SSEStreamer(heartbeat_interval=30.0)
```

## 授權

MIT License
