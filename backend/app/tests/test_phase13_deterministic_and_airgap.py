"""Tests for Phase 13 Deterministic Rebuild and Air-Gap Compliance."""
import os
import json
import inspect
import pytest
from app.intelligence.config import get_data_dir
from app.intelligence.parsers.attack_stix_parser import AttackSTIXParser
from app.intelligence.parsers.cisa_kev_parser import CISAKEVParser
from app.intelligence.parsers.nvd_parser import NVDParser
from app.intelligence.normalizer import ThreatIntelligenceNormalizer


def test_deterministic_rebuild_verification():
    data_dir = get_data_dir()
    with open(os.path.join(data_dir, "raw", "attack_enterprise_stix21.json"), "r", encoding="utf-8") as f:
        raw_attack = json.load(f)
    with open(os.path.join(data_dir, "raw", "cisa_kev.json"), "r", encoding="utf-8") as f:
        raw_kev = json.load(f)
    with open(os.path.join(data_dir, "raw", "nvd_cve_feed.json"), "r", encoding="utf-8") as f:
        raw_nvd = json.load(f)

    # Pass 1
    b1, _ = AttackSTIXParser.parse_bundle(raw_attack)
    k1, _ = CISAKEVParser.parse_catalog(raw_kev)
    n1, _ = NVDParser.parse_feed(raw_nvd)
    norm_att1 = ThreatIntelligenceNormalizer.normalize_attack(b1)
    norm_kev1 = ThreatIntelligenceNormalizer.normalize_kev(k1)
    norm_nvd1 = ThreatIntelligenceNormalizer.normalize_nvd(n1)

    # Pass 2
    b2, _ = AttackSTIXParser.parse_bundle(raw_attack)
    k2, _ = CISAKEVParser.parse_catalog(raw_kev)
    n2, _ = NVDParser.parse_feed(raw_nvd)
    norm_att2 = ThreatIntelligenceNormalizer.normalize_attack(b2)
    norm_kev2 = ThreatIntelligenceNormalizer.normalize_kev(k2)
    norm_nvd2 = ThreatIntelligenceNormalizer.normalize_nvd(n2)

    # Assert 100% deterministic equality
    assert norm_att1 == norm_att2
    assert norm_kev1 == norm_kev2
    assert norm_nvd1 == norm_nvd2


def test_air_gap_offline_compliance():
    """Verify that app/intelligence contains zero network request libraries in runtime path."""
    import app.intelligence.parsers.attack_stix_parser as ap
    import app.intelligence.parsers.cisa_kev_parser as kp
    import app.intelligence.parsers.nvd_parser as np
    import app.intelligence.normalizer as nm
    import app.intelligence.mapper as mp
    import app.intelligence.enrichment_engine as ee
    import app.intelligence.cpe_matcher as cm

    for mod in [ap, kp, np, nm, mp, ee, cm]:
        src = inspect.getsource(mod)
        assert "urllib.request" not in src
        assert "requests.get" not in src
        assert "httpx.get" not in src
        assert "aiohttp" not in src
