import time
import uuid
import psutil
import os
import tracemalloc
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import AnalysisRun, Finding, Evidence, RiskScore, ReviewQueueItem, Alert, CSE, Asset, FindingSeverity, FindingStatus
from app.ingestion.generator.engine import SyntheticDatasetGenerator, GeneratorConfig
from app.rules.service import ExecutionGapEngine, NegativeSpaceEngine

from app.analytics.risk_engine import SupervisoryRiskEngine
from app.analytics.prioritization_engine import ReviewPrioritizationEngine
from app.analytics.graph_engine import SupervisoryEvidenceGraphEngine
from app.evidence.assembler import EvidenceAssembler
from app.core.logging import logger


@dataclass
class BenchmarkRunResult:
    dataset_size_label: str
    target_alert_count: int
    actual_alert_count: int
    asset_count: int
    cse_count: int
    ingestion_time_seconds: float
    ingestion_rows_per_second: float
    execution_gap_findings: int
    execution_gap_time_seconds: float
    negative_space_findings: int
    negative_space_time_seconds: float
    evidence_records_assembled: int
    evidence_time_seconds: float
    risk_scores_computed: int
    risk_time_seconds: float
    queue_items_prioritized: int
    prioritization_time_seconds: float
    graph_node_count: int
    graph_edge_count: int
    graph_construction_time_seconds: float
    total_pipeline_elapsed_seconds: float
    overall_throughput_records_per_second: float
    peak_memory_mb: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SystemBenchmarkSuite:
    """Benchmarking suite for measuring SAT-SA scalability, throughput, memory, and engine execution costs."""

    @staticmethod
    def run_benchmark_scale(alert_count: int, seed: int = 42) -> BenchmarkRunResult:
        """Run performance benchmark across specified alert scale."""
        tracemalloc.start()
        process = psutil.Process(os.getpid())
        initial_mem = process.memory_info().rss / (1024 * 1024)

        t_pipeline_start = time.time()

        # 1. Data Generation & Ingestion Benchmark
        t0 = time.time()
        config = GeneratorConfig(
            num_cses=min(50, max(5, alert_count // 1000)),
            total_alerts=alert_count,
            seed=seed
        )

        dataset = SyntheticDatasetGenerator(config).generate()

        t_ingest = time.time() - t0
        ingest_throughput = alert_count / t_ingest if t_ingest > 0 else 0.0

        db: Session = SessionLocal()
        try:
            run_id = uuid.uuid4()
            import_id = uuid.uuid4()

            run = AnalysisRun(
                id=run_id,
                dataset_import_id=import_id,
                rule_version="1.0.0",
                model_version="1.0.0",
                status="RUNNING"

            )
            db.add(run)

            # Persist CSEs, Assets, Alerts into DB for DB-bound engine test
            cses_db = [CSE(id=uuid.UUID(str(c["id"])), name=c["name"], sector=c["sector"], entity_type=c["entity_type"], size_tier=c["size_tier"]) for c in dataset["cses"]]
            assets_db = [Asset(id=uuid.UUID(str(a["id"])), cse_id=uuid.UUID(str(a["cse_id"])), name=a["name"], asset_type=a["asset_type"], criticality=a["criticality"], status=a["status"]) for a in dataset["assets"]]
            
            alerts_db = []
            for al in dataset["alerts"]:
                alerts_db.append(Alert(
                    id=uuid.UUID(str(al["id"])),
                    cse_id=uuid.UUID(str(al["cse_id"])),
                    asset_id=uuid.UUID(str(al["asset_id"])),
                    source_system=al.get("source_system", "SIEM"),
                    category=al.get("category", "UNSPECIFIED"),
                    severity=al.get("severity", "MEDIUM"),
                    raw_severity=al.get("raw_severity", "MEDIUM"),
                    status=al.get("status", "OPEN"),
                    created_at=al["created_at"]
                ))

            db.add_all(cses_db + assets_db + alerts_db)
            db.commit()

            # 2. Execution Gap Engine Benchmark
            t0 = time.time()
            gap_engine = ExecutionGapEngine(db=db)
            run_gap = gap_engine.run_analysis(dataset_import_id=import_id, analysis_run_id=run_id)
            t_gap = time.time() - t0

            # 3. Negative Space Engine Benchmark
            t0 = time.time()
            neg_engine = NegativeSpaceEngine(db=db)
            run_neg = neg_engine.run_analysis(dataset_import_id=import_id, analysis_run_id=run_id)
            t_neg = time.time() - t0


            # Combine Findings
            total_findings = db.query(Finding).filter(Finding.analysis_run_id == run_id).all()

            # 4. Evidence Engine Benchmark
            t0 = time.time()
            ev_count = 0
            for f in total_findings[:100]:  # Sample top 100 for evidence package timing
                pkg = EvidenceAssembler.build_evidence_package(db, f.id)
                if pkg:
                    ev_count += len(pkg.supporting_records)
            t_ev = time.time() - t0

            # 5. Supervisory Risk Engine Benchmark
            t0 = time.time()
            risk_scores = SupervisoryRiskEngine.compute_supervisory_risk(db, run_id)
            t_risk = time.time() - t0

            # 6. Review Prioritization Engine Benchmark
            t0 = time.time()
            queue, p_metrics = ReviewPrioritizationEngine.generate_review_queue(db, run_id, target_queue_size=10)
            t_prioritization = time.time() - t0

            # 7. Supervisory Evidence Graph Benchmark
            t0 = time.time()
            G = SupervisoryEvidenceGraphEngine.build_graph_for_analysis_run(db, run_id)
            t_graph = time.time() - t0

            total_elapsed = time.time() - t_pipeline_start
            overall_throughput = alert_count / total_elapsed if total_elapsed > 0 else 0.0

            current_mem, peak_mem = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            peak_mem_mb = round((peak_mem / (1024 * 1024)) + initial_mem, 2)

            return BenchmarkRunResult(
                dataset_size_label=f"{alert_count // 1000}K_ALERTS",
                target_alert_count=alert_count,
                actual_alert_count=len(alerts_db),
                asset_count=len(assets_db),
                cse_count=len(cses_db),
                ingestion_time_seconds=round(t_ingest, 4),
                ingestion_rows_per_second=round(ingest_throughput, 2),
                execution_gap_findings=run_gap.findings_generated if run_gap else 0,
                execution_gap_time_seconds=round(t_gap, 4),
                negative_space_findings=run_neg.findings_generated if run_neg else 0,

                negative_space_time_seconds=round(t_neg, 4),
                evidence_records_assembled=ev_count,
                evidence_time_seconds=round(t_ev, 4),
                risk_scores_computed=len(risk_scores),
                risk_time_seconds=round(t_risk, 4),
                queue_items_prioritized=len(queue),
                prioritization_time_seconds=round(t_prioritization, 4),
                graph_node_count=G.number_of_nodes(),
                graph_edge_count=G.number_of_edges(),
                graph_construction_time_seconds=round(t_graph, 4),
                total_pipeline_elapsed_seconds=round(total_elapsed, 4),
                overall_throughput_records_per_second=round(overall_throughput, 2),
                peak_memory_mb=peak_mem_mb
            )

        finally:
            db.close()
