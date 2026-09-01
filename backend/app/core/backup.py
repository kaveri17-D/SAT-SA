"""Database Backup & Disaster Recovery Manager for SAT-SA."""
import os
import shutil
import sqlite3
import hashlib
import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from app.core.database import SessionLocal, Base, engine


class DatabaseBackupManager:
    """Manages point-in-time database backups, SHA-256 integrity verification, and atomic restoration."""

    @staticmethod
    def _compute_sha256(filepath: str) -> str:
        """Compute SHA-256 checksum of a file in streaming chunks."""
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    @classmethod
    def create_backup(cls, output_dir: str = None) -> dict:
        """Create an atomic SQLite point-in-time backup with SHA-256 sidecar checksum."""
        if not output_dir:
            output_dir = os.path.abspath(settings.BACKUP_DIR)
        os.makedirs(output_dir, exist_ok=True)

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_filename = f"satsa_backup_{timestamp_str}.db"
        backup_path = os.path.join(output_dir, backup_filename)
        checksum_path = f"{backup_path}.sha256"

        db_url = settings.active_database_url
        if db_url.startswith("sqlite:///"):
            src_db_path = db_url.replace("sqlite:///", "")
            if not os.path.isabs(src_db_path):
                src_db_path = os.path.abspath(src_db_path)

            # SQLite Online Backup API ensures clean snapshot under active WAL transactions
            src_conn = sqlite3.connect(src_db_path)
            dst_conn = sqlite3.connect(backup_path)
            try:
                src_conn.backup(dst_conn)
            finally:
                dst_conn.close()
                src_conn.close()
        else:
            raise NotImplementedError("Backup currently configured for SQLite single-file engine.")

        # Compute SHA-256 Checksum
        sha256_hash = cls._compute_sha256(backup_path)
        with open(checksum_path, "w", encoding="utf-8") as f:
            f.write(f"{sha256_hash}  {backup_filename}\n")

        file_size = os.path.getsize(backup_path)

        metadata = {
            "backup_filename": backup_filename,
            "backup_path": backup_path,
            "checksum_path": checksum_path,
            "sha256_checksum": sha256_hash,
            "file_size_bytes": file_size,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "SUCCESS"
        }

        meta_path = f"{backup_path}.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return metadata

    @classmethod
    def verify_backup_integrity(cls, backup_path: str) -> tuple[bool, str]:
        """Verify the cryptographic SHA-256 checksum and SQLite structure of a backup file."""
        if not os.path.exists(backup_path):
            return False, f"Backup file not found: {backup_path}"

        checksum_path = f"{backup_path}.sha256"
        if not os.path.exists(checksum_path):
            return False, f"Sidecar checksum file missing: {checksum_path}"

        with open(checksum_path, "r", encoding="utf-8") as f:
            expected_hash = f.read().strip().split()[0]

        actual_hash = cls._compute_sha256(backup_path)
        if actual_hash != expected_hash:
            return False, f"Checksum mismatch: expected {expected_hash}, computed {actual_hash}"

        # Verify SQLite DB can be opened and queried
        try:
            conn = sqlite3.connect(backup_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            row = cursor.fetchone()
            conn.close()
            if not row or row[0] != "ok":
                return False, f"SQLite integrity check failed: {row}"
        except Exception as e:
            return False, f"Database corruption error: {str(e)}"

        return True, "Backup integrity cryptographically verified"

    @classmethod
    def restore_backup(cls, backup_path: str, target_db_path: str = None) -> dict:
        """Atomically restore a database backup after strictly verifying its cryptographic checksum."""
        is_valid, msg = cls.verify_backup_integrity(backup_path)
        if not is_valid:
            raise ValueError(f"Cannot restore invalid backup: {msg}")

        if not target_db_path:
            db_url = settings.active_database_url
            if db_url.startswith("sqlite:///"):
                target_db_path = db_url.replace("sqlite:///", "")
                if not os.path.isabs(target_db_path):
                    target_db_path = os.path.abspath(target_db_path)
            else:
                raise NotImplementedError("Restore target resolution for non-sqlite engine.")

        # Atomic copy using SQLite backup API to active database target
        src_conn = sqlite3.connect(backup_path)
        dst_conn = sqlite3.connect(target_db_path)
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
            src_conn.close()

        return {
            "status": "RESTORED",
            "source_backup": backup_path,
            "target_database": target_db_path,
            "verified_checksum": cls._compute_sha256(target_db_path),
            "restored_at": datetime.now(timezone.utc).isoformat()
        }
