"""Tests for Threat Mapping, Context Enrichment and Risk Engine Isolation."""
import json
import os
import pytest
from app.intelligence.config import get_data_dir
from app.intelligence.mapper import SATSAThreatMapper
from app.intelligence.enrichment_engine import ThreatEnrichmentEngine
from app.intelligence.models import MappingType


def test_satsa_threat_mapper_rules():
    t_id, m_type, just, conf = SATSAThreatMapper.map_rule_to_technique("NEG-01")
    assert t_id == "T1562.002"
    assert m_type == MappingType.DIRECT
    assert conf == 1.0

    t_id, m_type, just, conf = SATSAThreatMapper.map_rule_to_technique("GAP-01")
    assert t_id == "T1562"
    assert m_type == MappingType.SUPPORTED_INFERENCE
    assert conf == 0.85

    t_id, m_type, just, conf = SATSAThreatMapper.map_rule_to_technique("NON_EXISTENT_RULE")
    assert t_id is None
    assert m_type == MappingType.UNMAPPED


def test_asset_and_finding_enrichment():
    data_dir = get_data_dir()
    with open(os.path.join(data_dir, "normalized", "nvd_normalized.json"), "r", encoding="utf-8") as f:
        norm_nvd = json.load(f)
    with open(os.path.join(data_dir, "normalized", "cisa_kev_normalized.json"), "r", encoding="utf-8") as f:
        norm_kev = json.load(f)
    with open(os.path.join(data_dir, "normalized", "attack_normalized.json"), "r", encoding="utf-8") as f:
        norm_att = json.load(f)

    enricher = ThreatEnrichmentEngine(norm_nvd, norm_kev, norm_att)
    
    # Asset Enrichment
    ctx_asset = enricher.enrich_asset("WEB_SERVER", "PROD_WEB_01")
    assert ctx_asset.cve_id == "CVE-2021-44228"
    assert ctx_asset.cvss_base_score == 10.0
    assert ctx_asset.is_cisa_kev is True
    assert "APT29" in ctx_asset.threat_groups

    # Finding Enrichment
    ctx_finding = enricher.enrich_finding("NEG-03")
    assert any(t["id"] == "T1070.001" for t in ctx_finding.attack_techniques)
