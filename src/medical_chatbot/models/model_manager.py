"""Model loading and management for medical chatbot"""

import gc
from pathlib import Path
from typing import Optional, Union

import torch
from loguru import logger
from peft import PeftModel
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    PreTrainedModel,
    PreTrainedTokenizer,
)


class ModelManager:
    """Manages model loading and inference"""

    def __init__(
        self,
        model_name: str,
        peft_name: Optional[str] = None,
        torch_dtype: str = "bfloat16",
        device_map: str = "auto",
        use_fast_tokenizer: bool = False,
        token: Optional[str] = None,
    ):
        """Initialize model manager

        Args:
            model_name: Base model name or path
            peft_name: PEFT adapter name or path (optional)
            torch_dtype: Torch dtype for model weights
            device_map: Device map for model loading
            use_fast_tokenizer: Whether to use fast tokenizer
            token: HuggingFace token for authentication
        """
        self.model_name = model_name
        self.peft_name = peft_name
        self.torch_dtype = getattr(torch, torch_dtype)
        self.device_map = device_map
        self.use_fast_tokenizer = use_fast_tokenizer
        self.token = token

        self.tokenizer: Optional[PreTrainedTokenizer] = None
        self.model: Optional[PreTrainedModel] = None

    def load_tokenizer(self) -> PreTrainedTokenizer:
        """Load tokenizer

        Returns:
            Loaded tokenizer
        """
        logger.info(f"Loading tokenizer from {self.model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            use_fast=self.use_fast_tokenizer,
            token=self.token,
        )
        logger.info("Tokenizer loaded successfully")
        return self.tokenizer

    def load_model(self, load_peft: bool = True) -> PreTrainedModel:
        """Load model with optional PEFT adapter

        Args:
            load_peft: Whether to load PEFT adapter

        Returns:
            Loaded model
        """
        logger.info(f"Loading model from {self.model_name}")
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            device_map=self.device_map,
            torch_dtype=self.torch_dtype,
            token=self.token,
        )

        # Load PEFT adapter if specified
        if load_peft and self.peft_name:
            logger.info(f"Loading PEFT adapter from {self.peft_name}")
            self.model = PeftModel.from_pretrained(self.model, self.peft_name)

        # Set pad and eos token IDs
        if self.tokenizer:
            if hasattr(self.tokenizer, "pad_token_id") and self.tokenizer.pad_token_id:
                self.model.config.pad_token_id = self.tokenizer.pad_token_id
            if hasattr(self.tokenizer, "eos_token_id") and self.tokenizer.eos_token_id:
                self.model.config.eos_token_id = self.tokenizer.eos_token_id

        logger.info("Model loaded successfully")
        return self.model

    def load(self, load_peft: bool = True) -> tuple[PreTrainedTokenizer, PreTrainedModel]:
        """Load both tokenizer and model

        Args:
            load_peft: Whether to load PEFT adapter

        Returns:
            Tuple of (tokenizer, model)
        """
        self.load_tokenizer()
        self.load_model(load_peft=load_peft)
        return self.tokenizer, self.model

    def move_to_device(self, device: str = "cuda") -> None:
        """Move model to specified device

        Args:
            device: Device to move model to
        """
        if self.model is None:
            raise ValueError("Model not loaded. Call load_model() first.")

        logger.info(f"Moving model to {device}")
        self.model = self.model.to(device)

    def unload(self) -> None:
        """Unload model and free memory"""
        logger.info("Unloading model")
        if self.model is not None:
            del self.model
            self.model = None

        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("Model unloaded and memory freed")

    def save_model(self, output_dir: str, safe_serialization: bool = True) -> None:
        """Save model to directory

        Args:
            output_dir: Directory to save model
            safe_serialization: Whether to use safe serialization
        """
        if self.model is None:
            raise ValueError("Model not loaded. Call load_model() first.")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Saving model to {output_dir}")
        self.model.save_pretrained(output_dir, safe_serialization=safe_serialization)

        if self.tokenizer:
            self.tokenizer.save_pretrained(output_dir)

        logger.info("Model saved successfully")

    def merge_and_save(self, output_dir: str) -> None:
        """Merge PEFT adapter and save full model

        Args:
            output_dir: Directory to save merged model
        """
        if self.model is None:
            raise ValueError("Model not loaded. Call load_model() first.")

        if not isinstance(self.model, PeftModel):
            logger.warning("Model is not a PeftModel, saving without merging")
            self.save_model(output_dir)
            return

        logger.info("Merging PEFT adapter with base model")
        merged_model = self.model.merge_and_unload()

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Saving merged model to {output_dir}")
        merged_model.save_pretrained(output_dir)

        if self.tokenizer:
            self.tokenizer.save_pretrained(output_dir)

        logger.info("Merged model saved successfully")
