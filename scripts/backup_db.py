"""Database Backup CLI Script for SAT-SA."""
import sys
import os
import json

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.backup import DatabaseBackupManager

def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else None
    print("[*] Initiating SAT-SA point-in-time database backup...")
    try:
        meta = DatabaseBackupManager.create_backup(output_dir=out_dir)
        print(f"[+] Backup created successfully!")
        print(f"    File: {meta['backup_path']}")
        print(f"    SHA-256 Checksum: {meta['sha256_checksum']}")
        print(f"    Size: {meta['file_size_bytes']} bytes")
        return 0
    except Exception as e:
        print(f"[-] Backup failed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
