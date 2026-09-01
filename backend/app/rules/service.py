import time
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session, joinedload

from app.core.database import SessionLocal
from app.models import (
    AnalysisRun, Finding, Evidence, RuleVersion, AnalysisRunStatus,
    FindingStatus, Alert, Investigation, MaintenanceLog, Asset, CSE, DatasetImport
)
from app.evidence.reconstructor import WorkflowReconstructor
from app.evidence.assembler import EvidenceAssembler
from app.rules.baseline import BaselineRuleEvaluators
from app.rules.negative_space import NegativeSpaceEvaluators
from app.rules.matrix import ExpectedEvidenceMatrix
from app.rules.evaluator import EvaluationStatus, RuleEvaluationResult
from app.core.logging import logger


class ExecutionGapEngine:
    """Independent supervisory intelligence service detecting process execution gaps from canonical records."""

    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()

    def run_analysis(self, dataset_import_id: uuid.UUID, rule_version: str = "1.0.0", analysis_run_id: Optional[uuid.UUID] = None) -> AnalysisRun:
        """Run execution gap detection over canonical database records for a DatasetImport."""
        start_time = time.time()

        # 1. Fetch DatasetImport & Completeness Score
        ds_import = self.db.query(DatasetImport).filter(DatasetImport.id == dataset_import_id).first()
        completeness_score = ds_import.completeness_score if ds_import else 100.0

        # 2. Create or Fetch AnalysisRun Provenance Record
        if analysis_run_id:
            analysis_run = self.db.query(AnalysisRun).filter(AnalysisRun.id == analysis_run_id).first()
        else:
            analysis_run = None

        if not analysis_run:
            analysis_run = AnalysisRun(
                id=analysis_run_id or uuid.uuid4(),
                dataset_import_id=dataset_import_id,
                started_at=datetime.now(timezone.utc),
                status=AnalysisRunStatus.RUNNING,
                rule_version=rule_version,
                model_version="1.0.0",
                records_processed=0,
                findings_generated=0,
                configuration={"engine": "ExecutionGapEngine", "rule_version": rule_version}
            )
            self.db.add(analysis_run)
            self.db.commit()

        try:
            # 3. Fetch Canonical Alerts using joinedload to eliminate N+1 queries
            self.db.query(Finding).filter(
                Finding.analysis_run_id == analysis_run.id,
                Finding.rule_id.like("GAP-%")
            ).delete()
            self.db.commit()

            alerts = self.db.query(Alert).options(
                joinedload(Alert.asset),
                joinedload(Alert.cse),
                joinedload(Alert.investigation).joinedload(Investigation.escalation)
            ).all()


            workflow_nodes = WorkflowReconstructor.reconstruct_for_alerts(alerts)

            eval_results: List[RuleEvaluationResult] = []
            findings_created: List[Finding] = []

            # 4. Evaluate Baseline Rules against canonical workflow nodes
            for node in workflow_nodes:
                res_gap01 = BaselineRuleEvaluators.evaluate_gap01(node, completeness_score=completeness_score)
                res_gap03 = BaselineRuleEvaluators.evaluate_gap03(node, completeness_score=completeness_score)

                for res in [res_gap01, res_gap03]:
                    eval_results.append(res)
                    
                    # Only confirmed execution gaps (FAIL or CONFIRMED status) create Finding records!
                    if res.status in (EvaluationStatus.FAIL, EvaluationStatus.CONFIRMED):
                        finding = Finding(
                            id=uuid.uuid4(),
                            analysis_run_id=analysis_run.id,
                            rule_id=res.rule_id,
                            rule_version=res.rule_version,
                            cse_id=node.alert.cse_id,
                            asset_id=node.alert.asset_id,
                            case_id=node.case.id if node.case else None,
                            severity=res.severity,
                            anomaly_score=0.0,
                            confidence=res.confidence,
                            risk_score=res.risk_contribution,
                            supervisory_priority=round(res.risk_contribution * res.confidence, 2),
                            reason=res.explanation,
                            expected_behaviour=res.expected_behaviour,
                            observed_behaviour=res.observed_behaviour,
                            evidence_refs=res.evidence_refs,
                            recommendation=res.recommendation,
                            status=FindingStatus.NEW
                        )
                        self.db.add(finding)
                        EvidenceAssembler.assemble_execution_gap_evidence(
                            db=self.db,
                            finding=finding,
                            workflow_node=node,
                            analysis_run=analysis_run,
                            completeness_score=completeness_score
                        )
                        findings_created.append(finding)

            duration = round(time.time() - start_time, 3)

            # 5. Finalize AnalysisRun Record
            analysis_run.ended_at = datetime.now(timezone.utc)
            analysis_run.status = AnalysisRunStatus.COMPLETED
            analysis_run.records_processed = len(alerts)
            analysis_run.findings_generated = len(findings_created)
            analysis_run.processing_duration_seconds = duration

            self.db.commit()
            logger.info(f"ExecutionGapEngine run completed for import {dataset_import_id}: processed {len(alerts)} alerts, generated {len(findings_created)} findings in {duration}s")
            return analysis_run

        except Exception as e:
            self.db.rollback()
            analysis_run.status = AnalysisRunStatus.FAILED
            self.db.commit()
            logger.error(f"ExecutionGapEngine run failed: {str(e)}")
            raise e


