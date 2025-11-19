"""
端到端整合測試
"""
import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# 添加專案根目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def mock_full_stack():
    """模擬完整的堆疊"""
    with patch('transformers.AutoModelForCausalLM') as mock_model, \
         patch('transformers.AutoTokenizer') as mock_tokenizer, \
         patch('torch.cuda.is_available', return_value=False):

        # 設置 tokenizer mock
        tokenizer_instance = MagicMock()
        tokenizer_instance.pad_token = "[PAD]"
        tokenizer_instance.eos_token = "[EOS]"
        tokenizer_instance.return_value = {
            'input_ids': MagicMock(),
            'attention_mask': MagicMock()
        }
        tokenizer_instance.decode.return_value = "測試回應"
        mock_tokenizer.from_pretrained.return_value = tokenizer_instance

        # 設置 model mock
        model_instance = MagicMock()
        model_instance.eval.return_value = model_instance
        model_instance.to.return_value = model_instance
        model_instance.generate.return_value = MagicMock()
        mock_model.from_pretrained.return_value = model_instance

        yield {
            'model': mock_model,
            'tokenizer': mock_tokenizer,
            'model_instance': model_instance,
            'tokenizer_instance': tokenizer_instance
        }


class TestFullPipeline:
    """完整流程測試"""

    def test_config_to_model_loading(self, mock_full_stack):
        """測試從配置到模型載入的完整流程"""
        from src.medical_chatbot.utils.config import load_config
        from src.medical_chatbot.models.model_manager import ModelManager

        # 載入配置
        config = load_config("configs/config.yaml")
        assert config is not None

        # 載入模型
        manager = ModelManager(config, autoload=False)
        manager.load_model()

        assert manager.is_loaded()

    def test_config_to_generation(self, mock_full_stack):
        """測試從配置到生成的完整流程"""
        from src.medical_chatbot.utils.config import load_config
        from src.medical_chatbot.inference.generator import Generator

        # 載入配置
        config = load_config("configs/config.yaml")

        # 創建生成器
        generator = Generator(config)

        # 生成回應
        response = generator.generate("測試問題")
        assert isinstance(response, str)
        assert len(response) > 0

    def test_api_full_flow(self, mock_full_stack):
        """測試 API 完整流程"""
        from fastapi.testclient import TestClient
        from src.medical_chatbot.api.server import app

        client = TestClient(app)

        # 測試健康檢查
        response = client.get("/health")
        assert response.status_code == 200

        # 測試聊天
        response = client.post("/chat", json={"message": "測試問題"})
        assert response.status_code == 200
        data = response.json()
        assert "response" in data


class TestSafetyIntegration:
    """安全整合測試"""

    def test_safety_with_api(self, mock_full_stack):
        """測試安全過濾與 API 整合"""
        from fastapi.testclient import TestClient
        from src.medical_chatbot.api.server import app

        client = TestClient(app)

        # 測試緊急消息
        response = client.post("/chat", json={"message": "我胸口很痛"})
        assert response.status_code == 200
        data = response.json()
        assert "emergency" in data

    def test_safety_with_generator(self, mock_full_stack):
        """測試安全過濾與生成器整合"""
        from src.medical_chatbot.utils.config import load_config
        from src.medical_chatbot.inference.generator import Generator
        from src.medical_chatbot.utils.safety import SafetyFilter

        config = load_config("configs/config.yaml")
        generator = Generator(config)
        safety = SafetyFilter()

        # 測試正常流程
        user_input = "什麼是高血壓？"
        if safety.is_safe(user_input):
            response = generator.generate(user_input)
            assert isinstance(response, str)


class TestConfigIntegration:
    """配置整合測試"""

    def test_config_loads_all_sections(self):
        """測試配置載入所有部分"""
        from src.medical_chatbot.utils.config import load_config

        config = load_config("configs/config.yaml")

        # 檢查所有主要配置部分
        assert hasattr(config, 'model')
        assert hasattr(config, 'dataset')
        assert hasattr(config, 'training')
        assert hasattr(config, 'lora')
        assert hasattr(config, 'inference')
        assert hasattr(config, 'prompts')
        assert hasattr(config, 'api')
        assert hasattr(config, 'gradio')
        assert hasattr(config, 'logging')

    def test_config_with_components(self, mock_full_stack):
        """測試配置與各組件整合"""
        from src.medical_chatbot.utils.config import load_config
        from src.medical_chatbot.models.model_manager import ModelManager
        from src.medical_chatbot.inference.generator import Generator

        config = load_config("configs/config.yaml")

        # 測試與模型管理器整合
        manager = ModelManager(config, autoload=False)
        assert manager.config == config

        # 測試與生成器整合
        generator = Generator(config)
        assert generator.config == config


