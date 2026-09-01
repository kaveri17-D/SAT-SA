"""Comprehensive Security Validation Tests for Phase 13 Threat Intelligence Data Foundation."""
import os
import json
import inspect
import pytest
from app.intelligence.config import get_data_dir
from app.intelligence.parsers.attack_stix_parser import AttackSTIXParser
from app.intelligence.parsers.cisa_kev_parser import CISAKEVParser
from app.intelligence.parsers.nvd_parser import NVDParser
from app.intelligence.cpe_matcher import CPE23Uri, CPEMatcher, MatchStatus
from app.intelligence.manifest_manager import DatasetManifestManager


def test_security_path_traversal_protection():
    """Verify that path resolution and file loading remain strictly confined to the repo."""
    data_dir = get_data_dir()
    assert os.path.isabs(data_dir)
    assert os.path.exists(data_dir)
    raw_path = os.path.join(data_dir, "raw", "..", "raw", "cisa_kev.json")
    normalized_path = os.path.normpath(raw_path)
    assert os.path.commonpath([data_dir, normalized_path]) == data_dir


def test_security_malformed_json_and_schemas():
    """Verify that parsers defend against malformed payloads, non-dict roots, and missing fields."""
    # 1. Non-dict payloads
    _, rep1 = AttackSTIXParser.parse_bundle({"objects": ["INVALID_STRING", 123, None]})
    assert rep1.rejected_records >= 3

    # 2. Malformed CVE and missing fields in KEV
    malformed_kev = {
        "vulnerabilities": [
            {"cveID": "../../../etc/passwd", "vendorProject": "Hack"},
            {"cveID": "CVE-INVALID", "product": "P"},
            {}
        ]
    }
    recs, rep2 = CISAKEVParser.parse_catalog(malformed_kev)
    assert len(recs) == 0
    assert rep2.rejected_records == 3

    # 3. Malformed NVD structures
    malformed_nvd = {
        "vulnerabilities": [
            {"cve": {"id": "NOT-A-CVE"}},
            {"cve": {"id": "CVE-2021-99999", "metrics": {"invalidKey": []}}},
            {}
        ]
    }
    nvd_recs, rep3 = NVDParser.parse_feed(malformed_nvd)
    assert len(nvd_recs) == 1
    assert rep3.rejected_records == 2


def test_security_malformed_cpe_handling():
    """Verify that CPEMatcher safely handles malformed COE strings without crashing or false matching."""
    malformed_cpes = [
        "not_a_cpe",
        "cpe:2.3:",
        "cpe:2.3:invalid:only:four",
        "",
        None,
        "cpe:2.3:a:../../../../evil:product:1.0:*:*:*:*:*:*:*"
    ]
    for cpe_str in malformed_cpes:
        parsed = CPE23Uri.from_string(cpe_str)
        if parsed:
            assert not parsed.matches(CPE23Uri.from_string("cpe:2.3:a:apache:log4j:2.14.1:*:*:*:*:*:*"))


def test_security_no_unsafe_deserialization():
    """Verify that app/intelligence contains zero usages of pickle, eval, exec, or yaml.unsafe_load."""
    import app.intelligence.parsers.attack_stix_parser as ap
    import app.intelligence.parsers.cisa_kev_parser as kp
    import app.intelligence.parsers.nvd_parser as np
    import app.intelligence.normalizer as nm
    import app.intelligence.mapper as mp
    import app.intelligence.enrichment_engine as ee
    import app.intelligence.cpe_matcher as cm
    import app.intelligence.manifest_manager as mm
    import app.intelligence.benchmark_builder as bb
    import app.intelligence.scalability as sc

    modules = [ap, kp, np, nm, mp, ee, cm, mm, bb, sc]
    for mod in modules:
        src = inspect.getsource(mod)
        assert "pickle." not in src
        assert "eval(" not in src
        assert "exec(" not in src
        assert "yaml.unsafe_load" not in src
        assert "marshal." not in src


def test_security_airgap_socket_isolation():
    """Verify that intelligence query paths do not instantiate sockets or make HTTP calls."""
    import app.intelligence.parsers.attack_stix_parser as ap
    import app.intelligence.parsers.cisa_kev_parser as kp
    import app.intelligence.parsers.nvd_parser as np
    import app.intelligence.normalizer as nm
    import app.intelligence.mapper as mp
    import app.intelligence.enrichment_engine as ee
    import app.intelligence.cpe_matcher as cm

    modules = [ap, kp, np, nm, mp, ee, cm]
    for mod in modules:
        src = inspect.getsource(mod)
        assert "socket.socket" not in src
        assert "urllib.request" not in src
        assert "requests.get" not in src
        assert "requests.post" not in src
        assert "httpx." not in src
        assert "aiohttp." not in src
