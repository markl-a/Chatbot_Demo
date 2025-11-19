"""
基本備份和恢復範例
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.medical_chatbot.backup import BackupManager, RestoreManager, BackupType


def main():
    """主程序"""
    print("=" * 80)
    print("備份和恢復範例")
    print("=" * 80)

    # 創建備份管理器
    backup_manager = BackupManager(backup_dir="backups", keep_count=5)

    # 創建完整備份
    print("\n1. 創建完整備份...")
    metadata = backup_manager.create_full_backup(
        include_database=False,  # 示範用，不備份資料庫
        include_files=True,
        include_config=True,
    )

    print(f"   備份 ID: {metadata.backup_id}")
    print(f"   狀態: {metadata.status.value}")
    print(f"   大小: {metadata.size_bytes / 1024:.2f} KB")
    print(f"   時間: {metadata.duration_seconds:.2f} 秒")

    # 列出所有備份
    print("\n2. 列出所有備份...")
    backups = backup_manager.list_backups()
    for backup in backups:
        print(f"   {backup.backup_id} - {backup.status.value} - {backup.created_at}")

    # 恢復備份
    print("\n3. 恢復備份...")
    restore_manager = RestoreManager(backup_manager)
    result = restore_manager.restore_backup(
        backup_id=metadata.backup_id,
        restore_database=False,
        target_dir="restore_test",
    )

    print(f"   成功: {result.success}")
    print(f"   訊息: {result.message}")
    print(f"   恢復檔案數: {result.restored_files}")

    print("\n備份和恢復完成！")


if __name__ == "__main__":
    main()
