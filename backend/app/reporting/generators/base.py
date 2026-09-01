"""Base Report Generator for SAT-SA Reporting System."""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import (
    AnalysisRun, CSE, Asset, Alert, Finding, RiskScore, Evidence,
    ReportType, FindingSeverity
)
from app.intelligence.enrichment_engine import ThreatEnrichmentEngine


class BaseReportGenerator:
    """Base report generator extracting canonical state from SAT-SA database."""

    def __init__(self, db: Session, analysis_run: AnalysisRun, cse: Optional[CSE] = None, enricher: Optional[ThreatEnrichmentEngine] = None):
        self.db = db
        self.run = analysis_run
        self.cse = cse
        self.enricher = enricher or ThreatEnrichmentEngine()

    def get_findings(self) -> List[Finding]:
        query = self.db.query(Finding).filter(Finding.analysis_run_id == self.run.id)
        if self.cse:
            query = query.filter(Finding.cse_id == self.cse.id)
        return query.order_by(Finding.supervisory_priority.desc()).all()

    def get_risk_scores(self) -> List[RiskScore]:
        query = self.db.query(RiskScore).filter(RiskScore.analysis_run_id == self.run.id)
        if self.cse:
            query = query.filter(RiskScore.cse_id == self.cse.id)
        return query.all()

    def get_assets(self) -> List[Asset]:
        if self.cse:
            return self.db.query(Asset).filter(Asset.cse_id == self.cse.id).all()
        return self.db.query(Asset).all()

    def get_severity_distribution(self, findings: List[Finding]) -> Dict[str, int]:
        dist = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for f in findings:
            sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
            if sev in dist:
                dist[sev] += 1
            else:
                dist["MEDIUM"] += 1
        return dist

    def calculate_security_posture(self, overall_risk_score: float, critical_findings_count: int) -> str:
        if critical_findings_count >= 5 or overall_risk_score >= 80.0:
            return "CRITICAL"
        elif critical_findings_count >= 2 or overall_risk_score >= 60.0:
            return "HIGH"
        elif critical_findings_count >= 1 or overall_risk_score >= 40.0:
            return "ELEVATED"
        elif overall_risk_score >= 20.0:
            return "MODERATE"
        return "NOMINAL"

    def extract_evidence_references(self, findings: List[Finding]) -> List[Dict[str, Any]]:
        refs = []
        for f in findings:
            for ev in f.evidence_records:
                refs.append({
                    "finding_id": str(f.id),
                    "evidence_id": str(ev.id),
                    "evidence_type": ev.evidence_type,
                    "source_table": ev.source_table,
                    "source_record_id": ev.source_record_id,
                    "relevance": ev.relevance,
                    "description": ev.description,
                    "provenance": ev.provenance_json or {}
                })
        return refs
