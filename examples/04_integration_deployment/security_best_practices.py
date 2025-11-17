#!/usr/bin/env python3
"""
案例 4.3: 安全最佳實踐示例

這個範例展示醫療聊天機器人的安全最佳實踐，包括：
- 輸入驗證和清理
- 輸出過濾
- 速率限制
- 敏感資訊保護
- 安全配置

運行方式:
    python examples/04_integration_deployment/security_best_practices.py
"""

import re
import hashlib
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict


class InputValidator:
    """輸入驗證器"""

    def __init__(self):
        """初始化輸入驗證器"""
        # 危險模式
        self.dangerous_patterns = [
            r'<script',
            r'javascript:',
            r'onerror=',
            r'onclick=',
            r'\.\./',
            r'DROP\s+TABLE',
            r'SELECT\s+\*\s+FROM',
            r'UNION\s+SELECT'
        ]

        # 最大長度限制
        self.max_message_length = 2000
        self.max_messages_per_conversation = 50

    def validate_message(self, message: str) -> Tuple[bool, Optional[str]]:
        """驗證單個訊息

        Args:
            message: 訊息內容

        Returns:
            (是否有效, 錯誤訊息)
        """
        # 檢查空訊息
        if not message or not message.strip():
            return False, "訊息不能為空"

        # 檢查長度
        if len(message) > self.max_message_length:
            return False, f"訊息長度超過限制 ({self.max_message_length} 字元)"

        # 檢查危險模式
        for pattern in self.dangerous_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return False, f"檢測到潛在的安全風險: {pattern}"

        return True, None

    def sanitize_message(self, message: str) -> str:
        """清理訊息

        Args:
            message: 原始訊息

        Returns:
            清理後的訊息
        """
        # 移除 HTML 標籤
        message = re.sub(r'<[^>]+>', '', message)

        # 移除多餘的空白
        message = ' '.join(message.split())

        # 轉義特殊字元
        special_chars = {
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
            '/': '&#x2F;'
        }

        for char, escape in special_chars.items():
            message = message.replace(char, escape)

        return message


