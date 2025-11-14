"""Text generation for medical chatbot"""

import gc
from typing import Dict, List, Optional

import torch
from loguru import logger
from transformers import PreTrainedModel, PreTrainedTokenizer

from medical_chatbot.data.preprocessor import DataPreprocessor


class MedicalChatGenerator:
    """Medical chatbot text generator"""

    def __init__(
        self,
        model: PreTrainedModel,
        tokenizer: PreTrainedTokenizer,
        system_prompt: str = "你是一位專業的醫療人員，請用心且專業的以三到五句話回答問題。",
        max_new_tokens: int = 90,
        temperature: float = 0.15,
        top_p: float = 0.15,
        top_k: int = 50,
        repetition_penalty: float = 1.6,
        do_sample: bool = True,
    ):
        """Initialize medical chat generator

        Args:
            model: Language model for generation
            tokenizer: Tokenizer for the model
            system_prompt: System prompt for the chatbot
            max_new_tokens: Maximum number of new tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            repetition_penalty: Repetition penalty
            do_sample: Whether to use sampling
        """
        self.model = model
        self.tokenizer = tokenizer
        self.system_prompt = system_prompt
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.repetition_penalty = repetition_penalty
        self.do_sample = do_sample
        self.preprocessor = DataPreprocessor()

    def generate(
        self,
        user_input: str,
        system_prompt: Optional[str] = None,
        clean_output: bool = True,
        **generation_kwargs,
    ) -> str:
        """Generate response to user input

        Args:
            user_input: User's question or input
            system_prompt: Override default system prompt
            clean_output: Whether to clean the output
            **generation_kwargs: Additional generation parameters

        Returns:
            Generated response
        """
        # Use provided system prompt or default
        sys_prompt = system_prompt or self.system_prompt

        # Format messages
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_input},
        ]

        # Apply chat template
        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False
        )

        # Tokenize
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)

        # Merge generation kwargs
        gen_kwargs = {
            "max_new_tokens": self.max_new_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "repetition_penalty": self.repetition_penalty,
            "do_sample": self.do_sample,
            "eos_token_id": self.tokenizer.eos_token_id,
            "pad_token_id": self.tokenizer.pad_token_id,
        }
        gen_kwargs.update(generation_kwargs)

        # Generate
        logger.debug(f"Generating response for: {user_input}")
        with torch.no_grad():
            generated_ids = self.model.generate(
                model_inputs.input_ids,
                attention_mask=model_inputs.attention_mask,
                **gen_kwargs,
            )

        # Decode (remove input tokens)
        generated_ids = generated_ids[:, model_inputs.input_ids.shape[-1] :]
        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

        # Clean output if requested
        if clean_output:
            response = self.preprocessor.process_output(response)

        logger.debug(f"Generated response: {response}")
        return response

    def chat(
        self, messages: List[Dict[str, str]], clean_output: bool = True, **generation_kwargs
    ) -> str:
        """Generate response for a conversation

        Args:
            messages: List of message dicts with 'role' and 'content'
            clean_output: Whether to clean the output
            **generation_kwargs: Additional generation parameters

        Returns:
            Generated response
        """
        # Apply chat template
        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False
        )

        # Tokenize
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)

        # Merge generation kwargs
        gen_kwargs = {
            "max_new_tokens": self.max_new_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "repetition_penalty": self.repetition_penalty,
            "do_sample": self.do_sample,
            "eos_token_id": self.tokenizer.eos_token_id,
            "pad_token_id": self.tokenizer.pad_token_id,
        }
        gen_kwargs.update(generation_kwargs)

        # Generate
        with torch.no_grad():
            generated_ids = self.model.generate(
                model_inputs.input_ids,
                attention_mask=model_inputs.attention_mask,
                **gen_kwargs,
            )

        # Decode (remove input tokens)
        generated_ids = generated_ids[:, model_inputs.input_ids.shape[-1] :]
        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

        # Clean output if requested
        if clean_output:
            response = self.preprocessor.process_output(response)

        return response

    def clear_cache(self) -> None:
        """Clear GPU cache"""
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
