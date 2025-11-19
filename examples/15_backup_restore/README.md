# 資料備份和恢復系統

完整的備份和恢復解決方案，支援資料庫、檔案和配置備份。

## 功能特性

- ✅ 完整備份（FULL）
- ✅ 增量備份（INCREMENTAL）
- ✅ 差異備份（DIFFERENTIAL）
- ✅ 資料庫備份
- ✅ 檔案備份
- ✅ 配置備份
- ✅ 自動壓縮（tar.gz）
- ✅ 備份元數據管理
- ✅ 自動清理舊備份

## 快速開始

### 創建備份

```python
from src.medical_chatbot.backup import BackupManager

backup_manager = BackupManager(backup_dir="backups", keep_count=10)

# 完整備份
metadata = backup_manager.create_full_backup(
    include_database=True,
    include_files=True,
    include_config=True,
)

print(f"備份 ID: {metadata.backup_id}")
print(f"大小: {metadata.size_bytes / 1024 / 1024:.2f} MB")
```

### 恢復備份

```python
from src.medical_chatbot.backup import RestoreManager

restore_manager = RestoreManager(backup_manager)

result = restore_manager.restore_backup(
    backup_id="full_20240101_120000",
    restore_database=True,
    restore_files=True,
)

print(f"恢復成功: {result.success}")
```

### 列出備份

```python
backups = backup_manager.list_backups()

for backup in backups:
    print(f"{backup.backup_id} - {backup.status.value}")
    print(f"  時間: {backup.created_at}")
    print(f"  大小: {backup.size_bytes / 1024:.2f} KB")
```

## 備份類型

- **FULL**: 完整備份所有資料
- **INCREMENTAL**: 僅備份自上次備份以來修改的檔案
- **DIFFERENTIAL**: 備份自上次完整備份以來的所有修改
- **DATABASE**: 僅備份資料庫
- **FILES**: 僅備份檔案
- **CONFIG**: 僅備份配置

## 自動化

### 定期備份

```python
import schedule
import time

def daily_backup():
    backup_manager.create_full_backup()

# 每天凌晨 2 點執行
schedule.every().day.at("02:00").do(daily_backup)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### Cron 設置

```bash
# 每天凌晨 2 點執行備份
0 2 * * * python /path/to/backup_script.py
```

## 授權

MIT License
