"""Offline Deployment Bundle Packager for SAT-SA."""
import os
import sys
import zipfile
import hashlib
import json
from datetime import datetime, timezone

def compute_sha256(filepath):
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def build_offline_bundle(root_dir=None, output_dir=None):
    if not root_dir:
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if not output_dir:
        output_dir = os.path.join(root_dir, "dist_offline")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    bundle_name = f"satsa_offline_v1.0.0_{timestamp}"
    zip_path = os.path.join(output_dir, f"{bundle_name}.zip")
    manifest_path = os.path.join(output_dir, f"{bundle_name}_manifest.json")

    print(f"[*] Building SAT-SA Offline Package: {zip_path}")

    # Files and directories to include
    include_paths = [
        ("backend/app", "backend/app"),
        ("backend/alembic", "backend/alembic"),
        ("backend/alembic.ini", "backend/alembic.ini"),
        ("backend/requirements.txt", "backend/requirements.txt"),
        ("backend/Dockerfile", "backend/Dockerfile"),
        ("frontend/dist", "frontend/dist"),
        ("scripts", "scripts"),
        ("docker-compose.yml", "docker-compose.yml"),
        (".env.example", ".env.example"),
        ("README.md", "README.md"),
    ]

    manifest = {
        "package_name": bundle_name,
        "version": "1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "STRICT_LOCAL_ONLY_AIRGAP",
        "files": []
    }

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for src_rel, arc_rel in include_paths:
            src_full = os.path.join(root_dir, src_rel)
            if not os.path.exists(src_full):
                print(f"[!] Warning: Missing path {src_rel}, skipping.")
                continue

            if os.path.isfile(src_full):
                zipf.write(src_full, arc_rel)
                f_hash = compute_sha256(src_full)
                manifest["files"].append({
                    "path": arc_rel,
                    "sha256": f_hash,
                    "size_bytes": os.path.getsize(src_full)
                })
            elif os.path.isdir(src_full):
                for root, dirs, files in os.walk(src_full):
                    # Skip __pycache__ and test databases
                    if "__pycache__" in root or ".pytest_cache" in root:
                        continue
                    for file in files:
                        if file.endswith((".pyc", ".db", ".sqlite")):
                            continue
                        f_path = os.path.join(root, file)
                        rel_in_dir = os.path.relpath(f_path, src_full)
                        arc_path = os.path.join(arc_rel, rel_in_dir).replace("\\", "/")
                        zipf.write(f_path, arc_path)
                        f_hash = compute_sha256(f_path)
                        manifest["files"].append({
                            "path": arc_path,
                            "sha256": f_hash,
                            "size_bytes": os.path.getsize(f_path)
                        })

    # Save manifest
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # Compute package checksum
    pkg_hash = compute_sha256(zip_path)
    checksum_file = f"{zip_path}.sha256"
    with open(checksum_file, "w", encoding="utf-8") as f:
        f.write(f"{pkg_hash}  {os.path.basename(zip_path)}\n")

    pkg_size_mb = round(os.path.getsize(zip_path) / (1024 * 1024), 2)
    print(f"[+] Package created successfully!")
    print(f"    ZIP Archive: {zip_path} ({pkg_size_mb} MB)")
    print(f"    SHA-256: {pkg_hash}")
    print(f"    Total files bundled: {len(manifest['files'])}")
    return {
        "zip_path": zip_path,
        "sha256": pkg_hash,
        "size_mb": pkg_size_mb,
        "file_count": len(manifest["files"])
    }

if __name__ == "__main__":
    build_offline_bundle()
