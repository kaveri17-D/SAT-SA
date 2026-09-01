"""Phase 19: Progressive Scaled Streaming Ingestion & Bounded Memory Benchmark."""
import os
import sys
import time
import json
import uuid
import tempfile
import tracemalloc
from datetime import datetime, timezone
from typing import Dict, List, Any

from app.core.database import SessionLocal, engine, Base
from app.models import CSE, Asset, Alert, AssetCriticality, AlertSeverity
from app.ingestion.pipeline import IngestionPipeline


def generate_streaming_alert_file(file_path: str, record_count: int, cse_id: str, asset_id: str):
    """Generate a streaming JSON telemetry file with specified record count."""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("[\n")
        for i in range(record_count):
            alert = {
                "id": str(uuid.uuid4()),
                "cse_id": cse_id,
                "asset_id": asset_id,
                "source_system": "SIEM_SPLUNK",
                "category": "NETWORK" if i % 2 == 0 else "PRIVILEGE",
                "severity": "CRITICAL" if i % 10 == 0 else "HIGH",
                "raw_severity": "CRITICAL" if i % 10 == 0 else "HIGH",
                "status": "OPEN",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            json_str = json.dumps(alert)
            if i < record_count - 1:
                f.write(json_str + ",\n")
            else:
                f.write(json_str + "\n")
        f.write("]\n")


def run_streaming_benchmark():
    print("=================================================================")
    print("SAT-SA PHASE 19 — PROGRESSIVE STREAMING & BOUNDED MEMORY BENCHMARK")
    print("=================================================================")

    db = SessionLocal()
    try:
        # Create baseline CSE and Asset
        cse = db.query(CSE).filter(CSE.name == "STREAMING_SCALE_TEST_CSE").first()
        if not cse:
            cse = CSE(name="STREAMING_SCALE_TEST_CSE", sector="ENERGY", entity_type="GRID", size_tier="TIER_1")
            db.add(cse)
            db.commit()
            db.refresh(cse)

        asset = db.query(Asset).filter(Asset.name == "STREAMING_SCALE_TEST_ASSET").first()
        if not asset:
            asset = Asset(cse_id=cse.id, name="STREAMING_SCALE_TEST_ASSET", asset_type="GATEWAY", criticality=AssetCriticality.CRITICAL)
            db.add(asset)
            db.commit()
            db.refresh(asset)

        cse_id_str = str(cse.id)
        asset_id_str = str(asset.id)
    finally:
        db.close()

    # Define progressive tiers
    tiers = [
        {"name": "Tier 1 (5k alerts)", "count": 5000},
        {"name": "Tier 2 (25k alerts)", "count": 25000},
        {"name": "Tier 3 (50k alerts)", "count": 50000},
        {"name": "Tier 4 (100k alerts)", "count": 100000}
    ]

    benchmark_results = {
        "benchmark": "PROGRESSIVE_STREAMING_SCALE_BENCHMARK",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "chunk_size": 5000,
        "tiers": []
    }

    temp_dir = tempfile.mkdtemp(prefix="satsa_scale_")

    for tier in tiers:
        name = tier["name"]
        count = tier["count"]
        print(f"\n[*] Executing {name}: Generating {count} records...")
        file_path = os.path.join(temp_dir, f"alerts_{count}.json")
        t0_gen = time.perf_counter()
        generate_streaming_alert_file(file_path, count, cse_id_str, asset_id_str)
        gen_duration = round(time.perf_counter() - t0_gen, 2)
        file_size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)
        print(f"    Generated {file_size_mb} MB in {gen_duration}s")

        # Ingestion under Tracemalloc
        print(f"[*] Ingesting {count} records via streaming IngestionPipeline...")
        tracemalloc.start()
        t0_ingest = time.perf_counter()

        pipeline_db = SessionLocal()
        try:
            pipeline = IngestionPipeline(db=pipeline_db, imported_by="SCALE_BENCHMARK_RUNNER")
            ds_import = pipeline.process_file(file_path, chunk_size=5000)
            ingest_duration = round(time.perf_counter() - t0_ingest, 3)
            current_mem, peak_mem = tracemalloc.get_traced_memory()
            accepted_cnt = ds_import.accepted_count
            quarantined_cnt = ds_import.quarantined_count
        finally:
            pipeline_db.close()
            tracemalloc.stop()

        peak_mem_mb = round(peak_mem / (1024 * 1024), 2)
        throughput = round(count / ingest_duration, 1)

        tier_res = {
            "tier_name": name,
            "record_count": count,
            "file_size_mb": file_size_mb,
            "ingest_duration_seconds": ingest_duration,
            "throughput_records_per_sec": throughput,
            "peak_memory_mb": peak_mem_mb,
            "accepted_count": accepted_cnt,
            "quarantined_count": quarantined_cnt
        }
        benchmark_results["tiers"].append(tier_res)
        print(f"[+] {name} COMPLETE: Ingested {count} records in {ingest_duration}s ({throughput} rec/s) | Peak Memory: {peak_mem_mb} MB")

        # Clean up temporary json file
        try:
            os.remove(file_path)
        except Exception:
            pass

    try:
        os.rmdir(temp_dir)
    except Exception:
        pass

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    out_dir = os.path.join(root_dir, "data", "validation", "phase19")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "PHASE19_STREAMING_SCALE_BENCHMARK.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(benchmark_results, f, indent=2)

    backend_out_file = os.path.join(root_dir, "backend", "data", "validation", "phase19", "PHASE19_STREAMING_SCALE_BENCHMARK.json")
    os.makedirs(os.path.dirname(backend_out_file), exist_ok=True)
    with open(backend_out_file, "w", encoding="utf-8") as f:
        json.dump(benchmark_results, f, indent=2)

    print("\n=================================================================")
    print("[OK] STREAMING BENCHMARK SUCCESSFULLY COMPLETED!")
    print(f"     Results saved to: {out_file}")
    print("=================================================================")
    return benchmark_results


if __name__ == "__main__":
    run_streaming_benchmark()
