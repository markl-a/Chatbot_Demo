"""Tests for data preprocessing"""

import pytest

from medical_chatbot.data.preprocessor import DataPreprocessor


@pytest.fixture
def preprocessor():
    """Create preprocessor instance"""
    return DataPreprocessor()


def test_clean_response(preprocessor):
    """Test response cleaning"""
    text = "This is a test</s> with extra content"
    cleaned = preprocessor.clean_response(text)
    assert "</s>" not in cleaned
    assert "with extra content" not in cleaned


def test_truncate_at_sentence(preprocessor):
    """Test sentence truncation"""
    text = "這是第一句。這是第二句。還有更多內容"
    truncated = preprocessor.truncate_at_sentence(text)
    assert truncated == "這是第一句。這是第二句。"


def test_format_messages(preprocessor):
    """Test message formatting"""
    messages = [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
    ]

    formatted = preprocessor.format_messages(messages)
    assert "[SYSTEM]" in formatted
    assert "[USER]" in formatted
    assert "You are a helpful assistant" in formatted
    assert "Hello" in formatted


def test_process_output(preprocessor):
    """Test full output processing"""
    text = "這是回應。這是第二句。</s>extra"
    processed = preprocessor.process_output(text, clean=True, truncate=True)

    assert "</s>" not in processed
    assert "extra" not in processed
    assert processed.endswith("。")
