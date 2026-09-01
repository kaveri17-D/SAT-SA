"""Tests for Deterministic Normalization and Cross-Source Consistency."""
import json
import os
import pytest
from app.intelligence.config import get_data_dir
from app.intelligence.normalizer import ThreatIntelligenceNormalizer
from app.intelligence.cross_source import CrossSourceConsistencyValidator


def test_deterministic_normalization():
    data_dir = get_data_dir()
    with open(os.path.join(data_dir, "normalized", "attack_normalized.json"), "r", encoding="utf-8") as f:
        norm_att = json.load(f)
    with open(os.path.join(data_dir, "normalized", "cisa_kev_normalized.json"), "r", encoding="utf-8") as f:
        norm_kev = json.load(f)
    
    assert "techniques" in norm_att
    assert "tactics" in norm_att
    assert "vulnerabilities" in norm_kev
    assert "CVE-2021-44228" in norm_kev["vulnerabilities"]


def test_cross_source_consistency():
    data_dir = get_data_dir()
    with open(os.path.join(data_dir, "normalized", "nvd_normalized.json"), "r", encoding="utf-8") as f:
        norm_nvd = json.load(f)
    with open(os.path.join(data_dir, "normalized", "cisa_kev_normalized.json"), "r", encoding="utf-8") as f:
        norm_kev = json.load(f)
    with open(os.path.join(data_dir, "normalized", "attack_normalized.json"), "r", encoding="utf-8") as f:
        norm_att = json.load(f)

    rep = CrossSourceConsistencyValidator.validate_cross_source(norm_nvd, norm_kev, norm_att)
    assert rep["overlap_cves_count"] >= 8
    assert "CVE-2021-44228" in rep["matching_cves"]
    assert "CVE-2022-3602" in rep["nvd_only_cves"]  # High CVSS unexploited control
