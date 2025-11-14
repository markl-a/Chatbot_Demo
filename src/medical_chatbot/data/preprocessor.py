"""Data preprocessing utilities for medical chatbot"""

import re
from typing import List, Optional


class DataPreprocessor:
    """Text preprocessing for medical chatbot responses"""

    def __init__(self):
        """Initialize data preprocessor"""
        pass

    @staticmethod
    def clean_response(text: str) -> str:
        """Clean generated response text

        Args:
            text: Raw generated text

        Returns:
            Cleaned text
        """
        # Remove EOS tokens and everything after
        text = re.sub(r"</s>.*", "", text, flags=re.DOTALL)
        text = re.sub(r"</s>.*", "</s>", text)

        # Remove bracketed content
        text = re.sub(r"\[.*?\]", "", text)

        # Remove HTML tags
        text = re.sub(r"</?[^>]+>", "", text)

        # Remove specific unwanted words
        text = re.sub(r"dress|dressing", "", text, flags=re.IGNORECASE)

        # Remove special tags
        text = re.sub(r"<<.*?>>", "", text)

        # Strip whitespace
        text = text.strip()

        return text

    @staticmethod
    def truncate_at_sentence(text: str, max_sentences: Optional[int] = None) -> str:
        """Truncate text at the last complete sentence

        Args:
            text: Input text
            max_sentences: Maximum number of sentences to keep

        Returns:
            Truncated text
        """
        # Find last period or exclamation mark
        last_period_index = max(text.rfind("。"), text.rfind("!"))

        if last_period_index != -1:
            return text[: last_period_index + 1]

        return text

    @staticmethod
    def format_messages(messages: List[dict]) -> str:
        """Format messages for model input

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Formatted message string
        """
        formatted_messages = ""
        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "")

            if role == "system":
                formatted_messages += f"[SYSTEM] {content}\n"
            elif role == "user":
                formatted_messages += f"[USER] {content}\n"
            elif role == "assistant":
                formatted_messages += f"[ASSISTANT] {content}\n"

        return formatted_messages

    def process_output(
        self, text: str, clean: bool = True, truncate: bool = True
    ) -> str:
        """Process model output text

        Args:
            text: Raw model output
            clean: Whether to clean the text
            truncate: Whether to truncate at sentence boundary

        Returns:
            Processed text
        """
        if clean:
            text = self.clean_response(text)

        if truncate:
            text = self.truncate_at_sentence(text)

        return text.strip()
