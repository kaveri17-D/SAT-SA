"""Tests for Cryptographic Manifests and Tamper Detection."""
import json
import os
import pytest
from app.intelligence.config import get_data_dir
from app.intelligence.manifest_manager import DatasetManifestManager


def test_manifest_verification_on_authentic_files():
    data_dir = get_data_dir()
    with open(os.path.join(data_dir, "manifests", "attack_enterprise_manifest.json"), "r", encoding="utf-8") as f:
        mf = json.load(f)
    target_path = os.path.join(data_dir, "raw", "attack_enterprise_stix21.json")
    is_valid, msg = DatasetManifestManager.verify_manifest(mf, target_path)
    assert is_valid is True
    assert "Checksum verified" in msg


def test_manifest_tamper_detection_on_altered_content(tmp_path):
    fake_file = tmp_path / "tampered_catalog.json"
    fake_file.write_text('{"vulnerabilities": []}', encoding="utf-8")
    
    mf = DatasetManifestManager.create_manifest(
        dataset_name="Test KEV",
        source_org="CISA",
        source_url="http://example.com",
        filepath=str(fake_file),
        version="1.0",
        record_count=0
    )
    
    # Tamper with 1 byte
    fake_file.write_text('{"vulnerabilities": ["TAMPERED"]}', encoding="utf-8")
    is_valid, msg = DatasetManifestManager.verify_manifest(mf, str(fake_file))
    assert is_valid is False
    assert "Tamper detected" in msg