class RateLimiter:
    """速率限制器"""

    def __init__(
        self,
        max_requests_per_minute: int = 10,
        max_requests_per_hour: int = 100
    ):
        """初始化速率限制器

        Args:
            max_requests_per_minute: 每分鐘最大請求數
            max_requests_per_hour: 每小時最大請求數
        """
        self.max_requests_per_minute = max_requests_per_minute
        self.max_requests_per_hour = max_requests_per_hour

        # 請求歷史
        self.request_history = defaultdict(list)

    def _get_client_id(self, ip_address: str, user_id: Optional[str] = None) -> str:
        """生成客戶端 ID

        Args:
            ip_address: IP 地址
            user_id: 用戶 ID

        Returns:
            客戶端 ID
        """
        identifier = f"{ip_address}:{user_id or 'anonymous'}"
        return hashlib.sha256(identifier.encode()).hexdigest()

    def is_allowed(
        self,
        ip_address: str,
        user_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """檢查是否允許請求

        Args:
            ip_address: IP 地址
            user_id: 用戶 ID

        Returns:
            (是否允許, 原因)
        """
        client_id = self._get_client_id(ip_address, user_id)
        now = datetime.now()

        # 清理舊的請求記錄
        self.request_history[client_id] = [
            timestamp for timestamp in self.request_history[client_id]
            if now - timestamp < timedelta(hours=1)
        ]

        # 檢查每分鐘限制
        minute_ago = now - timedelta(minutes=1)
        recent_requests = [
            t for t in self.request_history[client_id]
            if t > minute_ago
        ]

        if len(recent_requests) >= self.max_requests_per_minute:
            return False, f"超過每分鐘請求限制 ({self.max_requests_per_minute})"

        # 檢查每小時限制
        if len(self.request_history[client_id]) >= self.max_requests_per_hour:
            return False, f"超過每小時請求限制 ({self.max_requests_per_hour})"

        # 記錄請求
        self.request_history[client_id].append(now)

        return True, None


class ContentFilter:
    """內容過濾器"""

    def __init__(self):
        """初始化內容過濾器"""
        # 敏感關鍵字
        self.sensitive_keywords = [
            # 個人資訊
            r'\d{10}',  # 電話號碼
            r'\d{3}-\d{2}-\d{4}',  # 身分證號碼格式
            r'\b\d{16}\b',  # 信用卡號碼
            # 醫療處方
            r'處方\s*\d+',
            r'藥物\s*代碼',
        ]

        # 免責聲明
        self.disclaimer = """
⚠️ 重要聲明：
本系統提供的資訊僅供參考，不能替代專業醫療診斷和治療。
如有健康問題，請諮詢專業醫療人員。
"""

    def contains_sensitive_info(self, text: str) -> Tuple[bool, List[str]]:
        """檢查是否包含敏感資訊

        Args:
            text: 文本內容

        Returns:
            (是否包含敏感資訊, 匹配的模式列表)
        """
        matched_patterns = []

        for pattern in self.sensitive_keywords:
            if re.search(pattern, text):
                matched_patterns.append(pattern)

        return len(matched_patterns) > 0, matched_patterns

    def add_disclaimer(self, response: str) -> str:
        """添加免責聲明

        Args:
            response: 原始回應

        Returns:
            添加免責聲明後的回應
        """
        return f"{response}\n\n{self.disclaimer}"

    def mask_sensitive_info(self, text: str) -> str:
        """遮罩敏感資訊

        Args:
            text: 原始文本

        Returns:
            遮罩後的文本
        """
        # 遮罩電話號碼
        text = re.sub(r'\d{10}', '**********', text)

        # 遮罩身分證號碼
        text = re.sub(r'\d{3}-\d{2}-\d{4}', '***-**-****', text)

        # 遮罩信用卡號碼
        text = re.sub(r'\b\d{16}\b', '****************', text)

        return text


class SecurityManager:
    """安全管理器"""

    def __init__(self):
        """初始化安全管理器"""
        self.input_validator = InputValidator()
        self.rate_limiter = RateLimiter()
        self.content_filter = ContentFilter()

    def validate_request(
        self,
        message: str,
        ip_address: str,
        user_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """驗證請求

        Args:
            message: 訊息內容
            ip_address: IP 地址
            user_id: 用戶 ID

        Returns:
            (是否有效, 清理後的訊息, 錯誤訊息)
        """
        # 1. 檢查速率限制
        allowed, reason = self.rate_limiter.is_allowed(ip_address, user_id)
        if not allowed:
            return False, None, f"請求被限制: {reason}"

        # 2. 驗證輸入
        valid, error = self.input_validator.validate_message(message)
        if not valid:
            return False, None, f"輸入驗證失敗: {error}"

        # 3. 清理訊息
        sanitized_message = self.input_validator.sanitize_message(message)

        # 4. 檢查敏感資訊
        has_sensitive, patterns = self.content_filter.contains_sensitive_info(
            sanitized_message
        )
        if has_sensitive:
            return False, None, "訊息包含敏感資訊，已被攔截"

        return True, sanitized_message, None

    def process_response(self, response: str) -> str:
        """處理回應

        Args:
            response: 原始回應

        Returns:
            處理後的回應
        """
        # 遮罩可能的敏感資訊
        response = self.content_filter.mask_sensitive_info(response)

        # 添加免責聲明
        response = self.content_filter.add_disclaimer(response)

        return response


def demo_input_validation():
    """示範輸入驗證"""
    print("\n" + "=" * 60)
    print("示範 1: 輸入驗證")
    print("=" * 60)

    validator = InputValidator()

    # 測試案例
    test_cases = [
        {"message": "我頭痛該怎麼辦？", "expected": True},
        {"message": "", "expected": False},
        {"message": "A" * 3000, "expected": False},
        {"message": "<script>alert('xss')</script>", "expected": False},
        {"message": "SELECT * FROM users", "expected": False},
        {"message": "正常的醫療問題", "expected": True}
    ]

    for i, case in enumerate(test_cases, 1):
        message = case["message"]
        display_message = message[:50] + "..." if len(message) > 50 else message

        valid, error = validator.validate_message(message)

        status = "✓" if valid == case["expected"] else "✗"
        print(f"\n{status} 案例 {i}: {display_message}")

        if not valid:
            print(f"  錯誤: {error}")


def demo_rate_limiting():
    """示範速率限制"""
    print("\n" + "=" * 60)
    print("示範 2: 速率限制")
    print("=" * 60)

    # 創建限制器（每分鐘 5 次，每小時 20 次）
    rate_limiter = RateLimiter(
        max_requests_per_minute=5,
        max_requests_per_hour=20
    )

    ip_address = "192.168.1.1"

    print(f"\n測試 IP: {ip_address}")
    print(f"限制: 每分鐘 5 次，每小時 20 次\n")

    # 快速發送 10 次請求
    print("快速發送 10 次請求:")
    for i in range(10):
        allowed, reason = rate_limiter.is_allowed(ip_address)

        if allowed:
            print(f"  請求 {i+1}: ✓ 允許")
        else:
            print(f"  請求 {i+1}: ✗ 被限制 - {reason}")


def demo_content_filtering():
    """示範內容過濾"""
    print("\n" + "=" * 60)
    print("示範 3: 內容過濾")
    print("=" * 60)

    content_filter = ContentFilter()

    # 測試敏感資訊檢測
    test_texts = [
        "我的電話是 0912345678",
        "我的身分證號碼是 123-45-6789",
        "正常的醫療諮詢",
        "處方編號 12345"
    ]

    print("\n敏感資訊檢測:")
    for text in test_texts:
        has_sensitive, patterns = content_filter.contains_sensitive_info(text)

        if has_sensitive:
            print(f"  ⚠️  {text}")
            print(f"      匹配模式: {patterns}")
        else:
            print(f"  ✓ {text}")

    # 測試資訊遮罩
    print("\n\n資訊遮罩:")
    sensitive_text = "我的電話是 0912345678，身分證號碼是 123-45-6789"
    masked_text = content_filter.mask_sensitive_info(sensitive_text)

    print(f"  原文: {sensitive_text}")
    print(f"  遮罩: {masked_text}")


def demo_security_manager():
    """示範安全管理器"""
    print("\n" + "=" * 60)
    print("示範 4: 綜合安全管理")
    print("=" * 60)

    security_manager = SecurityManager()

    # 測試請求
    test_requests = [
        {
            "message": "我頭痛該怎麼辦？",
            "ip": "192.168.1.100",
            "user_id": "user001"
        },
        {
            "message": "<script>alert('test')</script>",
            "ip": "192.168.1.101",
            "user_id": "user002"
        },
        {
            "message": "我的電話是 0912345678",
            "ip": "192.168.1.102",
            "user_id": "user003"
        },
        {
            "message": "如何預防感冒？",
            "ip": "192.168.1.100",
            "user_id": "user001"
        }
    ]

    print("\n處理請求:")
    for i, req in enumerate(test_requests, 1):
        print(f"\n請求 {i}:")
        print(f"  訊息: {req['message'][:50]}")
        print(f"  IP: {req['ip']}")

        valid, sanitized, error = security_manager.validate_request(
            req["message"],
            req["ip"],
            req["user_id"]
        )

        if valid:
            print(f"  ✓ 驗證通過")
            print(f"  清理後: {sanitized}")

            # 模擬回應處理
            response = "這是醫療建議的回應。"
            processed = security_manager.process_response(response)
            print(f"  回應: {processed[:100]}...")
        else:
            print(f"  ✗ 驗證失敗: {error}")


def demo_security_config():
    """示範安全配置"""
    print("\n" + "=" * 60)
    print("示範 5: 安全配置最佳實踐")
    print("=" * 60)

    security_config = {
        "api": {
            "enable_https": True,
            "require_authentication": True,
            "session_timeout": 3600,
            "max_request_size": 10240
        },
        "rate_limiting": {
            "enabled": True,
            "requests_per_minute": 10,
            "requests_per_hour": 100,
            "requests_per_day": 1000
        },
        "input_validation": {
            "max_message_length": 2000,
            "sanitize_html": True,
            "block_sql_injection": True,
            "block_xss": True
        },
        "output_filtering": {
            "add_disclaimer": True,
            "mask_sensitive_info": True,
            "content_security_policy": True
        },
        "logging": {
            "log_all_requests": True,
            "log_failed_authentications": True,
            "log_rate_limit_violations": True,
            "retention_days": 90
        },
        "encryption": {
            "encrypt_data_at_rest": True,
            "encrypt_data_in_transit": True,
            "key_rotation_days": 90
        }
    }

    print("\n推薦的安全配置:")
    import json
    print(json.dumps(security_config, indent=2, ensure_ascii=False))


def main():
    """主函數"""
    print("""
╔══════════════════════════════════════════════════════════╗
║        醫療聊天機器人 - 安全最佳實踐示例                ║
╚══════════════════════════════════════════════════════════╝
    """)

    print("\n選擇要運行的示範:")
    print("1. 輸入驗證")
    print("2. 速率限制")
    print("3. 內容過濾")
    print("4. 綜合安全管理")
    print("5. 安全配置最佳實踐")
    print("6. 運行所有示範")

    try:
        choice = input("\n請輸入選項 (1-6): ").strip()

        if choice == "1":
            demo_input_validation()
        elif choice == "2":
            demo_rate_limiting()
        elif choice == "3":
            demo_content_filtering()
        elif choice == "4":
            demo_security_manager()
        elif choice == "5":
            demo_security_config()
        elif choice == "6":
            demo_input_validation()
            demo_rate_limiting()
            demo_content_filtering()
            demo_security_manager()
            demo_security_config()
        else:
            print("無效的選項")

        print("\n" + "=" * 60)
        print("示範完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
