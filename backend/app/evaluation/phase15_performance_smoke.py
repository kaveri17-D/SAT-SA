"""Phase 15: Operational Performance Smoke Test & Metrics Collector."""
import json
import os
import time
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models import (
    CSE, Asset, Finding, RiskScore, Evidence, AnalysisRun, DatasetImport,
    AssetCriticality, FindingSeverity, FindingStatus, ReportType, ReviewQueueItem, QueueItemStatus
)
from app.reporting.builder import ReportBuilder
from app.reporting.snapshot import SnapshotManager
from app.reporting.schemas import ReportGenerateRequest
from app.reporting.exporters.json_exporter import JSONReportExporter
from app.reporting.exporters.html_exporter import HTMLReportExporter
from app.audit.service import AuditService


def run_performance_smoke_benchmark():
    print("================================================================")
    print("SAT-SA PHASE 15 — OPERATIONAL PERFORMANCE SMOKE BENCHMARK")
    print("================================================================")

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "measurements": {}
    }

    # 1. Startup & Health Latency
    t0 = time.perf_counter()
    client = TestClient(app)
    t1 = time.perf_counter()
    results["measurements"]["testclient_init_latency_ms"] = round((t1 - t0) * 1000, 2)

    health_latencies = []
    for _ in range(20):
        th0 = time.perf_counter()
        resp = client.get("/api/v1/health")
        th1 = time.perf_counter()
        assert resp.status_code == 200
        health_latencies.append((th1 - th0) * 1000)
    
    results["measurements"]["health_endpoint_avg_latency_ms"] = round(sum(health_latencies) / len(health_latencies), 2)
    results["measurements"]["health_endpoint_p95_latency_ms"] = round(sorted(health_latencies)[int(len(health_latencies) * 0.95)], 2)
    print(f"[+] Health Endpoint Latency: {results['measurements']['health_endpoint_avg_latency_ms']} ms (avg)")

    # 2. Database & Assessment Execution Latency
    db = SessionLocal()
    try:
        t_assess_start = time.perf_counter()
        ds = DatasetImport(filename="smoke_telemetry.json", source="SMOKE_TEST", imported_by="SMOKE_RUNNER", row_count=100)
        db.add(ds)
        db.flush()

        run = AnalysisRun(id=uuid.uuid4(), dataset_import_id=ds.id, records_processed=100, findings_generated=5)
        db.add(run)
        db.flush()

        cse = CSE(name=f"SMOKE_CSE_{uuid.uuid4().hex[:6]}", sector="CRITICAL_INFRASTRUCTURE", entity_type="NUCLEAR_FACILITY", size_tier="TIER_1")
        db.add(cse)
        db.flush()

        assets = []
        for i in range(5):
            a = Asset(cse_id=cse.id, name=f"CONTROL_SYSTEM_PL_{i}", asset_type="PLC", criticality=AssetCriticality.CRITICAL)
            db.add(a)
            assets.append(a)
        db.flush()

        findings = []
        for i, a in enumerate(assets):
            f = Finding(
                analysis_run_id=run.id,
                cse_id=cse.id,
                asset_id=a.id,
                rule_id=f"GAP-0{i+1}",
                severity=FindingSeverity.HIGH,
                anomaly_score=0.88 + (i * 0.02),
                confidence=0.95,
                supervisory_priority=8.5 + (i * 0.2),
                reason=f"Supervisory telemetry gap detected on PLC unit {i}.",
                expected_behaviour="Continuous SCADA telemetry heartbeat.",
                observed_behaviour="Telemetry drop exceeding supervisory threshold.",
                recommendation="Dispatch field engineering team for inspection.",
                status=FindingStatus.NEW,
                evidence_refs=[{"source": "telemetry", "id": f"TEL-{i}"}]
            )
            db.add(f)
            findings.append(f)
        db.flush()

        for f in findings:
            ev = Evidence(
                finding_id=f.id,
                evidence_type="OPERATIONAL_GAP",
                source_table="alerts",
                source_record_id=f"REC-{f.rule_id}",
                description="Raw supervisory alert package"
            )
            db.add(ev)
        db.flush()

        risk = RiskScore(
            cse_id=cse.id,
            analysis_run_id=run.id,
            total_score=78.4,
            raw_score=78.4,
            normalized_score=78.4,
            risk_band="HIGH",
            component_breakdown={"execution_gap": 40.0, "negative_space": 18.4, "peer_deviation": 8.0, "investigation_anomaly": 12.0, "asset_criticality": 30.0}
        )
        db.add(risk)
        db.flush()

        for i, f in enumerate(findings):
            q = ReviewQueueItem(
                analysis_run_id=run.id,
                finding_id=f.id,
                cse_id=cse.id,
                rank=i+1,
                priority_score=f.supervisory_priority,
                priority_band="HIGH",
                status=QueueItemStatus.NEW,
                rationale="Supervisory queue priority item",
                contributing_factors={"severity": 8.0, "risk_score": 78.4},
                explanation_json={"driver": "Supervisory gap"}
            )
            db.add(q)
        db.commit()
        t_assess_end = time.perf_counter()
        results["measurements"]["assessment_persistence_latency_ms"] = round((t_assess_end - t_assess_start) * 1000, 2)
        print(f"[+] Assessment Pipeline Ingestion Latency: {results['measurements']['assessment_persistence_latency_ms']} ms")

        # 3. Report Generation Latencies (All 5 Types)
        report_gen_times = {}
        snapshots = {}
        for r_type in [
            ReportType.EXECUTIVE,
            ReportType.TECHNICAL,
            ReportType.RISK,
            ReportType.ASSET,
            ReportType.VULNERABILITY_THREAT_INTEL
        ]:
            t_rg0 = time.perf_counter()
            req = ReportGenerateRequest(
                assessment_id=str(run.id),
                report_type=r_type,
                cse_id=str(cse.id),
                title=f"Performance Smoke {r_type.value} Report"
            )
            snap = ReportBuilder.generate_report(db, req)
            t_rg1 = time.perf_counter()
            gen_ms = round((t_rg1 - t_rg0) * 1000, 2)
            report_gen_times[r_type.value] = gen_ms
            snapshots[r_type.value] = snap
            print(f"[+] Report Generation [{r_type.value}]: {gen_ms} ms (Report #{snap.report_number})")

        results["measurements"]["report_generation_latencies_ms"] = report_gen_times
        results["measurements"]["report_generation_avg_ms"] = round(sum(report_gen_times.values()) / len(report_gen_times), 2)

        # 4. Report Retrieval & Verification Latency
        exec_snap = snapshots[ReportType.EXECUTIVE.value]
        t_ver0 = time.perf_counter()
        is_valid, _ = SnapshotManager.verify_integrity(exec_snap)
        t_ver1 = time.perf_counter()
        assert is_valid is True
        results["measurements"]["snapshot_integrity_verification_latency_ms"] = round((t_ver1 - t_ver0) * 1000, 2)
        print(f"[+] Snapshot SHA-256 Verification: {results['measurements']['snapshot_integrity_verification_latency_ms']} ms")

        # 5. Export Latencies
        t_json0 = time.perf_counter()
        json_out = JSONReportExporter.export(exec_snap)
        t_json1 = time.perf_counter()
        results["measurements"]["json_export_latency_ms"] = round((t_json1 - t_json0) * 1000, 2)
        results["measurements"]["json_export_size_bytes"] = len(json_out.encode("utf-8"))

        t_html0 = time.perf_counter()
        html_out = HTMLReportExporter.export(exec_snap)
        t_html1 = time.perf_counter()
        results["measurements"]["html_export_latency_ms"] = round((t_html1 - t_html0) * 1000, 2)
        results["measurements"]["html_export_size_bytes"] = len(html_out.encode("utf-8"))
        print(f"[+] JSON Export: {results['measurements']['json_export_latency_ms']} ms ({results['measurements']['json_export_size_bytes']} bytes)")
        print(f"[+] HTML Export: {results['measurements']['html_export_latency_ms']} ms ({results['measurements']['html_export_size_bytes']} bytes)")

        # 6. Audit Trail Verification Latency
        t_aud0 = time.perf_counter()
        is_aud_valid, total_aud, verified_aud, _, _ = AuditService.verify_audit_trail_integrity(db)
        t_aud1 = time.perf_counter()
        assert is_aud_valid is True
        results["measurements"]["audit_verification_latency_ms"] = round((t_aud1 - t_aud0) * 1000, 2)
        results["measurements"]["audit_total_events_verified"] = verified_aud
        print(f"[+] Cryptographic Audit Chain Verification: {results['measurements']['audit_verification_latency_ms']} ms ({verified_aud} events verified)")

    finally:
        db.close()

    # Save to data/reports/PHASE_15_PERFORMANCE_SMOKE_REPORT.json
    os.makedirs("data/reports", exist_ok=True)
    out_path = "data/reports/PHASE_15_PERFORMANCE_SMOKE_REPORT.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[OK] Performance smoke report saved to {out_path}")
    print("================================================================")
    return results


if __name__ == "__main__":
    run_performance_smoke_benchmark()
