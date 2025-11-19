"""
API 服務測試
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# 添加專案根目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.medical_chatbot.api.server import app
from src.medical_chatbot.utils.config import Config


@pytest.fixture
def mock_config():
    """模擬配置"""
    config = Mock(spec=Config)
    config.api.host = "0.0.0.0"
    config.api.port = 8000
    config.api.workers = 1
    config.api.cors_origins = ["*"]
    config.api.max_request_size = 1048576
    config.api.timeout = 300
    return config


@pytest.fixture
def mock_generator():
    """模擬生成器"""
    with patch('src.medical_chatbot.api.server.generator') as mock_gen:
        mock_gen.generate.return_value = "這是一個測試回應。"
        mock_gen.generate_conversation.return_value = "這是對話測試回應。"
        yield mock_gen


@pytest.fixture
def client(mock_generator):
    """測試客戶端"""
    return TestClient(app)


class TestHealthEndpoints:
    """健康檢查端點測試"""

    def test_root_endpoint(self, client):
        """測試根端點"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Medical Chatbot API"
        assert data["version"] == "0.2.0"
        assert "description" in data

    def test_health_basic(self, client):
        """測試基礎健康檢查"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @patch('src.medical_chatbot.api.server.generator')
    def test_health_detailed(self, mock_gen, client):
        """測試詳細健康檢查"""
        mock_gen.model_manager.model = MagicMock()

        response = client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "model_loaded" in data
        assert "uptime" in data
        assert "memory_usage" in data


class TestChatEndpoint:
    """聊天端點測試"""

    def test_chat_success(self, client, mock_generator):
        """測試成功的聊天請求"""
        payload = {
            "message": "什麼是高血壓？",
            "max_length": 256,
            "temperature": 0.7
        }

        response = client.post("/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "safe" in data
        assert "emergency" in data
        assert isinstance(data["response"], str)

    def test_chat_empty_message(self, client):
        """測試空消息"""
        payload = {"message": ""}

        response = client.post("/chat", json=payload)
        assert response.status_code == 422  # Validation error

    def test_chat_missing_message(self, client):
        """測試缺少消息"""
        payload = {}

        response = client.post("/chat", json=payload)
        assert response.status_code == 422

    @patch('src.medical_chatbot.api.server.safety_filter.is_safe')
    def test_chat_unsafe_message(self, mock_safe, client, mock_generator):
        """測試不安全的消息"""
        mock_safe.return_value = False

        payload = {"message": "測試不安全的內容"}

        response = client.post("/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["safe"] is False
        assert "警告" in data["response"] or "注意" in data["response"]

    @patch('src.medical_chatbot.api.server.safety_filter.is_emergency')
    def test_chat_emergency_message(self, mock_emergency, client, mock_generator):
        """測試緊急消息"""
        mock_emergency.return_value = True

        payload = {"message": "我胸口很痛"}

        response = client.post("/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["emergency"] is True
        assert "緊急" in data["response"] or "119" in data["response"]

    def test_chat_custom_parameters(self, client, mock_generator):
        """測試自定義參數"""
        payload = {
            "message": "測試消息",
            "max_length": 512,
            "temperature": 0.5,
            "top_p": 0.9,
            "top_k": 50
        }

        response = client.post("/chat", json=payload)
        assert response.status_code == 200

        # 驗證生成器被正確調用
        mock_generator.generate.assert_called_once()
        call_kwargs = mock_generator.generate.call_args[1]
        assert call_kwargs["max_length"] == 512
        assert call_kwargs["temperature"] == 0.5


class TestConversationEndpoint:
    """對話端點測試"""

    def test_conversation_success(self, client, mock_generator):
        """測試成功的對話請求"""
        payload = {
            "messages": [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好！我是醫療諮詢助手。"},
                {"role": "user", "content": "什麼是感冒？"}
            ]
        }

        response = client.post("/conversation", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert isinstance(data["response"], str)

    def test_conversation_empty_messages(self, client):
        """測試空消息列表"""
        payload = {"messages": []}

        response = client.post("/conversation", json=payload)
        assert response.status_code == 422

    def test_conversation_invalid_format(self, client):
        """測試無效的消息格式"""
        payload = {
            "messages": [
                {"invalid": "format"}
            ]
        }

        response = client.post("/conversation", json=payload)
        assert response.status_code == 422


class TestMetricsEndpoint:
    """指標端點測試"""

    def test_metrics_endpoint(self, client):
        """測試指標端點"""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()

        assert "total_requests" in data
        assert "active_requests" in data
        assert "latency_stats" in data

        latency = data["latency_stats"]
        assert "p50" in latency
        assert "p95" in latency
        assert "p99" in latency


class TestCORS:
    """CORS 測試"""

    def test_cors_headers(self, client):
        """測試 CORS 標頭"""
        headers = {"Origin": "http://localhost:3000"}
        response = client.options("/chat", headers=headers)

        # 檢查 CORS 標頭存在
        assert "access-control-allow-origin" in response.headers or \
               "Access-Control-Allow-Origin" in response.headers


class TestErrorHandling:
    """錯誤處理測試"""

    @patch('src.medical_chatbot.api.server.generator.generate')
    def test_internal_server_error(self, mock_generate, client):
        """測試內部伺服器錯誤"""
        mock_generate.side_effect = Exception("模擬錯誤")

        payload = {"message": "測試"}
        response = client.post("/chat", json=payload)

        # 應該返回 500 或包含錯誤信息
        assert response.status_code in [500, 200]
        if response.status_code == 200:
            data = response.json()
            assert "錯誤" in data["response"] or "error" in data["response"].lower()

    def test_invalid_json(self, client):
        """測試無效的 JSON"""
        response = client.post(
            "/chat",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422


class TestInputValidation:
    """輸入驗證測試"""

    def test_message_max_length(self, client):
        """測試消息最大長度"""
        long_message = "測試" * 10000  # 非常長的消息
        payload = {"message": long_message}

        response = client.post("/chat", json=payload)
        # 應該被接受或被拒絕，但不應該崩潰
        assert response.status_code in [200, 422, 413]

    def test_negative_parameters(self, client, mock_generator):
        """測試負數參數"""
        payload = {
            "message": "測試",
            "temperature": -1.0,
            "max_length": -100
        }

        response = client.post("/chat", json=payload)
        # 應該驗證失敗
        assert response.status_code == 422

    def test_temperature_range(self, client):
        """測試溫度範圍"""
        # 測試過高的溫度
        payload = {
            "message": "測試",
            "temperature": 10.0
        }

        response = client.post("/chat", json=payload)
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
