"""
備份管理器

管理資料庫、檔案和配置的備份。
"""
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import json
import shutil
import tarfile
import gzip

from loguru import logger


# ============================================================================
# 備份類型和狀態
# ============================================================================


class BackupType(Enum):
    """備份類型"""

    FULL = "full"  # 完整備份
    INCREMENTAL = "incremental"  # 增量備份
    DIFFERENTIAL = "differential"  # 差異備份
    DATABASE = "database"  # 僅資料庫
    FILES = "files"  # 僅檔案
    CONFIG = "config"  # 僅配置


class BackupStatus(Enum):
    """備份狀態"""

    PENDING = "pending"  # 等待中
    RUNNING = "running"  # 執行中
    COMPLETED = "completed"  # 完成
    FAILED = "failed"  # 失敗


# ============================================================================
# 備份元數據
# ============================================================================


@dataclass
class BackupMetadata:
    """備份元數據"""

    backup_id: str
    backup_type: BackupType
    status: BackupStatus
    created_at: datetime
    size_bytes: int = 0
    duration_seconds: float = 0.0
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        data = asdict(self)
        data["backup_type"] = self.backup_type.value
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        return data

    def to_json(self) -> str:
        """轉換為 JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BackupMetadata":
        """從字典創建"""
        data["backup_type"] = BackupType(data["backup_type"])
        data["status"] = BackupStatus(data["status"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)


# ============================================================================
# 備份管理器
# ============================================================================


class BackupManager:
    """備份管理器"""

    def __init__(
        self,
        backup_dir: str = "backups",
        database_manager=None,
        compress: bool = True,
        keep_count: int = 10,
    ):
        """
        初始化備份管理器

        Args:
            backup_dir: 備份目錄
            database_manager: 資料庫管理器
            compress: 是否壓縮
            keep_count: 保留的備份數量
        """
        self.backup_dir = Path(backup_dir)
        self.database_manager = database_manager
        self.compress = compress
        self.keep_count = keep_count

        # 創建備份目錄
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # 元數據目錄
        self.metadata_dir = self.backup_dir / "metadata"
        self.metadata_dir.mkdir(exist_ok=True)

        logger.info(f"備份管理器初始化完成: {self.backup_dir}")

    # ========================================================================
    # 完整備份
    # ========================================================================

    def create_full_backup(
        self,
        include_database: bool = True,
        include_files: bool = True,
        include_config: bool = True,
        file_patterns: Optional[List[str]] = None,
    ) -> BackupMetadata:
        """
        創建完整備份

        Args:
            include_database: 是否包含資料庫
            include_files: 是否包含檔案
            include_config: 是否包含配置
            file_patterns: 要備份的檔案模式列表

        Returns:
            備份元數據
        """
        import time

        # 生成備份 ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_id = f"full_{timestamp}"

        # 創建元數據
        metadata = BackupMetadata(
            backup_id=backup_id,
            backup_type=BackupType.FULL,
            status=BackupStatus.PENDING,
            created_at=datetime.now(),
        )

        try:
            # 更新狀態
            metadata.status = BackupStatus.RUNNING
            self._save_metadata(metadata)

            start_time = time.time()

            # 創建備份目錄
            backup_path = self.backup_dir / backup_id
            backup_path.mkdir(exist_ok=True)

            # 備份資料庫
            if include_database and self.database_manager:
                logger.info("備份資料庫...")
                self._backup_database(backup_path)

            # 備份檔案
            if include_files:
                logger.info("備份檔案...")
                self._backup_files(backup_path, file_patterns)

            # 備份配置
            if include_config:
                logger.info("備份配置...")
                self._backup_config(backup_path)

            # 壓縮備份
            if self.compress:
                logger.info("壓縮備份...")
                archive_path = self._compress_backup(backup_path)
                metadata.file_path = str(archive_path)

                # 刪除原始備份目錄
                shutil.rmtree(backup_path)
            else:
                metadata.file_path = str(backup_path)

            # 計算大小和時間
            if self.compress:
                metadata.size_bytes = Path(metadata.file_path).stat().st_size
            else:
                metadata.size_bytes = sum(
                    f.stat().st_size for f in backup_path.rglob("*") if f.is_file()
                )

            metadata.duration_seconds = time.time() - start_time
            metadata.status = BackupStatus.COMPLETED

            logger.info(f"完整備份完成: {backup_id}")

        except Exception as e:
            logger.error(f"備份失敗: {e}")
            metadata.status = BackupStatus.FAILED
            metadata.error_message = str(e)
            raise

        finally:
            # 保存元數據
            self._save_metadata(metadata)

            # 清理舊備份
            self._cleanup_old_backups()

        return metadata

    # ========================================================================
    # 增量備份
    # ========================================================================

    def create_incremental_backup(
        self, base_backup_id: Optional[str] = None
    ) -> BackupMetadata:
        """
        創建增量備份

        僅備份自上次備份以來修改的檔案。

        Args:
            base_backup_id: 基礎備份 ID（None 則使用最新的完整備份）

        Returns:
            備份元數據
        """
        import time

        # 獲取基礎備份
        if base_backup_id is None:
            base_metadata = self._get_latest_full_backup()
            if not base_metadata:
                raise ValueError("找不到完整備份，請先創建完整備份")
        else:
            base_metadata = self._load_metadata(base_backup_id)

        # 生成備份 ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_id = f"incr_{timestamp}"

        metadata = BackupMetadata(
            backup_id=backup_id,
            backup_type=BackupType.INCREMENTAL,
            status=BackupStatus.PENDING,
            created_at=datetime.now(),
            metadata={"base_backup_id": base_metadata.backup_id},
        )

        try:
            metadata.status = BackupStatus.RUNNING
            start_time = time.time()

            backup_path = self.backup_dir / backup_id
            backup_path.mkdir(exist_ok=True)

            # 僅備份修改的檔案
            self._backup_modified_files(backup_path, base_metadata.created_at)

            # 壓縮
            if self.compress:
                archive_path = self._compress_backup(backup_path)
                metadata.file_path = str(archive_path)
                shutil.rmtree(backup_path)
            else:
                metadata.file_path = str(backup_path)

            metadata.size_bytes = Path(metadata.file_path).stat().st_size if self.compress else 0
            metadata.duration_seconds = time.time() - start_time
            metadata.status = BackupStatus.COMPLETED

            logger.info(f"增量備份完成: {backup_id}")

        except Exception as e:
            logger.error(f"增量備份失敗: {e}")
            metadata.status = BackupStatus.FAILED
            metadata.error_message = str(e)
            raise

        finally:
            self._save_metadata(metadata)

        return metadata

    # ========================================================================
    # 資料庫備份
    # ========================================================================

    def _backup_database(self, backup_path: Path):
        """
        備份資料庫

        Args:
            backup_path: 備份路徑
        """
        if not self.database_manager:
            logger.warning("沒有資料庫管理器，跳過資料庫備份")
            return

        db_backup_dir = backup_path / "database"
        db_backup_dir.mkdir(exist_ok=True)

        # SQLite 備份
        if "sqlite" in str(self.database_manager.engine.url):
            # 複製 SQLite 檔案
            db_file = str(self.database_manager.engine.url).replace("sqlite:///", "")
            if Path(db_file).exists():
                shutil.copy2(db_file, db_backup_dir / Path(db_file).name)
                logger.info(f"SQLite 資料庫已備份: {db_file}")

        # PostgreSQL/MySQL 備份
        else:
            # 使用 pg_dump 或 mysqldump
            # 這裡需要實現具體的備份邏輯
            logger.warning("PostgreSQL/MySQL 備份需要實現")

    # ========================================================================
    # 檔案備份
    # ========================================================================

    def _backup_files(self, backup_path: Path, patterns: Optional[List[str]] = None):
        """
        備份檔案

        Args:
            backup_path: 備份路徑
            patterns: 檔案模式列表
        """
        files_backup_dir = backup_path / "files"
        files_backup_dir.mkdir(exist_ok=True)

        # 預設備份模式
        if patterns is None:
            patterns = [
                "logs/**/*.log",
                "data/**/*",
                "uploads/**/*",
            ]

        # 備份匹配的檔案
        for pattern in patterns:
            for file_path in Path(".").glob(pattern):
                if file_path.is_file():
                    # 保留目錄結構
                    relative_path = file_path
                    dest_path = files_backup_dir / relative_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)

                    shutil.copy2(file_path, dest_path)

        logger.info(f"檔案已備份到: {files_backup_dir}")

    def _backup_modified_files(self, backup_path: Path, since: datetime):
        """
        備份修改的檔案

        Args:
            backup_path: 備份路徑
            since: 自從該時間以來修改的檔案
        """
        files_backup_dir = backup_path / "files"
        files_backup_dir.mkdir(exist_ok=True)

        patterns = ["logs/**/*.log", "data/**/*", "uploads/**/*"]

        for pattern in patterns:
            for file_path in Path(".").glob(pattern):
                if file_path.is_file():
                    # 檢查修改時間
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime > since:
                        relative_path = file_path
                        dest_path = files_backup_dir / relative_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(file_path, dest_path)

        logger.info(f"修改的檔案已備份: {files_backup_dir}")

    # ========================================================================
    # 配置備份
    # ========================================================================

    def _backup_config(self, backup_path: Path):
        """
        備份配置

        Args:
            backup_path: 備份路徑
        """
        config_backup_dir = backup_path / "config"
        config_backup_dir.mkdir(exist_ok=True)

        # 備份配置檔案
        config_files = [
            ".env",
            ".env.example",
            "config/**/*.json",
            "config/**/*.yaml",
            "config/**/*.yml",
        ]

        for pattern in config_files:
            for file_path in Path(".").glob(pattern):
                if file_path.is_file():
                    dest_path = config_backup_dir / file_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, dest_path)

        logger.info(f"配置已備份: {config_backup_dir}")

    # ========================================================================
    # 壓縮和解壓
    # ========================================================================

    def _compress_backup(self, backup_path: Path) -> Path:
        """
        壓縮備份

        Args:
            backup_path: 備份路徑

        Returns:
            壓縮檔案路徑
        """
        archive_path = backup_path.with_suffix(".tar.gz")

        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(backup_path, arcname=backup_path.name)

        logger.info(f"備份已壓縮: {archive_path}")

        return archive_path

    # ========================================================================
    # 元數據管理
    # ========================================================================

    def _save_metadata(self, metadata: BackupMetadata):
        """保存元數據"""
        metadata_file = self.metadata_dir / f"{metadata.backup_id}.json"

        with open(metadata_file, "w", encoding="utf-8") as f:
            f.write(metadata.to_json())

    def _load_metadata(self, backup_id: str) -> Optional[BackupMetadata]:
        """加載元數據"""
        metadata_file = self.metadata_dir / f"{backup_id}.json"

        if not metadata_file.exists():
            return None

        with open(metadata_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return BackupMetadata.from_dict(data)

    def _get_latest_full_backup(self) -> Optional[BackupMetadata]:
        """獲取最新的完整備份"""
        metadata_files = sorted(self.metadata_dir.glob("full_*.json"), reverse=True)

        for metadata_file in metadata_files:
            with open(metadata_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                metadata = BackupMetadata.from_dict(data)
                if metadata.status == BackupStatus.COMPLETED:
                    return metadata

        return None

    # ========================================================================
    # 清理
    # ========================================================================

    def _cleanup_old_backups(self):
        """清理舊備份"""
        # 獲取所有備份
        backups = []
        for metadata_file in self.metadata_dir.glob("*.json"):
            with open(metadata_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                metadata = BackupMetadata.from_dict(data)
                backups.append(metadata)

        # 按時間排序
        backups.sort(key=lambda x: x.created_at, reverse=True)

        # 刪除超過保留數量的備份
        for backup in backups[self.keep_count :]:
            self.delete_backup(backup.backup_id)

    def delete_backup(self, backup_id: str):
        """刪除備份"""
        metadata = self._load_metadata(backup_id)
        if not metadata:
            logger.warning(f"找不到備份: {backup_id}")
            return

        # 刪除備份檔案
        if metadata.file_path and Path(metadata.file_path).exists():
            if Path(metadata.file_path).is_file():
                Path(metadata.file_path).unlink()
            else:
                shutil.rmtree(metadata.file_path)

        # 刪除元數據
        metadata_file = self.metadata_dir / f"{backup_id}.json"
        if metadata_file.exists():
            metadata_file.unlink()

        logger.info(f"備份已刪除: {backup_id}")

    # ========================================================================
    # 查詢
    # ========================================================================

    def list_backups(
        self, backup_type: Optional[BackupType] = None
    ) -> List[BackupMetadata]:
        """
        列出所有備份

        Args:
            backup_type: 篩選備份類型

        Returns:
            備份元數據列表
        """
        backups = []

        for metadata_file in self.metadata_dir.glob("*.json"):
            with open(metadata_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                metadata = BackupMetadata.from_dict(data)

                if backup_type is None or metadata.backup_type == backup_type:
                    backups.append(metadata)

        # 按時間排序
        backups.sort(key=lambda x: x.created_at, reverse=True)

        return backups

    def get_backup_info(self, backup_id: str) -> Optional[BackupMetadata]:
        """獲取備份資訊"""
        return self._load_metadata(backup_id)
