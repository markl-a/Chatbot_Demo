"""Tests for configuration management"""

import os
from pathlib import Path

import pytest

from medical_chatbot.utils.config import Config, load_config


def test_default_config():
    """Test default configuration"""
    config = Config()

    assert config.model.base_model == "taide/TAIDE-LX-7B-Chat"
    assert config.training.num_train_epochs == 40
    assert config.lora.r == 8
    assert config.inference.max_new_tokens == 90


def test_load_config():
    """Test loading configuration from YAML file"""
    # Create a temporary config file
    config_content = """
model:
  base_model: "test/model"
training:
  num_train_epochs: 10
"""

    config_path = Path("test_config.yaml")
    config_path.write_text(config_content)

    try:
        config = load_config(str(config_path))
        assert config.model.base_model == "test/model"
        assert config.training.num_train_epochs == 10
    finally:
        config_path.unlink()


def test_config_env_vars(monkeypatch):
    """Test configuration with environment variables"""
    monkeypatch.setenv("HF_TOKEN", "test_token")

    config = Config()
    assert config.hf_token == "test_token"
