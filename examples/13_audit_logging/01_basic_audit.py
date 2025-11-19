"""
基本審計日誌範例

展示如何使用審計日誌系統。
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.medical_chatbot.audit import AuditLogger, AuditEventType, AuditLevel


def example_1_basic_logging():
    """基本審計日誌記錄"""
    print("\n" + "=" * 80)
    print("範例 1: 基本審計日誌記錄")
    print("=" * 80)

    audit_logger = AuditLogger(log_to_console=True)

    # 記錄用戶登入
    audit_logger.log_user_login(user_id="user123", ip_address="192.168.1.1")

    # 記錄 API 調用
    audit_logger.log_api_call(
        endpoint="/api/chat",
        method="POST",
        user_id="user123",
        status_code=200,
        response_time=0.5,
    )

    # 記錄資料操作
    audit_logger.log_data_operation(
        operation="create",
        resource="session",
        user_id="user123",
        resource_id="session-456",
    )

    print("\n審計摘要:")
    summary = audit_logger.generate_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")


def example_2_security_events():
    """安全事件記錄"""
    print("\n" + "=" * 80)
    print("範例 2: 安全事件記錄")
    print("=" * 80)

    audit_logger = AuditLogger()

    # 記錄認證失敗
    audit_logger.log_auth_failure(
        user_id="user123", ip_address="192.168.1.1", reason="Invalid password"
    )

    # 記錄權限拒絕
    audit_logger.log_permission_denied(
        user_id="user123", resource="/admin/users", action="delete", reason="Not admin"
    )

    # 獲取安全事件
    security_events = audit_logger.get_security_events()
    print(f"\n安全事件數: {len(security_events)}")


if __name__ == "__main__":
    example_1_basic_logging()
    example_2_security_events()
    print("\n審計日誌範例完成！")
