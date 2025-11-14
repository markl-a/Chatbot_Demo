"""Dataset loading and processing for medical chatbot"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from datasets import Dataset
from loguru import logger
from transformers import PreTrainedTokenizer


class MedicalDataset:
    """Medical dataset handler"""

    def __init__(
        self,
        dataset_path: Optional[str] = None,
        dataset_url: Optional[str] = None,
        max_length: int = 384,
    ):
        """Initialize medical dataset

        Args:
            dataset_path: Path to local dataset file
            dataset_url: URL to download dataset
            max_length: Maximum sequence length for tokenization
        """
        self.dataset_path = dataset_path
        self.dataset_url = dataset_url
        self.max_length = max_length
        self.data: Optional[Dataset] = None

    def download(self, save_path: Optional[str] = None) -> str:
        """Download dataset from URL

        Args:
            save_path: Path to save downloaded dataset

        Returns:
            Path to downloaded file
        """
        if not self.dataset_url:
            raise ValueError("Dataset URL not provided")

        if save_path is None:
            save_path = self.dataset_path or "data/raw/MedText_zhtw.json"

        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Downloading dataset from {self.dataset_url}")
        response = requests.get(self.dataset_url)
        response.raise_for_status()

        with open(save_path, "wb") as f:
            f.write(response.content)

        logger.info(f"Dataset downloaded to {save_path}")
        self.dataset_path = str(save_path)
        return str(save_path)

    def load(self) -> Dataset:
        """Load dataset from file

        Returns:
            Loaded dataset
        """
        if not self.dataset_path or not Path(self.dataset_path).exists():
            raise FileNotFoundError(f"Dataset file not found: {self.dataset_path}")

        logger.info(f"Loading dataset from {self.dataset_path}")
        df = pd.read_json(self.dataset_path)
        self.data = Dataset.from_pandas(df)
        logger.info(f"Loaded {len(self.data)} examples")
        return self.data

    def process(self, tokenizer: PreTrainedTokenizer) -> Dataset:
        """Process dataset with tokenizer

        Args:
            tokenizer: Tokenizer to use for processing

        Returns:
            Processed dataset
        """
        if self.data is None:
            raise ValueError("Dataset not loaded. Call load() first.")

        def process_func(example: Dict[str, Any]) -> Dict[str, Any]:
            """Process a single example"""
            # Build instruction and input string
            instruction = tokenizer(
                f"user\n\n{example['instruction'] + example['input']}assistant\n\n",
                add_special_tokens=False,
            )
            response = tokenizer(f"{example['output']}", add_special_tokens=False)

            # Merge input and response token IDs
            input_ids = instruction["input_ids"] + response["input_ids"]
            attention_mask = instruction["attention_mask"] + response["attention_mask"]
            labels = [-100] * len(instruction["input_ids"]) + response["input_ids"]

            # Truncate if exceeds max length
            if len(input_ids) > self.max_length:
                input_ids = input_ids[: self.max_length]
                attention_mask = attention_mask[: self.max_length]
                labels = labels[: self.max_length]

            return {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "labels": labels,
            }

        logger.info("Processing dataset...")
        tokenized_ds = self.data.map(process_func, remove_columns=self.data.column_names)
        logger.info(f"Dataset processed: {len(tokenized_ds)} examples")

        return tokenized_ds

    def split(self, train_ratio: float = 0.9) -> tuple[Dataset, Dataset]:
        """Split dataset into train and validation sets

        Args:
            train_ratio: Ratio of training data

        Returns:
            Tuple of (train_dataset, val_dataset)
        """
        if self.data is None:
            raise ValueError("Dataset not loaded. Call load() first.")

        split_data = self.data.train_test_split(train_size=train_ratio, seed=42)
        train_ds = split_data["train"]
        val_ds = split_data["test"]

        logger.info(f"Split dataset: {len(train_ds)} train, {len(val_ds)} validation")
        return train_ds, val_ds


def load_dataset(
    dataset_path: Optional[str] = None,
    dataset_url: Optional[str] = None,
    download_if_missing: bool = True,
) -> MedicalDataset:
    """Load medical dataset

    Args:
        dataset_path: Path to local dataset file
        dataset_url: URL to download dataset
        download_if_missing: Whether to download if local file doesn't exist

    Returns:
        MedicalDataset object
    """
    dataset = MedicalDataset(dataset_path=dataset_path, dataset_url=dataset_url)

    if dataset_path and Path(dataset_path).exists():
        dataset.load()
    elif download_if_missing and dataset_url:
        dataset.download(dataset_path)
        dataset.load()
    else:
        raise FileNotFoundError(
            f"Dataset not found at {dataset_path} and download_if_missing=False"
        )

    return dataset


def process_dataset(
    dataset: MedicalDataset, tokenizer: PreTrainedTokenizer
) -> Dataset:
    """Process dataset with tokenizer

    Args:
        dataset: MedicalDataset object
        tokenizer: Tokenizer to use

    Returns:
        Processed dataset
    """
    return dataset.process(tokenizer)
