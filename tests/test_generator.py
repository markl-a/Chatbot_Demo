"""
推理生成器測試
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import torch
import sys
from pathlib import Path

# 添加專案根目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.medical_chatbot.inference.generator import Generator
from src.medical_chatbot.utils.config import Config


@pytest.fixture
def mock_config():
    """模擬配置"""
    config = Mock(spec=Config)
    config.inference.max_length = 256
    config.inference.temperature = 0.7
    config.inference.top_p = 0.9
    config.inference.top_k = 50
    config.inference.repetition_penalty = 1.1
    config.inference.do_sample = True
    config.prompts.system_prompt = "你是醫療助手"
    config.prompts.user_template = "使用者: {input}"
    config.prompts.assistant_template = "助手: {output}"
    return config


@pytest.fixture
def mock_model_manager():
    """模擬模型管理器"""
    manager = MagicMock()
    manager.model = MagicMock()
    manager.tokenizer = MagicMock()
    manager.device = "cpu"
    manager.is_loaded.return_value = True
    return manager


@pytest.fixture
def generator(mock_config, mock_model_manager):
    """生成器實例"""
    with patch('src.medical_chatbot.inference.generator.ModelManager', return_value=mock_model_manager):
        gen = Generator(mock_config)
        gen.model_manager = mock_model_manager
        return gen


class TestGeneratorInit:
    """生成器初始化測試"""

    def test_init_success(self, mock_config, mock_model_manager):
        """測試成功初始化"""
        with patch('src.medical_chatbot.inference.generator.ModelManager', return_value=mock_model_manager):
            gen = Generator(mock_config)
            assert gen.config == mock_config
            assert gen.model_manager is not None

    def test_init_loads_model(self, mock_config, mock_model_manager):
        """測試初始化時載入模型"""
        with patch('src.medical_chatbot.inference.generator.ModelManager', return_value=mock_model_manager):
            Generator(mock_config)
            mock_model_manager.is_loaded.assert_called()


class TestSingleTurnGeneration:
    """單輪生成測試"""

    def test_generate_basic(self, generator, mock_model_manager):
        """測試基本生成"""
        # 設置 tokenizer 返回值
        mock_model_manager.tokenizer.return_value = {
            'input_ids': torch.tensor([[1, 2, 3]]),
            'attention_mask': torch.tensor([[1, 1, 1]])
        }

        # 設置模型生成返回值
        mock_model_manager.model.generate.return_value = torch.tensor([[1, 2, 3, 4, 5]])

        # 設置解碼返回值
        mock_model_manager.tokenizer.decode.return_value = "這是生成的回應。"

        result = generator.generate("測試問題")

        assert isinstance(result, str)
        assert len(result) > 0
        mock_model_manager.model.generate.assert_called_once()

    def test_generate_with_custom_params(self, generator, mock_model_manager):
        """測試使用自定義參數生成"""
        mock_model_manager.tokenizer.return_value = {
            'input_ids': torch.tensor([[1, 2, 3]]),
            'attention_mask': torch.tensor([[1, 1, 1]])
        }
        mock_model_manager.model.generate.return_value = torch.tensor([[1, 2, 3, 4, 5]])
        mock_model_manager.tokenizer.decode.return_value = "回應"

        result = generator.generate(
            "測試",
            max_length=512,
            temperature=0.5,
            top_p=0.95,
            top_k=40
        )

        assert isinstance(result, str)

        # 檢查參數是否正確傳遞
        call_kwargs = mock_model_manager.model.generate.call_args[1]
        assert call_kwargs['max_length'] == 512
        assert call_kwargs['temperature'] == 0.5
        assert call_kwargs['top_p'] == 0.95
        assert call_kwargs['top_k'] == 40

    def test_generate_empty_input(self, generator):
        """測試空輸入"""
        with pytest.raises(ValueError):
            generator.generate("")

    def test_generate_model_not_loaded(self, mock_config):
        """測試模型未載入"""
        mock_manager = MagicMock()
        mock_manager.is_loaded.return_value = False

        with patch('src.medical_chatbot.inference.generator.ModelManager', return_value=mock_manager):
            gen = Generator(mock_config)

            with pytest.raises(RuntimeError):
                gen.generate("測試")


class TestMultiTurnConversation:
    """多輪對話測試"""

    def test_conversation_basic(self, generator, mock_model_manager):
        """測試基本對話"""
        mock_model_manager.tokenizer.return_value = {
            'input_ids': torch.tensor([[1, 2, 3]]),
            'attention_mask': torch.tensor([[1, 1, 1]])
        }
        mock_model_manager.model.generate.return_value = torch.tensor([[1, 2, 3, 4, 5]])
        mock_model_manager.tokenizer.decode.return_value = "對話回應"

        messages = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！"},
            {"role": "user", "content": "什麼是感冒？"}
        ]

        result = generator.generate_conversation(messages)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_conversation_empty(self, generator):
        """測試空對話歷史"""
        with pytest.raises(ValueError):
            generator.generate_conversation([])

    def test_conversation_invalid_format(self, generator):
        """測試無效的對話格式"""
        messages = [
            {"invalid": "format"}
        ]

        with pytest.raises((KeyError, ValueError)):
            generator.generate_conversation(messages)

    def test_conversation_builds_prompt_correctly(self, generator, mock_model_manager):
        """測試對話正確構建提示"""
        mock_model_manager.tokenizer.return_value = {
            'input_ids': torch.tensor([[1, 2, 3]]),
            'attention_mask': torch.tensor([[1, 1, 1]])
        }
        mock_model_manager.model.generate.return_value = torch.tensor([[1, 2, 3, 4, 5]])
        mock_model_manager.tokenizer.decode.return_value = "回應"

        messages = [
            {"role": "user", "content": "問題1"},
            {"role": "assistant", "content": "回答1"},
            {"role": "user", "content": "問題2"}
        ]

        generator.generate_conversation(messages)

        # 檢查 tokenizer 被調用
        mock_model_manager.tokenizer.assert_called()


class TestPromptFormatting:
    """提示格式化測試"""

    def test_format_prompt_single(self, generator, mock_config):
        """測試單輪提示格式化"""
        prompt = generator._format_prompt("測試問題")

        assert isinstance(prompt, str)
        assert "測試問題" in prompt
        assert mock_config.prompts.system_prompt in prompt

    def test_format_conversation_prompt(self, generator, mock_config):
        """測試對話提示格式化"""
        messages = [
            {"role": "user", "content": "問題1"},
            {"role": "assistant", "content": "回答1"},
            {"role": "user", "content": "問題2"}
        ]

        prompt = generator._format_conversation_prompt(messages)

        assert isinstance(prompt, str)
        assert "問題1" in prompt
        assert "回答1" in prompt
        assert "問題2" in prompt


class TestOutputCleaning:
    """輸出清理測試"""

    def test_clean_output_basic(self, generator):
        """測試基本輸出清理"""
        raw_output = "助手: 這是回應。"
        cleaned = generator._clean_output(raw_output)

        assert "助手:" not in cleaned or cleaned.strip().startswith("這是")

    def test_clean_output_removes_prompt(self, generator):
        """測試移除提示內容"""
        raw_output = "使用者: 問題\n助手: 回應"
        cleaned = generator._clean_output(raw_output)

        # 應該只保留回應部分
        assert "回應" in cleaned

    def test_clean_output_strips_whitespace(self, generator):
        """測試去除空白"""
        raw_output = "  回應內容  \n\n"
        cleaned = generator._clean_output(raw_output)

        assert cleaned == cleaned.strip()

    def test_clean_output_empty(self, generator):
        """測試空輸出"""
        cleaned = generator._clean_output("")
        assert cleaned == ""


class TestGenerationParameters:
    """生成參數測試"""

    def test_default_parameters(self, generator, mock_model_manager, mock_config):
        """測試使用默認參數"""
        mock_model_manager.tokenizer.return_value = {
            'input_ids': torch.tensor([[1, 2, 3]]),
            'attention_mask': torch.tensor([[1, 1, 1]])
        }
        mock_model_manager.model.generate.return_value = torch.tensor([[1, 2, 3, 4, 5]])
        mock_model_manager.tokenizer.decode.return_value = "回應"

        generator.generate("測試")

        call_kwargs = mock_model_manager.model.generate.call_args[1]
        assert call_kwargs['max_length'] == mock_config.inference.max_length
        assert call_kwargs['temperature'] == mock_config.inference.temperature

    def test_parameter_override(self, generator, mock_model_manager):
        """測試參數覆蓋"""
        mock_model_manager.tokenizer.return_value = {
            'input_ids': torch.tensor([[1, 2, 3]]),
            'attention_mask': torch.tensor([[1, 1, 1]])
        }
        mock_model_manager.model.generate.return_value = torch.tensor([[1, 2, 3, 4, 5]])
        mock_model_manager.tokenizer.decode.return_value = "回應"

        custom_temp = 0.3
        generator.generate("測試", temperature=custom_temp)

        call_kwargs = mock_model_manager.model.generate.call_args[1]
        assert call_kwargs['temperature'] == custom_temp

    def test_invalid_temperature(self, generator):
        """測試無效的溫度參數"""
        with pytest.raises(ValueError):
            generator.generate("測試", temperature=-1.0)

        with pytest.raises(ValueError):
            generator.generate("測試", temperature=10.0)

    def test_invalid_max_length(self, generator):
        """測試無效的最大長度"""
        with pytest.raises(ValueError):
            generator.generate("測試", max_length=0)

        with pytest.raises(ValueError):
            generator.generate("測試", max_length=-100)


class TestErrorHandling:
    """錯誤處理測試"""

    def test_generation_error(self, generator, mock_model_manager):
        """測試生成錯誤"""
        mock_model_manager.tokenizer.return_value = {
            'input_ids': torch.tensor([[1, 2, 3]]),
            'attention_mask': torch.tensor([[1, 1, 1]])
        }
        mock_model_manager.model.generate.side_effect = RuntimeError("CUDA out of memory")

        with pytest.raises(RuntimeError):
            generator.generate("測試")

    def test_tokenization_error(self, generator, mock_model_manager):
        """測試分詞錯誤"""
        mock_model_manager.tokenizer.side_effect = Exception("Tokenization failed")

        with pytest.raises(Exception):
            generator.generate("測試")


class TestBatchGeneration:
    """批量生成測試"""

    def test_batch_generate(self, generator, mock_model_manager):
        """測試批量生成"""
        mock_model_manager.tokenizer.return_value = {
            'input_ids': torch.tensor([[1, 2, 3], [4, 5, 6]]),
            'attention_mask': torch.tensor([[1, 1, 1], [1, 1, 1]])
        }
        mock_model_manager.model.generate.return_value = torch.tensor([
            [1, 2, 3, 4, 5],
            [6, 7, 8, 9, 10]
        ])
        mock_model_manager.tokenizer.decode.side_effect = ["回應1", "回應2"]

        questions = ["問題1", "問題2"]
        results = []

        for q in questions:
            result = generator.generate(q)
            results.append(result)

        assert len(results) == 2
        assert all(isinstance(r, str) for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