class TestMonitoringIntegration:
    """監控整合測試"""

    def test_monitoring_with_api(self, mock_full_stack):
        """測試監控與 API 整合"""
        from fastapi.testclient import TestClient
        from src.medical_chatbot.api.server import app

        client = TestClient(app)

        # 發送幾個請求
        for _ in range(3):
            client.post("/chat", json={"message": "測試"})

        # 檢查指標
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()

        assert data["total_requests"] >= 3
        assert "latency_stats" in data


class TestErrorPropagation:
    """錯誤傳播測試"""

    def test_model_error_to_api(self):
        """測試模型錯誤傳播到 API"""
        from fastapi.testclient import TestClient
        from src.medical_chatbot.api.server import app

        with patch('src.medical_chatbot.api.server.generator.generate',
                   side_effect=Exception("模型錯誤")):
            client = TestClient(app)
            response = client.post("/chat", json={"message": "測試"})

            # API 應該優雅地處理錯誤
            assert response.status_code in [500, 200]

    def test_config_error_propagation(self):
        """測試配置錯誤傳播"""
        from src.medical_chatbot.utils.config import load_config

        # 測試載入不存在的配置文件
        with pytest.raises((FileNotFoundError, Exception)):
            load_config("nonexistent_config.yaml")


class TestDataFlow:
    """資料流測試"""

    def test_data_preprocessing_to_training(self, mock_full_stack):
        """測試資料預處理到訓練的流程"""
        from src.medical_chatbot.data.preprocessor import TextPreprocessor
        from src.medical_chatbot.utils.config import load_config

        config = load_config("configs/config.yaml")
        preprocessor = TextPreprocessor(config)

        # 測試預處理
        text = "測試文本 <html>標籤</html>"
        cleaned = preprocessor.clean_text(text)

        assert isinstance(cleaned, str)
        assert "<html>" not in cleaned

    def test_user_input_to_response_flow(self, mock_full_stack):
        """測試用戶輸入到回應的完整流程"""
        from src.medical_chatbot.utils.config import load_config
        from src.medical_chatbot.utils.safety import SafetyFilter
        from src.medical_chatbot.inference.generator import Generator

        config = load_config("configs/config.yaml")
        safety = SafetyFilter()
        generator = Generator(config)

        # 模擬完整流程
        user_input = "什麼是糖尿病？"

        # 1. 安全檢查
        sanitized = safety.sanitize_input(user_input)
        assert isinstance(sanitized, str)

        # 2. 檢查是否安全
        is_safe = safety.is_safe(sanitized)
        assert is_safe is True

        # 3. 生成回應
        response = generator.generate(sanitized)
        assert isinstance(response, str)
        assert len(response) > 0


class TestMultiComponentInteraction:
    """多組件交互測試"""

    def test_logger_with_all_components(self, mock_full_stack):
        """測試日誌系統與所有組件的交互"""
        from src.medical_chatbot.utils.logger import setup_logger
        from src.medical_chatbot.utils.config import load_config

        config = load_config("configs/config.yaml")
        logger = setup_logger(config)

        # 確保日誌器可用
        assert logger is not None
        logger.info("測試日誌")

    def test_all_components_together(self, mock_full_stack):
        """測試所有組件一起工作"""
        from src.medical_chatbot.utils.config import load_config
        from src.medical_chatbot.utils.logger import setup_logger
        from src.medical_chatbot.utils.safety import SafetyFilter
        from src.medical_chatbot.models.model_manager import ModelManager
        from src.medical_chatbot.inference.generator import Generator

        # 載入配置
        config = load_config("configs/config.yaml")

        # 設置日誌
        logger = setup_logger(config)

        # 創建安全過濾器
        safety = SafetyFilter()

        # 創建模型管理器
        manager = ModelManager(config, autoload=False)
        manager.load_model()

        # 創建生成器
        generator = Generator(config)

        # 測試完整流程
        user_input = "什麼是高血壓？"
        sanitized = safety.sanitize_input(user_input)

        if safety.is_safe(sanitized):
            response = generator.generate(sanitized)
            logger.info(f"生成回應: {response[:50]}...")
            assert isinstance(response, str)


class TestConcurrency:
    """並發測試"""

    def test_concurrent_api_requests(self, mock_full_stack):
        """測試並發 API 請求"""
        from fastapi.testclient import TestClient
        from src.medical_chatbot.api.server import app
        import concurrent.futures

        client = TestClient(app)

        def make_request():
            return client.post("/chat", json={"message": "測試"})

        # 並發發送請求
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in futures]

        # 所有請求都應該成功
        assert all(r.status_code == 200 for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
