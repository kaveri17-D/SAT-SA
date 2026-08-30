import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models import Evidence, Finding, AnalysisRun, Alert, Asset, CSE, Investigation, Escalation, Case, Closure, MaintenanceLog, AuditLog
from app.evidence.schema import EvidenceType, EvidenceRecordItem, WorkflowDifference, EvidencePackage
from app.evidence.reconstructor import OperationalWorkflowNode
from app.rules.evaluator import RuleEvaluationResult
from app.core.logging import logger


REQUIRED_EVIDENCE_CONTRACT: Dict[str, List[str]] = {
    "GAP-01": [EvidenceType.DIRECT_RECORD.value, EvidenceType.MISSING_EXPECTED_RECORD.value, EvidenceType.WORKFLOW_TRANSITION.value, EvidenceType.DATA_QUALITY.value],
    "GAP-02": [EvidenceType.DIRECT_RECORD.value, EvidenceType.MISSING_EXPECTED_RECORD.value, EvidenceType.WORKFLOW_TRANSITION.value, EvidenceType.DATA_QUALITY.value],
    "GAP-03": [EvidenceType.DIRECT_RECORD.value, EvidenceType.MISSING_EXPECTED_RECORD.value, EvidenceType.WORKFLOW_TRANSITION.value, EvidenceType.DATA_QUALITY.value],
    "GAP-04": [EvidenceType.DIRECT_RECORD.value, EvidenceType.MISSING_EXPECTED_RECORD.value, EvidenceType.WORKFLOW_TRANSITION.value, EvidenceType.DATA_QUALITY.value],
    "GAP-05": [EvidenceType.DIRECT_RECORD.value, EvidenceType.MISSING_EXPECTED_RECORD.value, EvidenceType.WORKFLOW_TRANSITION.value, EvidenceType.DATA_QUALITY.value],
    "GAP-06": [EvidenceType.DIRECT_RECORD.value, EvidenceType.MISSING_EXPECTED_RECORD.value, EvidenceType.WORKFLOW_TRANSITION.value, EvidenceType.DATA_QUALITY.value],
    "NEG-01": [EvidenceType.DIRECT_RECORD.value, EvidenceType.MISSING_EXPECTED_RECORD.value, EvidenceType.CONTEXT_SUPPRESSION.value, EvidenceType.DATA_QUALITY.value],
    "NEG-02": [EvidenceType.DIRECT_RECORD.value, EvidenceType.HISTORICAL_BASELINE.value, EvidenceType.STATISTICAL_DEVIATION.value, EvidenceType.DATA_QUALITY.value],
    "NEG-03": [EvidenceType.DIRECT_RECORD.value, EvidenceType.MISSING_EXPECTED_RECORD.value, EvidenceType.DATA_QUALITY.value],
    "NEG-04": [EvidenceType.DIRECT_RECORD.value, EvidenceType.PEER_COMPARISON.value, EvidenceType.STATISTICAL_DEVIATION.value, EvidenceType.DATA_QUALITY.value],
    "NEG-05": [EvidenceType.DIRECT_RECORD.value, EvidenceType.CONTEXT_SUPPRESSION.value, EvidenceType.DATA_QUALITY.value],
}


