"""SAT-SA Cyber Threat Intelligence & Real-World Security Data Foundation Package."""

from app.intelligence.config import get_data_dir
from app.intelligence.models import (
    AttackTactic, AttackTechnique, AttackGroup, AttackSoftware, AttackMitigation,
    KEVRecord, NVDRecord, MappingType, SecurityEnrichmentContext,
    DataQualityReport, ScenarioDefinition, GroundTruthEntry
)
from app.intelligence.cpe_matcher import CPE23Uri, CPEMatcher, CPEMatchResult, MatchStatus
from app.intelligence.parsers.attack_stix_parser import AttackSTIXParser
from app.intelligence.parsers.cisa_kev_parser import CISAKEVParser
from app.intelligence.parsers.nvd_parser import NVDParser
from app.intelligence.normalizer import ThreatIntelligenceNormalizer
from app.intelligence.cross_source import CrossSourceConsistencyValidator
from app.intelligence.mapper import SATSAThreatMapper
from app.intelligence.enrichment_engine import ThreatEnrichmentEngine
from app.intelligence.manifest_manager import DatasetManifestManager
from app.intelligence.benchmark_builder import Phase13BenchmarkBuilder
from app.intelligence.scalability import Phase13ScalabilityBenchmark

__all__ = [
    "get_data_dir",
    "AttackTactic",
    "AttackTechnique",
    "AttackGroup",
    "AttackSoftware",
    "AttackMitigation",
    "KEVRecord",
    "NVDRecord",
    "MappingType",
    "SecurityEnrichmentContext",
    "DataQualityReport",
    "ScenarioDefinition",
    "GroundTruthEntry",
    "CPE23Uri",
    "CPEMatcher",
    "CPEMatchResult",
    "MatchStatus",
    "AttackSTIXParser",
    "CISAKEVParser",
    "NVDParser",
    "ThreatIntelligenceNormalizer",
    "CrossSourceConsistencyValidator",
    "SATSAThreatMapper",
    "ThreatEnrichmentEngine",
    "DatasetManifestManager",
    "Phase13BenchmarkBuilder",
    "Phase13ScalabilityBenchmark",
]
