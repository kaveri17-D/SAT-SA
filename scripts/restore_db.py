"""Database Restore CLI Script for SAT-SA."""
import sys
import os
import json

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.backup import DatabaseBackupManager

def main():
    if len(sys.argv) < 2:
        print("Usage: python restore_db.py <path_to_backup_file.db> [optional_target_db_path]")
        return 1

    backup_path = os.path.abspath(sys.argv[1])
    target_path = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else None

    print(f"[*] Validating and restoring database from: {backup_path}")
    try:
        res = DatabaseBackupManager.restore_backup(backup_path=backup_path, target_db_path=target_path)
        print(f"[+] Database restored successfully and verified!")
        print(f"    Source: {res['source_backup']}")
        print(f"    Target: {res['target_database']}")
        print(f"    Verified SHA-256: {res['verified_checksum']}")
        return 0
    except Exception as e:
        print(f"[-] Restore failed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
