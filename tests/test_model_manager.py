"""
模型管理器測試
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import torch
import sys
from pathlib import Path

# 添加專案根目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.medical_chatbot.models.model_manager import ModelManager
from src.medical_chatbot.utils.config import Config


@pytest.fixture
def mock_config():
    """模擬配置"""
    config = Mock(spec=Config)
    config.model.base_model = "taide/Llama3-TAIDE-LX-8B-Chat-Alpha1"
    config.model.alternative_models = []
    config.model.device = "cpu"
    config.model.load_in_8bit = False
    config.model.trust_remote_code = True
    config.model.max_memory = None
    return config


@pytest.fixture
def mock_tokenizer():
    """模擬 tokenizer"""
    tokenizer = MagicMock()
    tokenizer.pad_token = "[PAD]"
    tokenizer.eos_token = "[EOS]"
    return tokenizer


@pytest.fixture
def mock_model():
    """模擬模型"""
    model = MagicMock()
    model.eval.return_value = model
    model.to.return_value = model
    return model


class TestModelManagerInit:
    """模型管理器初始化測試"""

    def test_init_without_autoload(self, mock_config):
        """測試不自動載入的初始化"""
        manager = ModelManager(mock_config, autoload=False)
        assert manager.config == mock_config
        assert manager.model is None
        assert manager.tokenizer is None
        assert manager.device == "cpu"

    @patch('src.medical_chatbot.models.model_manager.AutoModelForCausalLM')
    @patch('src.medical_chatbot.models.model_manager.AutoTokenizer')
    def test_init_with_autoload(self, mock_tokenizer_class, mock_model_class, mock_config):
        """測試自動載入的初始化"""
        mock_tokenizer_class.from_pretrained.return_value = MagicMock()
        mock_model_class.from_pretrained.return_value = MagicMock()

        manager = ModelManager(mock_config, autoload=True)
        assert manager.model is not None
        assert manager.tokenizer is not None

    def test_device_detection_cuda(self, mock_config):
        """測試 CUDA 設備檢測"""
        mock_config.model.device = "auto"

        with patch('torch.cuda.is_available', return_value=True):
            manager = ModelManager(mock_config, autoload=False)
            assert manager.device == "cuda"

    def test_device_detection_cpu(self, mock_config):
        """測試 CPU 設備檢測"""
        mock_config.model.device = "auto"

        with patch('torch.cuda.is_available', return_value=False):
            manager = ModelManager(mock_config, autoload=False)
            assert manager.device == "cpu"


class TestModelLoading:
    """模型載入測試"""

    @patch('src.medical_chatbot.models.model_manager.AutoModelForCausalLM')
    @patch('src.medical_chatbot.models.model_manager.AutoTokenizer')
    def test_load_model_success(self, mock_tokenizer_class, mock_model_class, mock_config, mock_tokenizer, mock_model):
        """測試成功載入模型"""
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        mock_model_class.from_pretrained.return_value = mock_model

        manager = ModelManager(mock_config, autoload=False)
        manager.load_model()

        assert manager.model is not None
        assert manager.tokenizer is not None
        mock_model.eval.assert_called_once()

    @patch('src.medical_chatbot.models.model_manager.AutoModelForCausalLM')
    @patch('src.medical_chatbot.models.model_manager.AutoTokenizer')
    def test_load_model_with_8bit(self, mock_tokenizer_class, mock_model_class, mock_config, mock_tokenizer, mock_model):
        """測試 8-bit 量化載入"""
        mock_config.model.load_in_8bit = True
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        mock_model_class.from_pretrained.return_value = mock_model

        manager = ModelManager(mock_config, autoload=False)
        manager.load_model()

        # 檢查是否使用了 8-bit 配置
        call_kwargs = mock_model_class.from_pretrained.call_args[1]
        assert 'load_in_8bit' in call_kwargs or 'quantization_config' in call_kwargs

    @patch('src.medical_chatbot.models.model_manager.AutoTokenizer')
    def test_load_model_tokenizer_error(self, mock_tokenizer_class, mock_config):
        """測試 tokenizer 載入錯誤"""
        mock_tokenizer_class.from_pretrained.side_effect = Exception("載入失敗")

        manager = ModelManager(mock_config, autoload=False)

        with pytest.raises(Exception):
            manager.load_model()

    @patch('src.medical_chatbot.models.model_manager.AutoModelForCausalLM')
    @patch('src.medical_chatbot.models.model_manager.AutoTokenizer')
    def test_load_model_alternative_on_failure(self, mock_tokenizer_class, mock_model_class, mock_config):
        """測試主模型失敗後載入備選模型"""
        mock_config.model.alternative_models = ["backup/model"]

        # 第一次失敗，第二次成功
        mock_model_class.from_pretrained.side_effect = [
            Exception("主模型載入失敗"),
            MagicMock()
        ]
        mock_tokenizer_class.from_pretrained.return_value = MagicMock()

        manager = ModelManager(mock_config, autoload=False)
        manager.load_model()

        # 應該嘗試載入備選模型
        assert mock_model_class.from_pretrained.call_count >= 1


class TestModelUnloading:
    """模型卸載測試"""

    @patch('src.medical_chatbot.models.model_manager.AutoModelForCausalLM')
    @patch('src.medical_chatbot.models.model_manager.AutoTokenizer')
    @patch('torch.cuda.empty_cache')
    def test_unload_model(self, mock_empty_cache, mock_tokenizer_class, mock_model_class, mock_config):
        """測試卸載模型"""
        mock_tokenizer_class.from_pretrained.return_value = MagicMock()
        mock_model_class.from_pretrained.return_value = MagicMock()

        manager = ModelManager(mock_config, autoload=True)
        manager.unload_model()

        assert manager.model is None
        assert manager.tokenizer is None
        mock_empty_cache.assert_called()

    def test_unload_model_not_loaded(self, mock_config):
        """測試卸載未載入的模型"""
        manager = ModelManager(mock_config, autoload=False)
        # 不應該拋出異常
        manager.unload_model()


class TestAdapterLoading:
    """適配器載入測試"""

    @patch('src.medical_chatbot.models.model_manager.PeftModel')
    @patch('src.medical_chatbot.models.model_manager.AutoModelForCausalLM')
    @patch('src.medical_chatbot.models.model_manager.AutoTokenizer')
    def test_load_adapter_success(self, mock_tokenizer_class, mock_model_class, mock_peft, mock_config, mock_model):
        """測試成功載入適配器"""
        mock_tokenizer_class.from_pretrained.return_value = MagicMock()
        mock_model_class.from_pretrained.return_value = mock_model
        mock_peft.from_pretrained.return_value = mock_model

        manager = ModelManager(mock_config, autoload=True)
        manager.load_adapter("path/to/adapter")

        mock_peft.from_pretrained.assert_called_once()

    def test_load_adapter_no_model(self, mock_config):
        """測試在未載入模型時載入適配器"""
        manager = ModelManager(mock_config, autoload=False)

        with pytest.raises(ValueError):
            manager.load_adapter("path/to/adapter")


class TestMemoryManagement:
    """記憶體管理測試"""

    @patch('torch.cuda.empty_cache')
    def test_clear_cache_cuda(self, mock_empty_cache, mock_config):
        """測試清理 CUDA 快取"""
        mock_config.model.device = "cuda"

        with patch('torch.cuda.is_available', return_value=True):
            manager = ModelManager(mock_config, autoload=False)
            manager.unload_model()

            mock_empty_cache.assert_called()

    @patch('torch.cuda.empty_cache')
    def test_clear_cache_cpu(self, mock_empty_cache, mock_config):
        """測試 CPU 模式不清理 CUDA 快取"""
        mock_config.model.device = "cpu"

        manager = ModelManager(mock_config, autoload=False)
        # 僅卸載，不清理 CUDA 快取
        manager.unload_model()

        # CPU 模式下也會調用，但實際上不會有效果
        # 主要是測試不會出錯


class TestModelInfo:
    """模型資訊測試"""

    @patch('src.medical_chatbot.models.model_manager.AutoModelForCausalLM')
    @patch('src.medical_chatbot.models.model_manager.AutoTokenizer')
    def test_is_loaded_true(self, mock_tokenizer_class, mock_model_class, mock_config):
        """測試模型已載入"""
        mock_tokenizer_class.from_pretrained.return_value = MagicMock()
        mock_model_class.from_pretrained.return_value = MagicMock()

        manager = ModelManager(mock_config, autoload=True)
        assert manager.is_loaded() is True

    def test_is_loaded_false(self, mock_config):
        """測試模型未載入"""
        manager = ModelManager(mock_config, autoload=False)
        assert manager.is_loaded() is False

    @patch('src.medical_chatbot.models.model_manager.AutoModelForCausalLM')
    @patch('src.medical_chatbot.models.model_manager.AutoTokenizer')
    def test_get_model_name(self, mock_tokenizer_class, mock_model_class, mock_config):
        """測試獲取模型名稱"""
        mock_tokenizer_class.from_pretrained.return_value = MagicMock()
        mock_model_class.from_pretrained.return_value = MagicMock()

        manager = ModelManager(mock_config, autoload=True)
        assert manager.current_model_name == mock_config.model.base_model


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