class NegativeSpaceEngine:
    """Supervisory intelligence engine evaluating missing expected evidence (Negative Space) across canonical DB records."""

    def __init__(self, db: Session = None, matrix: Optional[ExpectedEvidenceMatrix] = None):
        self.db = db or SessionLocal()
        self.matrix = matrix or ExpectedEvidenceMatrix()

    def run_analysis(self, dataset_import_id: uuid.UUID, rule_version: str = "1.0.0", analysis_run_id: Optional[uuid.UUID] = None) -> AnalysisRun:
        """Run negative space evaluation rules (NEG-01 through NEG-05) against canonical database records."""
        start_time = time.time()

        # 1. Fetch DatasetImport & Completeness Score
        ds_import = self.db.query(DatasetImport).filter(DatasetImport.id == dataset_import_id).first()
        completeness_score = ds_import.completeness_score if ds_import else 100.0

        # 2. Create or Fetch AnalysisRun Provenance Record
        if analysis_run_id:
            analysis_run = self.db.query(AnalysisRun).filter(AnalysisRun.id == analysis_run_id).first()
        else:
            analysis_run = None

        if not analysis_run:
            analysis_run = AnalysisRun(
                id=analysis_run_id or uuid.uuid4(),
                dataset_import_id=dataset_import_id,
                started_at=datetime.now(timezone.utc),
                status=AnalysisRunStatus.RUNNING,
                rule_version=rule_version,
                model_version="1.0.0",
                records_processed=0,
                findings_generated=0,
                configuration={"engine": "NegativeSpaceEngine", "rule_version": rule_version}
            )
            self.db.add(analysis_run)
            self.db.commit()

        try:
            # 3. Fetch Canonical Entities from DB
            self.db.query(Finding).filter(
                Finding.analysis_run_id == analysis_run.id,
                Finding.rule_id.like("NEG-%")
            ).delete()
            self.db.commit()

            alerts = self.db.query(Alert).all()
            assets = self.db.query(Asset).all()

            asset_map = {asset.id: asset for asset in assets}
            cses = self.db.query(CSE).all()
            cse_map = {cse.id: cse for cse in cses}
            maint_logs = self.db.query(MaintenanceLog).all()

            eval_results: List[RuleEvaluationResult] = []
            findings_created: List[Finding] = []

            from collections import defaultdict
            alerts_by_asset = defaultdict(list)
            alerts_by_cse = defaultdict(list)
            alert_counts_by_asset: Dict[str, int] = defaultdict(int)
            for a in alerts:
                alerts_by_asset[a.asset_id].append(a)
                alert_counts_by_asset[str(a.asset_id)] += 1
                alerts_by_cse[a.cse_id].append(a)

            # 4. Evaluate Asset-Level Rules (NEG-01, NEG-04, NEG-05)
            for asset in assets:
                asset_recent_alerts = alerts_by_asset.get(asset.id, [])
                res_neg01 = NegativeSpaceEvaluators.evaluate_neg01_missing_telemetry(
                    asset=asset,
                    recent_alerts=asset_recent_alerts,
                    maintenance_logs=[m for m in maint_logs if str(m.asset_id) == str(asset.id)],
                    matrix=self.matrix,
                    completeness_score=completeness_score
                )
                res_neg04 = NegativeSpaceEvaluators.evaluate_neg04_under_monitored_asset(
                    target_asset=asset,
                    all_assets=assets,
                    all_alerts=alerts,
                    completeness_score=completeness_score,
                    alert_counts_by_asset=alert_counts_by_asset
                )
                res_neg05 = NegativeSpaceEvaluators.evaluate_neg05_unexplained_maintenance_silence(
                    asset=asset,
                    recent_alerts=asset_recent_alerts,
                    maintenance_logs=maint_logs,
                    completeness_score=completeness_score
                )

                eval_results.extend([res_neg01, res_neg04, res_neg05])

            # 5. Evaluate CSE-Level Rules (NEG-02, NEG-03)
            for cse in cses:
                cse_alerts = alerts_by_cse.get(cse.id, [])
                res_neg02 = NegativeSpaceEvaluators.evaluate_neg02_telemetry_drop(
                    cse=cse,
                    alerts=cse_alerts,
                    maintenance_logs=[m for m in maint_logs if str(m.cse_id) == str(cse.id)],
                    completeness_score=completeness_score
                )
                eval_results.append(res_neg02)

                expected_categories = self.matrix.get_expected_categories_for_cse(cse)
                for cat in expected_categories:
                    res_neg03 = NegativeSpaceEvaluators.evaluate_neg03_missing_category(
                        cse=cse,
                        alerts=cse_alerts,
                        expected_category=cat,
                        matrix=self.matrix,
                        completeness_score=completeness_score
                    )
                    eval_results.append(res_neg03)


            # 6. Generate Findings ONLY for CONFIRMED evaluation state (or FAIL for backward compatibility)
            for res in eval_results:
                if res.status in (EvaluationStatus.CONFIRMED, EvaluationStatus.FAIL):
                    cse_id = None
                    asset_id = None

                    if res.target_entity_type == "CSE" and res.target_entity_id:
                        cse_id = uuid.UUID(res.target_entity_id)
                    elif res.target_entity_type == "Asset" and res.target_entity_id:
                        asset_id = uuid.UUID(res.target_entity_id)
                        target_asset = asset_map.get(asset_id)
                        if target_asset:
                            cse_id = target_asset.cse_id

                    if cse_id is None:
                        # Fallback if target asset lookup failed
                        cse_id = cses[0].id

                    finding = Finding(
                        id=uuid.uuid4(),
                        analysis_run_id=analysis_run.id,
                        rule_id=res.rule_id,
                        rule_version=res.rule_version,
                        cse_id=cse_id,
                        asset_id=asset_id,
                        severity=res.severity,
                        anomaly_score=0.0,
                        confidence=res.confidence,
                        risk_score=res.risk_contribution,
                        supervisory_priority=round(res.risk_contribution * res.confidence, 2),
                        reason=res.explanation,
                        expected_behaviour=res.expected_behaviour or res.expectation or "",
                        observed_behaviour=res.observed_behaviour or (str(res.observed_activity) if res.observed_activity else ""),
                        evidence_refs=res.evidence_refs,
                        recommendation=res.recommendation,
                        status=FindingStatus.NEW
                    )
                    self.db.add(finding)

                    # Invoke EvidenceAssembler for structured canonical evidence records
                    EvidenceAssembler.assemble_negative_space_evidence(
                        db=self.db,
                        finding=finding,
                        res=res,
                        analysis_run=analysis_run,
                        cse=cse_map.get(cse_id) if cse_id else None,
                        asset=asset_map.get(asset_id) if asset_id else None,
                        maintenance_logs=maint_logs,
                        completeness_score=completeness_score
                    )

                    findings_created.append(finding)

            duration = round(time.time() - start_time, 4)
            records_evaluated = len(alerts)
            assets_evaluated = len(assets)
            cses_evaluated = len(cses)
            windows_evaluated = assets_evaluated * 3 + cses_evaluated * 2
            throughput_records = round(records_evaluated / duration, 2) if duration > 0 else 0.0
            throughput_windows = round(windows_evaluated / duration, 2) if duration > 0 else 0.0

            # 7. Finalize AnalysisRun Provenance and Benchmark Record
            analysis_run.ended_at = datetime.now(timezone.utc)
            analysis_run.status = AnalysisRunStatus.COMPLETED
            analysis_run.records_processed = records_evaluated
            analysis_run.findings_generated = len(findings_created)
            analysis_run.processing_duration_seconds = duration
            analysis_run.configuration = {
                "engine": "NegativeSpaceEngine",
                "rule_version": rule_version,
                "benchmark": {
                    "records_evaluated": records_evaluated,
                    "assets_evaluated": assets_evaluated,
                    "cses_evaluated": cses_evaluated,
                    "windows_evaluated": windows_evaluated,
                    "findings_generated": len(findings_created),
                    "execution_time_seconds": duration,
                    "records_per_second": throughput_records,
                    "windows_per_second": throughput_windows
                }
            }

            self.db.commit()
            logger.info(f"NegativeSpaceEngine completed for import {dataset_import_id}: evaluated {records_evaluated} records, {windows_evaluated} windows across {assets_evaluated} assets, generated {len(findings_created)} findings in {duration}s ({throughput_records} rec/s)")
            return analysis_run

        except Exception as e:
            self.db.rollback()
            analysis_run.status = AnalysisRunStatus.FAILED
            self.db.commit()
            logger.error(f"NegativeSpaceEngine run failed: {str(e)}")
            raise e
