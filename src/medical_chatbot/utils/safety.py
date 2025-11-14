"""Safety utilities for medical chatbot"""

import re
from typing import List, Optional, Tuple


class MedicalSafetyFilter:
    """Safety filter for medical chatbot responses"""

    # Medical disclaimer
    DISCLAIMER = """

⚠️ **重要提醒**: 本回應僅供參考,不構成專業醫療建議。如有任何健康疑慮,請諮詢合格的醫療專業人員。
"""

    # Keywords that require extra caution
    HIGH_RISK_KEYWORDS = [
        "自殺",
        "自殘",
        "服藥過量",
        "緊急",
        "胸痛",
        "呼吸困難",
        "嚴重出血",
        "失去意識",
        "中毒",
        "藥物過敏",
    ]

    # Emergency response template
    EMERGENCY_RESPONSE = """
🚨 **緊急情況**: 您提到的症狀可能需要立即醫療協助。

請立即:
1. 撥打緊急電話 119
2. 前往最近的急診室
3. 聯繫您的醫療服務提供者

在等待緊急服務時,請保持冷靜並待在安全的地方。
"""

    def __init__(self, add_disclaimer: bool = True, detect_emergency: bool = True):
        """Initialize safety filter

        Args:
            add_disclaimer: Whether to add disclaimer to responses
            detect_emergency: Whether to detect emergency situations
        """
        self.add_disclaimer = add_disclaimer
        self.detect_emergency = detect_emergency

    def is_emergency(self, text: str) -> bool:
        """Check if text contains emergency keywords

        Args:
            text: Input text to check

        Returns:
            True if emergency keywords detected
        """
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.HIGH_RISK_KEYWORDS)

    def filter_response(self, user_input: str, response: str) -> Tuple[str, bool]:
        """Filter and enhance response with safety measures

        Args:
            user_input: User's original input
            response: Model's generated response

        Returns:
            Tuple of (filtered_response, is_emergency)
        """
        # Check for emergency
        is_emergency_case = False
        if self.detect_emergency and self.is_emergency(user_input):
            is_emergency_case = True
            # Prepend emergency warning
            response = self.EMERGENCY_RESPONSE + "\n\n" + response

        # Add disclaimer
        if self.add_disclaimer:
            response = response + self.DISCLAIMER

        return response, is_emergency_case

    def sanitize_input(self, text: str) -> str:
        """Sanitize user input

        Args:
            text: User input text

        Returns:
            Sanitized text
        """
        # Remove potential injection attempts
        text = re.sub(r"<script.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"javascript:", "", text, flags=re.IGNORECASE)

        # Limit length
        max_length = 2000
        if len(text) > max_length:
            text = text[:max_length]

        return text.strip()


class BiasDetector:
    """Detect potential biases in responses"""

    # Biased terms that should be avoided
    BIASED_TERMS = [
        "總是",
        "從不",
        "所有人",
        "沒有人",
        "絕對",
        "肯定",
        "保證",
        "一定",
    ]

    def detect_bias(self, text: str) -> List[str]:
        """Detect potential biases in text

        Args:
            text: Text to analyze

        Returns:
            List of detected biased terms
        """
        detected = []
        for term in self.BIASED_TERMS:
            if term in text:
                detected.append(term)

        return detected

    def suggest_alternatives(self, text: str) -> Optional[str]:
        """Suggest more balanced alternatives

        Args:
            text: Original text

        Returns:
            Suggestion message if biases detected
        """
        biases = self.detect_bias(text)

        if biases:
            return f"建議: 回應中包含絕對性詞彙 ({', '.join(biases)})。考慮使用更謹慎的表述,如'通常'、'可能'、'在某些情況下'等。"

        return None
