"""LoRA training for medical chatbot"""

from pathlib import Path
from typing import Optional

import torch
from datasets import Dataset
from loguru import logger
from peft import LoraConfig, TaskType, get_peft_model
from transformers import (
    DataCollatorForSeq2Seq,
    PreTrainedModel,
    PreTrainedTokenizer,
    Trainer,
    TrainingArguments,
)


class LoraTrainer:
    """LoRA fine-tuning trainer"""

    def __init__(
        self,
        model: PreTrainedModel,
        tokenizer: PreTrainedTokenizer,
        lora_config: Optional[dict] = None,
        training_config: Optional[dict] = None,
    ):
        """Initialize LoRA trainer

        Args:
            model: Base model to fine-tune
            tokenizer: Tokenizer for the model
            lora_config: LoRA configuration dict
            training_config: Training configuration dict
        """
        self.base_model = model
        self.tokenizer = tokenizer
        self.model: Optional[PreTrainedModel] = None
        self.trainer: Optional[Trainer] = None

        # Default LoRA config
        self.lora_config = lora_config or {
            "r": 8,
            "lora_alpha": 32,
            "lora_dropout": 0.1,
            "target_modules": [
                "q_proj",
                "k_proj",
                "v_proj",
                "o_proj",
                "gate_proj",
                "up_proj",
                "down_proj",
            ],
        }

        # Default training config
        self.training_config = training_config or {
            "output_dir": "models/checkpoints",
            "num_train_epochs": 40,
            "per_device_train_batch_size": 64,
            "gradient_accumulation_steps": 4,
            "learning_rate": 5e-5,
            "weight_decay": 0.01,
            "logging_steps": 10,
            "save_steps": 50,
            "save_total_limit": 5,
        }

    def setup_lora(self) -> PreTrainedModel:
        """Setup LoRA adapter on base model

        Returns:
            Model with LoRA adapter
        """
        logger.info("Setting up LoRA adapter")

        # Enable gradient checkpointing
        self.base_model.enable_input_require_grads()

        # Create LoRA config
        config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            inference_mode=False,
            r=self.lora_config["r"],
            lora_alpha=self.lora_config["lora_alpha"],
            lora_dropout=self.lora_config["lora_dropout"],
            target_modules=self.lora_config["target_modules"],
        )

        # Get PEFT model
        self.model = get_peft_model(self.base_model, config)

        # Print trainable parameters
        trainable_params = sum(
            p.numel() for p in self.model.parameters() if p.requires_grad
        )
        all_params = sum(p.numel() for p in self.model.parameters())
        trainable_percentage = 100 * trainable_params / all_params

        logger.info(
            f"Trainable params: {trainable_params:,} || "
            f"All params: {all_params:,} || "
            f"Trainable%: {trainable_percentage:.4f}"
        )

        return self.model

    def setup_trainer(
        self,
        train_dataset: Dataset,
        eval_dataset: Optional[Dataset] = None,
    ) -> Trainer:
        """Setup Trainer

        Args:
            train_dataset: Training dataset
            eval_dataset: Evaluation dataset (optional)

        Returns:
            Configured Trainer
        """
        if self.model is None:
            raise ValueError("LoRA not setup. Call setup_lora() first.")

        logger.info("Setting up Trainer")

        # Create output directory
        output_dir = Path(self.training_config["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        # Training arguments
        args = TrainingArguments(
            output_dir=str(output_dir),
            num_train_epochs=self.training_config.get("num_train_epochs", 40),
            per_device_train_batch_size=self.training_config.get(
                "per_device_train_batch_size", 64
            ),
            per_device_eval_batch_size=self.training_config.get(
                "per_device_eval_batch_size", 32
            ),
            gradient_accumulation_steps=self.training_config.get(
                "gradient_accumulation_steps", 4
            ),
            learning_rate=self.training_config.get("learning_rate", 5e-5),
            weight_decay=self.training_config.get("weight_decay", 0.01),
            warmup_ratio=self.training_config.get("warmup_ratio", 0.1),
            logging_dir=self.training_config.get("logging_dir", "logs"),
            logging_steps=self.training_config.get("logging_steps", 10),
            save_strategy=self.training_config.get("save_strategy", "steps"),
            save_steps=self.training_config.get("save_steps", 50),
            save_total_limit=self.training_config.get("save_total_limit", 5),
            evaluation_strategy=self.training_config.get("evaluation_strategy", "steps")
            if eval_dataset
            else "no",
            eval_steps=self.training_config.get("eval_steps", 100),
            gradient_checkpointing=self.training_config.get("gradient_checkpointing", True),
            bf16=self.training_config.get("bf16", True),
            fp16=self.training_config.get("fp16", False),
        )

        # Data collator
        data_collator = DataCollatorForSeq2Seq(tokenizer=self.tokenizer, padding=True)

        # Create trainer
        self.trainer = Trainer(
            model=self.model,
            args=args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            data_collator=data_collator,
            tokenizer=self.tokenizer,
        )

        logger.info("Trainer setup complete")
        return self.trainer

    def train(self) -> None:
        """Start training"""
        if self.trainer is None:
            raise ValueError("Trainer not setup. Call setup_trainer() first.")

        logger.info("Starting training")

        # Disable reentrant for gradient checkpointing
        torch.utils.checkpoint.use_reentrant = False

        # Train
        self.trainer.train()

        logger.info("Training complete")

    def save(self, output_dir: str, safe_serialization: bool = True) -> None:
        """Save trained model

        Args:
            output_dir: Directory to save model
            safe_serialization: Whether to use safe serialization
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Saving model to {output_dir}")
        self.model.save_pretrained(output_dir, safe_serialization=safe_serialization)
        self.tokenizer.save_pretrained(output_dir)

        logger.info("Model saved successfully")