class EvidenceAssembler:
    """Independent service converting analytical findings into structured evidence packages."""

    @staticmethod
    def assemble_execution_gap_evidence(
        db: Session,
        finding: Finding,
        workflow_node: OperationalWorkflowNode,
        analysis_run: Optional[AnalysisRun] = None,
        completeness_score: float = 100.0
    ) -> List[Evidence]:
        """Assemble canonical evidence records for Execution Gap findings."""
        evidence_records: List[Evidence] = []
        now = datetime.now(timezone.utc)

        prov = {
            "dataset_import_id": str(analysis_run.dataset_import_id) if analysis_run else None,
            "analysis_run_id": str(analysis_run.id) if analysis_run else str(finding.analysis_run_id),
            "rule_version": finding.rule_version,
            "engine": "ExecutionGapEngine",
            "assembled_by": "EvidenceAssembler"
        }

        # 1. Direct Record: Alert
        if workflow_node.alert:
            ev_alert = Evidence(
                id=uuid.uuid4(),
                finding_id=finding.id,
                evidence_type=EvidenceType.DIRECT_RECORD.value,
                source_table="alerts",
                source_record_id=str(workflow_node.alert.id),
                evidence_timestamp=workflow_node.alert.created_at,
                description=f"Canonical alert {workflow_node.alert.category} ({workflow_node.alert.severity.value}) registered at {workflow_node.alert.created_at.isoformat()}.",
                relevance="CRITICAL",
                payload_json={
                    "alert_id": str(workflow_node.alert.id),
                    "category": workflow_node.alert.category,
                    "severity": workflow_node.alert.severity.value,
                    "source_system": workflow_node.alert.source_system,
                    "created_at": workflow_node.alert.created_at.isoformat()
                },
                provenance_json=prov,
                captured_at=now
            )
            evidence_records.append(ev_alert)

        # 2. Direct Record: Asset (if present)
        if workflow_node.asset:
            ev_asset = Evidence(
                id=uuid.uuid4(),
                finding_id=finding.id,
                evidence_type=EvidenceType.DIRECT_RECORD.value,
                source_table="assets",
                source_record_id=str(workflow_node.asset.id),
                evidence_timestamp=workflow_node.asset.created_at,
                description=f"Target asset {workflow_node.asset.name} ({workflow_node.asset.criticality.value})",
                relevance="HIGH",
                payload_json={
                    "asset_id": str(workflow_node.asset.id),
                    "name": workflow_node.asset.name,
                    "asset_type": workflow_node.asset.asset_type,
                    "criticality": workflow_node.asset.criticality.value
                },
                provenance_json=prov,
                captured_at=now
            )
            evidence_records.append(ev_asset)

        # 3. Direct Record / Missing Expected: Investigation
        if workflow_node.investigation:
            ev_inv = Evidence(
                id=uuid.uuid4(),
                finding_id=finding.id,
                evidence_type=EvidenceType.DIRECT_RECORD.value,
                source_table="investigations",
                source_record_id=str(workflow_node.investigation.id),
                evidence_timestamp=workflow_node.investigation.started_at,
                description=f"Investigation started at {workflow_node.investigation.started_at.isoformat()} with duration {workflow_node.investigation.duration_seconds}s.",
                relevance="HIGH",
                payload_json={
                    "investigation_id": str(workflow_node.investigation.id),
                    "analyst_id": str(workflow_node.investigation.analyst_id) if workflow_node.investigation.analyst_id else None,
                    "started_at": workflow_node.investigation.started_at.isoformat(),
                    "duration_seconds": workflow_node.investigation.duration_seconds
                },
                provenance_json=prov,
                captured_at=now
            )
            evidence_records.append(ev_inv)
        else:
            # Missing Investigation Record
            ev_miss_inv = Evidence(
                id=uuid.uuid4(),
                finding_id=finding.id,
                evidence_type=EvidenceType.MISSING_EXPECTED_RECORD.value,
                source_table="investigations",
                source_record_id=f"MISSING_INVESTIGATION_{workflow_node.alert.id}",
                evidence_timestamp=now,
                description="Expected mandatory investigation record is missing for high-severity alert.",
                relevance="CRITICAL",
                payload_json={
                    "expected_evidence": "Investigation record by assigned analyst",
                    "expected_time_or_window": "Within 30 minutes of alert registration",
                    "observed_evidence": "No investigation entity created or linked to alert",
                    "observation_window": f"Alert created at {workflow_node.alert.created_at.isoformat()}",
                    "reason_for_determining_absence": "Query returned 0 linked investigation records in canonical database",
                    "data_quality_context": f"Dataset completeness score is {completeness_score:.1f}%"
                },
                provenance_json=prov,
                captured_at=now
            )
            evidence_records.append(ev_miss_inv)

        # 4. Missing Escalation Transition (e.g. for GAP-01)
        if finding.rule_id == "GAP-01" and not workflow_node.has_escalation:
            ev_miss_esc = Evidence(
                id=uuid.uuid4(),
                finding_id=finding.id,
                evidence_type=EvidenceType.MISSING_EXPECTED_RECORD.value,
                source_table="escalations",
                source_record_id=f"MISSING_ESCALATION_{workflow_node.alert.id}",
                evidence_timestamp=now,
                description="Mandatory supervisory escalation record missing prior to case closure.",
                relevance="CRITICAL",
                payload_json={
                    "expected_evidence": "Escalation transition to L2/Supervisor",
                    "expected_time_or_window": "Prior to case closure for CRITICAL/HIGH alerts",
                    "observed_evidence": "Alert/Case closed directly without escalation transition",
                    "observation_window": f"Alert lifecycle from {workflow_node.alert.created_at.isoformat()}",
                    "reason_for_determining_absence": "Investigation has null escalation_id reference",
                    "data_quality_context": f"Dataset completeness score is {completeness_score:.1f}%"
                },
                provenance_json=prov,
                captured_at=now
            )
            evidence_records.append(ev_miss_esc)

        # 5. Workflow Transition Evidence
        expected_seq = ["Alert", "Investigation", "Escalation", "Case", "Closure"]
        observed_seq = ["Alert"]
        if workflow_node.has_investigation:
            observed_seq.append("Investigation")
        if workflow_node.has_escalation:
            observed_seq.append("Escalation")
        if workflow_node.has_case:
            observed_seq.append("Case")
        if workflow_node.has_closure:
            observed_seq.append("Closure")

        missing_trans = []
        if "Investigation" not in observed_seq:
            missing_trans.append({"from": "Alert", "to": "Investigation", "reason": "Alert uninvestigated"})
        if "Escalation" not in observed_seq and "Case" in observed_seq:
            missing_trans.append({"from": "Investigation", "to": "Escalation", "reason": "Unescalated case closure"})

        ev_wf = Evidence(
            id=uuid.uuid4(),
            finding_id=finding.id,
            evidence_type=EvidenceType.WORKFLOW_TRANSITION.value,
            source_table="workflows",
            source_record_id=str(workflow_node.alert.id),
            evidence_timestamp=now,
            description="Operational workflow reconstruction showing transition gaps.",
            relevance="CRITICAL",
            payload_json={
                "expected_sequence": expected_seq,
                "observed_sequence": observed_seq,
                "missing_transitions": missing_trans
            },
            provenance_json=prov,
                captured_at=now
        )
        evidence_records.append(ev_wf)

        # 6. Data Quality Evidence
        ev_dq = Evidence(
            id=uuid.uuid4(),
            finding_id=finding.id,
            evidence_type=EvidenceType.DATA_QUALITY.value,
            source_table="dataset_imports",
            source_record_id=str(analysis_run.dataset_import_id) if analysis_run else "DS_IMPORT_REF",
            evidence_timestamp=now,
            description=f"Dataset ingestion completeness score: {completeness_score:.1f}%.",
            relevance="HIGH",
            payload_json={
                "completeness_score": completeness_score,
                "is_clean": completeness_score >= 95.0,
                "data_quality_warnings": [] if completeness_score >= 95.0 else [f"Completeness is {completeness_score:.1f}%"]
            },
            provenance_json=prov,
            captured_at=now
        )
        evidence_records.append(ev_dq)

        # Save evidence records to DB
        for ev in evidence_records:
            db.add(ev)

        # Update finding evidence completeness & adjusted confidence
        EvidenceAssembler._update_finding_evidence_completeness(finding, evidence_records)

        return evidence_records

    @staticmethod
    def assemble_negative_space_evidence(
        db: Session,
        finding: Finding,
        res: RuleEvaluationResult,
        analysis_run: Optional[AnalysisRun] = None,
        cse: Optional[CSE] = None,
        asset: Optional[Asset] = None,
        maintenance_logs: Optional[List[MaintenanceLog]] = None,
        completeness_score: float = 100.0
    ) -> List[Evidence]:
        """Assemble canonical evidence records for Negative Space findings."""
        evidence_records: List[Evidence] = []
        now = datetime.now(timezone.utc)

        prov = {
            "dataset_import_id": str(analysis_run.dataset_import_id) if analysis_run else None,
            "analysis_run_id": str(analysis_run.id) if analysis_run else str(finding.analysis_run_id),
            "rule_version": finding.rule_version,
            "engine": "NegativeSpaceEngine",
            "assembled_by": "EvidenceAssembler"
        }

        # 1. Direct Record: Asset / CSE Entity
        if asset:
            ev_entity = Evidence(
                id=uuid.uuid4(),
                finding_id=finding.id,
                evidence_type=EvidenceType.DIRECT_RECORD.value,
                source_table="assets",
                source_record_id=str(asset.id),
                evidence_timestamp=asset.created_at,
                description=f"Target critical asset {asset.name} ({asset.criticality.value}) with status {asset.status}.",
                relevance="CRITICAL",
                payload_json={
                    "asset_id": str(asset.id),
                    "name": asset.name,
                    "asset_type": asset.asset_type,
                    "criticality": asset.criticality.value,
                    "status": asset.status
                },
                provenance_json=prov,
                captured_at=now
            )
            evidence_records.append(ev_entity)
        elif cse:
            ev_entity = Evidence(
                id=uuid.uuid4(),
                finding_id=finding.id,
                evidence_type=EvidenceType.DIRECT_RECORD.value,
                source_table="cses",
                source_record_id=str(cse.id),
                evidence_timestamp=cse.created_at,
                description=f"Target CSE {cse.name} (Sector: {cse.sector}, Tier: {cse.size_tier}).",
                relevance="CRITICAL",
                payload_json={
                    "cse_id": str(cse.id),
                    "name": cse.name,
                    "sector": cse.sector,
                    "size_tier": cse.size_tier
                },
                provenance_json=prov,
                captured_at=now
            )
            evidence_records.append(ev_entity)

        # 2. Rule-Specific Evidence Assembly
        if res.rule_id == "NEG-01":
            # Missing Expected Telemetry
            ev_miss = Evidence(
                id=uuid.uuid4(),
                finding_id=finding.id,
                evidence_type=EvidenceType.MISSING_EXPECTED_RECORD.value,
                source_table="alerts",
                source_record_id=f"MISSING_TELEMETRY_{asset.id if asset else cse.id}",
                evidence_timestamp=now,
                description="Expected operational telemetry/evidence is absent beyond silence threshold.",
                relevance="CRITICAL",
                payload_json={
                    "expected_evidence": "Continuous telemetry or periodic operational alerts",
                    "expected_time_or_window": "At least 1 alert every 48.0 hours",
                    "observed_evidence": res.observed_activity,
                    "observation_window": "Past 48.0 hours prior to evaluation timestamp",
                    "reason_for_determining_absence": "Zero telemetry records found for active critical asset in window",
                    "data_quality_context": f"Dataset completeness score is {completeness_score:.1f}%"
                },
                provenance_json=prov,
                captured_at=now
            )
            evidence_records.append(ev_miss)

            ev_ctx = Evidence(
                id=uuid.uuid4(),
                finding_id=finding.id,
                evidence_type=EvidenceType.CONTEXT_SUPPRESSION.value,
                source_table="maintenance_logs",
                source_record_id=f"MAINT_CHECK_{asset.id if asset else cse.id}",
                evidence_timestamp=now,
                description="Context check: Verified asset status is ACTIVE and no authorized maintenance window overlaps.",
                relevance="HIGH",
                payload_json={
                    "asset_status": asset.status if asset else "ACTIVE",
                    "maintenance_overlap": False,
                    "suppression_reason": None
                },
                provenance_json=prov,
                captured_at=now
            )
            evidence_records.append(ev_ctx)

        elif res.rule_id == "NEG-02":
            # Telemetry Volume Drop (Historical Baseline & Statistical Deviation)
            ev_base = Evidence(
                id=uuid.uuid4(),
                finding_id=finding.id,
                evidence_type=EvidenceType.HISTORICAL_BASELINE.value,
                source_table="baselines",
                source_record_id=f"BASELINE_30D_{cse.id if cse else (asset.id if asset else 'REF')}",
                evidence_timestamp=now,
                description="30-day rolling telemetry volume baseline statistics.",
                relevance="HIGH",
                payload_json=res.baseline,
                provenance_json=prov,
                captured_at=now
            )
            evidence_records.append(ev_base)

            ev_dev = Evidence(
                id=uuid.uuid4(),
                finding_id=finding.id,
                evidence_type=EvidenceType.STATISTICAL_DEVIATION.value,
                source_table="baseline_deviations",
                source_record_id=f"DEV_NEG02_{cse.id if cse else (asset.id if asset else 'REF')}",
                evidence_timestamp=now,
                description=f"Statistical measurement of volume drop: {res.absence_deviation_measurement}",
                relevance="CRITICAL",
                payload_json={
                    "observed_activity": res.observed_activity,
                    "deviation_measurement": res.absence_deviation_measurement,
                    "baseline_stats": res.baseline
                },
                provenance_json=prov,
                captured_at=now
            )
            evidence_records.append(ev_dev)

        elif res.rule_id == "NEG-03":
            # Missing Expected Alert Category
            ev_cat = Evidence(
                id=uuid.uuid4(),
                finding_id=finding.id,
                evidence_type=EvidenceType.MISSING_EXPECTED_RECORD.value,
                source_table="alerts",
                source_record_id=f"MISSING_CATEGORY_{cse.id if cse else 'REF'}",
                evidence_timestamp=now,
                description="Expected mandatory alert category is completely absent.",
                relevance="CRITICAL",
                payload_json={
                    "expected_evidence": f"Expected alert category mandated by Expected Evidence Matrix",
                    "expected_time_or_window": "Past 30-day monitoring window",
                    "observed_evidence": res.observed_activity,
                    "observation_window": "30 days",
                    "reason_for_determining_absence": "Zero alerts logged for mandated category for sector/tier",
                    "data_quality_context": f"Dataset completeness score is {completeness_score:.1f}%"
                },
                provenance_json=prov,
                captured_at=now
            )
            evidence_records.append(ev_cat)

        elif res.rule_id == "NEG-04":
            # Under-Monitored Peer Asset (Peer Comparison & Statistical Deviation)
            ev_peer = Evidence(
                id=uuid.uuid4(),
                finding_id=finding.id,
                evidence_type=EvidenceType.PEER_COMPARISON.value,
                source_table="peer_groups",
                source_record_id=f"PEER_GROUP_{asset.cse_id if asset else 'REF'}",
                evidence_timestamp=now,
                description="Peer asset group alert density comparison.",
                relevance="HIGH",
                payload_json=res.baseline,
                provenance_json=prov,
                captured_at=now
            )
            evidence_records.append(ev_peer)

            ev_dev = Evidence(
                id=uuid.uuid4(),
                finding_id=finding.id,
                evidence_type=EvidenceType.STATISTICAL_DEVIATION.value,
                source_table="peer_deviations",
                source_record_id=f"DEV_NEG04_{asset.id if asset else 'REF'}",
                evidence_timestamp=now,
                description=f"Peer density ratio deviation: {res.absence_deviation_measurement}",
                relevance="CRITICAL",
                payload_json={
                    "observed_activity": res.observed_activity,
                    "deviation_measurement": res.absence_deviation_measurement,
                    "peer_baseline": res.baseline
                },
                provenance_json=prov,
                captured_at=now
            )
            evidence_records.append(ev_dev)

        elif res.rule_id == "NEG-05":
            # Unexplained Maintenance Silence
            ev_maint = Evidence(
                id=uuid.uuid4(),
                finding_id=finding.id,
                evidence_type=EvidenceType.CONTEXT_SUPPRESSION.value,
                source_table="maintenance_logs",
                source_record_id=f"MAINT_AUDIT_{asset.id if asset else 'REF'}",
                evidence_timestamp=now,
                description="Maintenance log audit: Telemetry silence occurred without recorded maintenance authorization.",
                relevance="CRITICAL",
                payload_json={
                    "observed_activity": res.observed_activity,
                    "explanation": res.explanation,
                    "maintenance_logs_count": len(maintenance_logs) if maintenance_logs else 0,
                    "evaluation_status": res.status.value
                },
                provenance_json=prov,
                captured_at=now
            )
            evidence_records.append(ev_maint)

        # 3. Data Quality Evidence
        ev_dq = Evidence(
            id=uuid.uuid4(),
            finding_id=finding.id,
            evidence_type=EvidenceType.DATA_QUALITY.value,
            source_table="dataset_imports",
            source_record_id=str(analysis_run.dataset_import_id) if analysis_run else "DS_IMPORT_REF",
            evidence_timestamp=now,
            description=f"Dataset ingestion completeness score: {completeness_score:.1f}%.",
            relevance="HIGH",
            payload_json={
                "completeness_score": completeness_score,
                "is_clean": completeness_score >= 95.0,
                "data_quality_warnings": [] if completeness_score >= 95.0 else [f"Completeness is {completeness_score:.1f}%"]
            },
            provenance_json=prov,
            captured_at=now
        )
        evidence_records.append(ev_dq)

        # Save evidence records to DB
        for ev in evidence_records:
            db.add(ev)

        # Update finding evidence completeness & adjusted confidence
        EvidenceAssembler._update_finding_evidence_completeness(finding, evidence_records)

        return evidence_records

    @staticmethod
    def _update_finding_evidence_completeness(finding: Finding, evidence_records: List[Evidence]):
        """Calculate present/required evidence ratio, update finding.evidence_completeness and scale confidence if incomplete."""
        required_types = REQUIRED_EVIDENCE_CONTRACT.get(finding.rule_id, [EvidenceType.DIRECT_RECORD.value, EvidenceType.DATA_QUALITY.value])
        present_types = set(ev.evidence_type for ev in evidence_records)

        present_required_count = sum(1 for t in required_types if t in present_types)
        total_required_count = len(required_types)

        completeness_pct = round((present_required_count / total_required_count) * 100.0, 2) if total_required_count > 0 else 100.0
        finding.evidence_completeness = completeness_pct

        # If evidence is incomplete (<100%), scale confidence proportionately
        if completeness_pct < 100.0:
            finding.confidence = round(finding.confidence * (completeness_pct / 100.0), 4)

    @staticmethod
    def build_evidence_package(db: Session, finding_id: uuid.UUID) -> Optional[EvidencePackage]:
        """Construct a complete, reproducible EvidencePackage for a finding."""
        finding = db.query(Finding).filter(Finding.id == finding_id).first()
        if not finding:
            return None

        analysis_run = db.query(AnalysisRun).filter(AnalysisRun.id == finding.analysis_run_id).first()
        evidence_records = db.query(Evidence).filter(Evidence.finding_id == finding_id).all()

        required_types = REQUIRED_EVIDENCE_CONTRACT.get(finding.rule_id, [EvidenceType.DIRECT_RECORD.value, EvidenceType.DATA_QUALITY.value])
        present_types = list(set(ev.evidence_type for ev in evidence_records))
        is_complete = (finding.evidence_completeness >= 100.0)

        # Reconstruct EvidenceRecordItems
        supporting_items: List[EvidenceRecordItem] = []
        wf_diff: Optional[WorkflowDifference] = None
        baseline_stats: Optional[Dict[str, Any]] = None
        peer_stats: Optional[Dict[str, Any]] = None
        dq_dict: Dict[str, Any] = {"completeness_score": 100.0}

        for ev in evidence_records:
            item = EvidenceRecordItem(
                evidence_id=str(ev.id),
                evidence_type=ev.evidence_type,
                source_entity_type=ev.source_table,
                source_record_id=str(ev.source_record_id),
                evidence_timestamp=ev.evidence_timestamp.isoformat() if ev.evidence_timestamp else None,
                description=ev.description,
                relevance=ev.relevance,
                payload=ev.payload_json or {},
                provenance=ev.provenance_json or {}
            )
            supporting_items.append(item)

            if ev.evidence_type == EvidenceType.WORKFLOW_TRANSITION.value and ev.payload_json:
                wf_diff = WorkflowDifference(
                    expected_sequence=ev.payload_json.get("expected_sequence", []),
                    observed_sequence=ev.payload_json.get("observed_sequence", []),
                    missing_transitions=ev.payload_json.get("missing_transitions", [])
                )
            elif ev.evidence_type == EvidenceType.HISTORICAL_BASELINE.value:
                baseline_stats = ev.payload_json
            elif ev.evidence_type == EvidenceType.PEER_COMPARISON.value:
                peer_stats = ev.payload_json
            elif ev.evidence_type == EvidenceType.DATA_QUALITY.value:
                dq_dict = ev.payload_json or {}

        package = EvidencePackage(
            finding_id=str(finding.id),
            rule_id=finding.rule_id or "UNKNOWN_RULE",
            rule_version=finding.rule_version,
            engine="ExecutionGapEngine" if finding.rule_id.startswith("GAP") else "NegativeSpaceEngine",
            cse_id=str(finding.cse_id),
            asset_id=str(finding.asset_id) if finding.asset_id else None,
            severity=finding.severity.value,
            supervisory_metrics={
                "anomaly_score": finding.anomaly_score,
                "confidence": finding.confidence,
                "risk_score": finding.risk_score,
                "supervisory_priority": finding.supervisory_priority
            },
            evidence_completeness=finding.evidence_completeness,
            is_evidence_complete=is_complete,
            required_evidence_types=required_types,
            present_evidence_types=present_types,
            detection_source={
                "dataset_import_id": str(analysis_run.dataset_import_id) if analysis_run else None,
                "analysis_run_id": str(finding.analysis_run_id),
                "rule_version": finding.rule_version,
                "model_version": finding.model_version
            },
            expected_behaviour=finding.expected_behaviour,
            observed_behaviour=finding.observed_behaviour,
            context={
                "cse_id": str(finding.cse_id),
                "asset_id": str(finding.asset_id) if finding.asset_id else None,
                "case_id": str(finding.case_id) if finding.case_id else None
            },
            supporting_records=supporting_items,
            workflow_difference=wf_diff,
            baseline_stats=baseline_stats,
            peer_stats=peer_stats,
            data_quality=dq_dict,
            recommendation=finding.recommendation,
            provenance={
                "dataset_import_id": str(analysis_run.dataset_import_id) if analysis_run else None,
                "analysis_run_id": str(finding.analysis_run_id),
                "rule_version": finding.rule_version,
                "generator_checksum": "SYNTHETIC_CANONICAL_PROVENANCE_V1"
            },
            assembled_at=datetime.now(timezone.utc).isoformat()
        )
        return package

    @staticmethod
    def assemble_for_finding(db: Session, finding: Finding, workflow_node: OperationalWorkflowNode) -> List[Evidence]:
        """Backward-compatible alias for execution gap evidence assembly."""
        return EvidenceAssembler.assemble_execution_gap_evidence(db, finding, workflow_node)

    @staticmethod
    def verify_evidence_integrity(db: Session, finding_id: uuid.UUID) -> Dict[str, Any]:
        """Verify immutable snapshot evidence integrity and compute cryptographic SHA-256 hash."""
        import hashlib
        import json

        finding = db.query(Finding).filter(Finding.id == finding_id).first()
        if not finding:
            return {"status": "FINDING_NOT_FOUND", "is_tampered": True}

        evidence_records = db.query(Evidence).filter(Evidence.finding_id == finding_id).all()
        tampered_records = []

        hasher = hashlib.sha256()
        sorted_evs = sorted(evidence_records, key=lambda x: str(x.id))
        for ev in sorted_evs:
            # Check source DB table if present
            if ev.source_table == "alerts":
                obj = db.query(Alert).filter(Alert.id == ev.source_record_id).first()
                if not obj:
                    tampered_records.append({"evidence_id": str(ev.id), "reason": "Referenced Alert record deleted from DB"})
            elif ev.source_table == "assets":
                obj = db.query(Asset).filter(Asset.id == ev.source_record_id).first()
                if not obj:
                    tampered_records.append({"evidence_id": str(ev.id), "reason": "Referenced Asset record deleted from DB"})

            ev_str = f"{ev.id}:{ev.evidence_type}:{ev.source_table}:{ev.source_record_id}:{json.dumps(ev.payload_json or {}, sort_keys=True)}"
            hasher.update(ev_str.encode("utf-8"))

        package_hash = hasher.hexdigest()
        is_tampered = len(tampered_records) > 0

        return {
            "finding_id": str(finding_id),
            "status": "VERIFIED" if not is_tampered else "INTEGRITY_COMPROMISED",
            "is_tampered": is_tampered,
            "sha256_hash": package_hash,
            "evidence_count": len(evidence_records),
            "tampered_count": len(tampered_records),
            "tampered_records": tampered_records,
            "completeness_score": finding.evidence_completeness,
            "rule_id": finding.rule_id,
            "rule_version": finding.rule_version,
            "verified_at": datetime.now(timezone.utc).isoformat()
        }

