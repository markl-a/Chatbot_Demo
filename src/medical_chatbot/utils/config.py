"""Configuration management for medical chatbot"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


class ModelConfig(BaseSettings):
    """Model configuration"""

    base_model: str = "taide/TAIDE-LX-7B-Chat"
    alternative_models: List[str] = ["MediaTek-Research/Breeze-7B-Instruct-v1_0"]
    fine_tuned_model: str = "mark1098/TAIDE-LX-7B-Chat-Medical-Fintune"
    torch_dtype: str = "bfloat16"
    device_map: str = "auto"
    use_fast_tokenizer: bool = False


class DatasetConfig(BaseSettings):
    """Dataset configuration"""

    name: str = "MedText_zhtw"
    url: str = (
        "https://huggingface.co/datasets/ChenWeiLi/Medtext_zhtw/raw/main/MedText_zhtw.json"
    )
    raw_path: str = "data/raw/MedText_zhtw.json"
    processed_path: str = "data/processed/MedText_zhtw_processed.json"
    train_test_split: float = 0.9
    max_length: int = 384


class TrainingConfig(BaseSettings):
    """Training configuration"""

    output_dir: str = "models/checkpoints"
    logging_dir: str = "logs"
    per_device_train_batch_size: int = 64
    per_device_eval_batch_size: int = 32
    gradient_accumulation_steps: int = 4
    num_train_epochs: int = 40
    learning_rate: float = 5e-5
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1
    save_strategy: str = "steps"
    save_steps: int = 50
    save_total_limit: int = 5
    logging_steps: int = 10
    evaluation_strategy: str = "steps"
    eval_steps: int = 100
    gradient_checkpointing: bool = True
    fp16: bool = False
    bf16: bool = True


class LoraConfig(BaseSettings):
    """LoRA configuration"""

    r: int = 8
    lora_alpha: int = 32
    lora_dropout: float = 0.1
    target_modules: List[str] = [
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ]
    task_type: str = "CAUSAL_LM"
    inference_mode: bool = False


class InferenceConfig(BaseSettings):
    """Inference configuration"""

    max_new_tokens: int = 90
    temperature: float = 0.15
    top_p: float = 0.15
    top_k: int = 50
    repetition_penalty: float = 1.6
    do_sample: bool = True
    num_beams: int = 1


class PromptsConfig(BaseSettings):
    """Prompts configuration"""

    system: str = "你是一位專業的醫療人員，請用心且專業的以三到五句話回答問題。"
    system_detailed: str = "你是一位專業的醫療人員，請用心且專業的回答問題。"


class APIConfig(BaseSettings):
    """API configuration"""

    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    reload: bool = False
    log_level: str = "info"


class GradioConfig(BaseSettings):
    """Gradio configuration"""

    share: bool = False
    server_name: str = "0.0.0.0"
    server_port: int = 7860
    enable_queue: bool = True


class LoggingConfig(BaseSettings):
    """Logging configuration"""

    level: str = "INFO"
    format: str = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    file: str = "logs/medical_chatbot.log"
    rotation: str = "10 MB"
    retention: str = "1 week"


class Config(BaseSettings):
    """Main configuration class"""

    model: ModelConfig = Field(default_factory=ModelConfig)
    dataset: DatasetConfig = Field(default_factory=DatasetConfig)
    training: TrainingConfig = Field(default_factory=TrainingConfig)
    lora: LoraConfig = Field(default_factory=LoraConfig)
    inference: InferenceConfig = Field(default_factory=InferenceConfig)
    prompts: PromptsConfig = Field(default_factory=PromptsConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    gradio: GradioConfig = Field(default_factory=GradioConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # Environment variables
    hf_token: Optional[str] = Field(None, env="HF_TOKEN")
    hf_read_token: Optional[str] = Field(None, env="HF_READ_TOKEN")
    hf_write_token: Optional[str] = Field(None, env="HF_WRITE_TOKEN")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from YAML file and environment variables

    Args:
        config_path: Path to YAML config file. If None, uses default path.

    Returns:
        Config object with loaded configuration
    """
    if config_path is None:
        config_path = "configs/config.yaml"

    config_path = Path(config_path)

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f)

        # Create nested config objects
        config_dict = {}
        if "model" in yaml_config:
            config_dict["model"] = ModelConfig(**yaml_config["model"])
        if "dataset" in yaml_config:
            config_dict["dataset"] = DatasetConfig(**yaml_config["dataset"])
        if "training" in yaml_config:
            config_dict["training"] = TrainingConfig(**yaml_config["training"])
        if "lora" in yaml_config:
            config_dict["lora"] = LoraConfig(**yaml_config["lora"])
        if "inference" in yaml_config:
            config_dict["inference"] = InferenceConfig(**yaml_config["inference"])
        if "prompts" in yaml_config:
            config_dict["prompts"] = PromptsConfig(**yaml_config["prompts"])
        if "api" in yaml_config:
            config_dict["api"] = APIConfig(**yaml_config["api"])
        if "gradio" in yaml_config:
            config_dict["gradio"] = GradioConfig(**yaml_config["gradio"])
        if "logging" in yaml_config:
            config_dict["logging"] = LoggingConfig(**yaml_config["logging"])

        return Config(**config_dict)
    else:
        # Return default config if file doesn't exist
        return Config()
