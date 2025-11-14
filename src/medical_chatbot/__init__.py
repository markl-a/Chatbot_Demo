"""Medical Chatbot - 醫療聊天機器人

基於 TAIDE/Breeze 模型的中文醫療問答系統
"""

__version__ = "0.2.0"
__author__ = "Mark L"
__email__ = "your.email@example.com"

from medical_chatbot.utils.config import Config, load_config

__all__ = ["Config", "load_config", "__version__"]
