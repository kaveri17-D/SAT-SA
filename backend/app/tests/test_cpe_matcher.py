"""Tests for CPE 2.3 URI Matching and Asset Vulnerability Resolution."""
import json
import os
import pytest
from app.intelligence.config import get_data_dir
from app.intelligence.cpe_matcher import CPE23Uri, CPEMatcher, MatchStatus


def test_cpe23_uri_parsing():
    uri_str = "cpe:2.3:a:apache:log4j:2.14.1:*:*:*:*:*:*:*"
    cpe = CPE23Uri.from_string(uri_str)
    assert cpe is not None
    assert cpe.part == "a"
    assert cpe.vendor == "apache"
    assert cpe.product == "log4j"
    assert cpe.version == "2.14.1"


def test_cpe_matching_exact_and_version():
    data_dir = get_data_dir()
    with open(os.path.join(data_dir, "normalized", "nvd_normalized.json"), "r", encoding="utf-8") as f:
        nvd_catalog = json.load(f)
    
    matcher = CPEMatcher(nvd_catalog)
    
    # Exact Match
    res_exact = matcher.match_asset_cpe("apache", "log4j", "2.14.1")
    assert res_exact.status == MatchStatus.EXACT_MATCH
    assert "CVE-2021-44228" in res_exact.matched_cves

    # Version Wildcard Match
    res_wild = matcher.match_asset_cpe("microsoft", "windows_server_2019", "*")
    assert res_wild.status in [MatchStatus.EXACT_MATCH, MatchStatus.VERSION_MATCH]
    assert "CVE-2020-1472" in res_wild.matched_cves

    # Unmapped Asset
    res_unmapped = matcher.match_asset_cpe("generic_vendor", "unknown_product", "1.0")
    assert res_unmapped.status == MatchStatus.UNMAPPED
    assert len(res_unmapped.matched_cves) == 0
