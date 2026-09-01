"""Tests for Phase 13 Cyber Threat Intelligence Parsers."""
import json
import os
import pytest
from app.intelligence.config import get_data_dir
from app.intelligence.parsers.attack_stix_parser import AttackSTIXParser
from app.intelligence.parsers.cisa_kev_parser import CISAKEVParser
from app.intelligence.parsers.nvd_parser import NVDParser


def test_attack_stix_parser():
    data_dir = get_data_dir()
    with open(os.path.join(data_dir, "raw", "attack_enterprise_stix21.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
    bundle, report = AttackSTIXParser.parse_bundle(data)
    assert len(bundle.tactics) >= 6
    assert len(bundle.techniques) >= 10
    assert len(bundle.groups) >= 4
    assert len(bundle.software) >= 4
    assert len(bundle.mitigations) >= 2
    assert len(bundle.relationships) >= 4
    assert report.valid_records >= 25
    assert report.deprecated_or_revoked >= 1


def test_cisa_kev_parser():
    data_dir = get_data_dir()
    with open(os.path.join(data_dir, "raw", "cisa_kev.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
    records, report = CISAKEVParser.parse_catalog(data)
    assert len(records) >= 15
    assert report.valid_records >= 15
    assert report.rejected_records == 0
    cves = [r.cve_id for r in records]
    assert "CVE-2021-44228" in cves
    assert "CVE-2023-34362" in cves
    assert "CVE-2020-1472" in cves


def test_nvd_parser():
    data_dir = get_data_dir()
    with open(os.path.join(data_dir, "raw", "nvd_cve_feed.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
    records, report = NVDParser.parse_feed(data)
    assert len(records) >= 10
    assert report.valid_records >= 10
    log4j = next((r for r in records if r.cve_id == "CVE-2021-44228"), None)
    assert log4j is not None
    assert log4j.cvss_v3_base_score == 10.0
    assert log4j.cvss_v3_severity == "CRITICAL"
    assert len(log4j.cpe_match_criteria) >= 1


def test_malformed_record_handling():
    malformed_kev = {
        "vulnerabilities": [
            {"cveID": "INVALID-ID", "vendorProject": "Test", "product": "P"},
            {"cveID": "CVE-2021-44228", "vendorProject": "Apache", "product": "Log4j", "vulnerabilityName": "V", "dateAdded": "2021-12-10", "shortDescription": "D", "requiredAction": "A", "knownRansomwareCampaignUse": "Known"}
        ]
    }
    recs, rep = CISAKEVParser.parse_catalog(malformed_kev)
    assert len(recs) == 1
    assert rep.malformed_ids == 1
    assert rep.rejected_records == 1
