# SAT-SA — Offline Database Backup & Disaster Recovery Guide

## 1. Overview
SAT-SA provides point-in-time database backup and atomic restoration with cryptographic SHA-256 verification. Because supervisory assessments and cryptographic audit logs are legally binding, backup and restore operations enforce tamper detection to prevent corrupted or tampered ledger restoration.

---

## 2. Point-in-Time Database Backup

### Automated CLI Tool
```powershell
python scripts/backup_db.py [optional_output_directory]
```

### Python API Integration
```python
from app.core.backup import DatabaseBackupManager

# Creates atomic SQLite online backup (safe during active WAL transactions)
meta = DatabaseBackupManager.create_backup(output_dir="data/backups")
print(f"Backup File: {meta['backup_path']}")
print(f"SHA-256 Checksum: {meta['sha256_checksum']}")
```

### Generated Artifacts
1. `data/backups/satsa_backup_<YYYYMMDD_HHMMSS>.db`: The consistent SQLite binary database snapshot.
2. `data/backups/satsa_backup_<YYYYMMDD_HHMMSS>.db.sha256`: The SHA-256 sidecar checksum.
3. `data/backups/satsa_backup_<YYYYMMDD_HHMMSS>.db.json`: JSON metadata including size, timestamp, and status.

---

## 3. Cryptographic Verification & Restoration

### Verification Prior to Restoration
Before restoring a database backup, SAT-SA re-computes its SHA-256 hash and executes `PRAGMA integrity_check` on the SQLite binary. If bytes have been altered or corrupted, restoration is strictly blocked with a `ValueError`.

### Executing Database Restore
```powershell
python scripts/restore_db.py data/backups/satsa_backup_20260901_120000.db
```

### Python API Restore
```python
from app.core.backup import DatabaseBackupManager

result = DatabaseBackupManager.restore_backup(
    backup_path="data/backups/satsa_backup_20260901_120000.db"
)
print(f"Restored to: {result['target_database']}")
print(f"Verified Checksum: {result['verified_checksum']}")
```

---

## 4. Disaster Recovery Checklist
1. **Host Server Failure:**
   - Deploy SAT-SA offline bundle to new host system.
   - Place latest verified backup `.db` and `.sha256` files in `data/backups/`.
   - Run `python scripts/restore_db.py <backup_file>`.
   - Launch platform via `scripts/start_offline_satsa.bat` (or `.sh`).
   - Run `python scripts/health_check.py 8000` to confirm ready state.
2. **Audit Ledger Continuity Post-Restore:**
   - Navigate to **Reports & Audit Trail** tab in UI.
   - Click **Verify Audit Integrity** to re-verify cryptographic hash chain continuity.
