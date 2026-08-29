import hashlib
import json
from typing import Dict, List, Any
from sqlalchemy.orm import Session

from app.models import Finding, RiskScore, ReviewQueueItem, CSE, Asset, Alert
from app.analytics.graph_engine import SupervisoryEvidenceGraphEngine


class DeterministicStateHasher:
    """Computes deterministic SHA-256 state hashes across analytical outputs, ignoring nondeterministic UUIDs and timestamps."""

    @staticmethod
    def extract_normalized_state(db: Session, analysis_run_id: str) -> Dict[str, Any]:
        # 1. Normalized Findings
        findings = db.query(Finding).filter(Finding.analysis_run_id == analysis_run_id).all()
        normalized_findings = []
        for f in findings:
            cse = db.query(CSE).filter(CSE.id == f.cse_id).first()
            asset = db.query(Asset).filter(Asset.id == f.asset_id).first() if f.asset_id else None
            
            # Normalize evidence refs by stripping volatile UUIDs
            norm_refs = []
            for ref in (f.evidence_refs or []):
                norm_refs.append({
                    "evidence_type": ref.get("evidence_type", ""),
                    "source_entity_type": ref.get("source_entity_type", ref.get("source_table", "")),
                    "summary": ref.get("summary", ""),
                    "relevance": ref.get("relevance", 1.0)
                })
            norm_refs.sort(key=lambda r: (r["evidence_type"], r["source_entity_type"], r["summary"]))

            normalized_findings.append({
                "rule_id": f.rule_id or "",
                "rule_version": f.rule_version or "1.0.0",
                "cse_name": cse.name if cse else "UNKNOWN_CSE",
                "asset_name": asset.name if asset else "NONE",
                "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                "confidence": round(float(f.confidence or 1.0), 2),
                "reason": str(f.reason or "").strip(),
                "expected_behaviour": str(f.expected_behaviour or "").strip(),
                "observed_behaviour": str(f.observed_behaviour or "").strip(),
                "recommendation": str(f.recommendation or "").strip(),
                "evidence_refs": norm_refs
            })
        normalized_findings.sort(key=lambda x: (x["rule_id"], x["cse_name"], x["asset_name"], x["reason"]))

        # 2. Normalized Risk Scores
        risk_scores = db.query(RiskScore).filter(RiskScore.analysis_run_id == analysis_run_id).all()
        normalized_risk = []
        for r in risk_scores:
            cse = db.query(CSE).filter(CSE.id == r.cse_id).first()
            normalized_risk.append({
                "cse_name": cse.name if cse else "UNKNOWN_CSE",
                "normalized_score": round(float(r.normalized_score or 0.0), 2),
                "risk_band": str(r.risk_band or "LOW"),
                "overall_confidence": round(float(r.overall_confidence or 1.0), 2),
                "component_scores": {
                    k: round(float(v), 2) for k, v in (r.component_scores or {}).items()
                }
            })
        normalized_risk.sort(key=lambda x: x["cse_name"])

        # 3. Normalized Review Queue
        queue_items = db.query(ReviewQueueItem).filter(ReviewQueueItem.analysis_run_id == analysis_run_id).order_by(ReviewQueueItem.rank.asc()).all()
        normalized_queue = []
        for item in queue_items:
            cse = db.query(CSE).filter(CSE.id == item.cse_id).first()
            finding = db.query(Finding).filter(Finding.id == item.finding_id).first()
            normalized_queue.append({
                "rank": item.rank,
                "cse_name": cse.name if cse else "UNKNOWN_CSE",
                "rule_id": finding.rule_id if finding else "",
                "finding_severity": item.finding_severity or "",
                "priority_band": item.priority_band or "",
                "candidate_score": round(float(item.candidate_score or 0.0), 2)
            })

        # 4. Normalized Graph Metrics
        import uuid as _uuid
        run_uuid = _uuid.UUID(analysis_run_id) if isinstance(analysis_run_id, str) else analysis_run_id
        G = SupervisoryEvidenceGraphEngine.build_graph_for_analysis_run(db, run_uuid)
        metrics = SupervisoryEvidenceGraphEngine.calculate_graph_metrics(G)
        anomalies = SupervisoryEvidenceGraphEngine.detect_graph_anomalies(db, G, run_uuid)

        norm_anomalies = sorted([
            {"anomaly_type": a.get("anomaly_type", ""), "severity": a.get("severity", "")}
            for a in anomalies
        ], key=lambda a: (a["anomaly_type"], a["severity"]))

        normalized_graph = {
            "node_count": metrics.get("node_count", 0),
            "edge_count": metrics.get("edge_count", 0),
            "anomaly_count": len(anomalies),
            "anomalies": norm_anomalies
        }

        return {
            "findings_count": len(normalized_findings),
            "findings": normalized_findings,
            "risk_scores_count": len(normalized_risk),
            "risk_scores": normalized_risk,
            "queue_count": len(normalized_queue),
            "queue": normalized_queue,
            "graph": normalized_graph
        }

    @classmethod
    def compute_state_hash(cls, db: Session, analysis_run_id: str) -> str:
        state = cls.extract_normalized_state(db, analysis_run_id)
        canonical_json = json.dumps(state, sort_keys=True, indent=2)
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
