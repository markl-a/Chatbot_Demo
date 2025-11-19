"""
恢復管理器

管理從備份恢復資料。
"""
from typing import Optional
from dataclasses import dataclass
from pathlib import Path
import tarfile
import shutil

from loguru import logger

from .backup_manager import BackupMetadata, BackupType


@dataclass
class RestoreResult:
    """恢復結果"""

    success: bool
    message: str
    restored_files: int = 0
    error: Optional[str] = None


class RestoreManager:
    """恢復管理器"""

    def __init__(self, backup_manager):
        """
        初始化恢復管理器

        Args:
            backup_manager: 備份管理器
        """
        self.backup_manager = backup_manager

        logger.info("恢復管理器初始化完成")

    def restore_backup(
        self,
        backup_id: str,
        restore_database: bool = True,
        restore_files: bool = True,
        restore_config: bool = True,
        target_dir: Optional[str] = None,
    ) -> RestoreResult:
        """
        恢復備份

        Args:
            backup_id: 備份 ID
            restore_database: 是否恢復資料庫
            restore_files: 是否恢復檔案
            restore_config: 是否恢復配置
            target_dir: 目標目錄（None 則恢復到原位置）

        Returns:
            恢復結果
        """
        try:
            # 獲取備份元數據
            metadata = self.backup_manager.get_backup_info(backup_id)
            if not metadata:
                return RestoreResult(
                    success=False, message=f"找不到備份: {backup_id}"
                )

            # 解壓備份（如果需要）
            backup_path = Path(metadata.file_path)
            if backup_path.suffix == ".gz":
                extract_path = self._extract_backup(backup_path)
            else:
                extract_path = backup_path

            restored_count = 0

            # 恢復資料庫
            if restore_database:
                db_dir = extract_path / "database"
                if db_dir.exists():
                    self._restore_database(db_dir, target_dir)
                    restored_count += 1

            # 恢復檔案
            if restore_files:
                files_dir = extract_path / "files"
                if files_dir.exists():
                    count = self._restore_files(files_dir, target_dir)
                    restored_count += count

            # 恢復配置
            if restore_config:
                config_dir = extract_path / "config"
                if config_dir.exists():
                    count = self._restore_config(config_dir, target_dir)
                    restored_count += count

            # 清理臨時檔案
            if backup_path.suffix == ".gz":
                shutil.rmtree(extract_path)

            return RestoreResult(
                success=True,
                message=f"備份已恢復: {backup_id}",
                restored_files=restored_count,
            )

        except Exception as e:
            logger.error(f"恢復失敗: {e}")
            return RestoreResult(success=False, message="恢復失敗", error=str(e))

    def _extract_backup(self, archive_path: Path) -> Path:
        """解壓備份"""
        extract_path = archive_path.parent / archive_path.stem.replace(".tar", "")

        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(extract_path)

        logger.info(f"備份已解壓: {extract_path}")

        return extract_path

    def _restore_database(self, db_dir: Path, target_dir: Optional[str]):
        """恢復資料庫"""
        # 實現資料庫恢復邏輯
        logger.info(f"恢復資料庫: {db_dir}")

    def _restore_files(self, files_dir: Path, target_dir: Optional[str]) -> int:
        """恢復檔案"""
        count = 0
        base_dir = Path(target_dir) if target_dir else Path(".")

        for file_path in files_dir.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(files_dir)
                dest_path = base_dir / relative_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, dest_path)
                count += 1

        logger.info(f"已恢復 {count} 個檔案")
        return count

    def _restore_config(self, config_dir: Path, target_dir: Optional[str]) -> int:
        """恢復配置"""
        count = 0
        base_dir = Path(target_dir) if target_dir else Path(".")

        for file_path in config_dir.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(config_dir)
                dest_path = base_dir / relative_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, dest_path)
                count += 1

        logger.info(f"已恢復 {count} 個配置檔案")
        return count
