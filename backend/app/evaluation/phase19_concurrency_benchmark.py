"""Phase 19: Progressive Multi-Client Concurrent Load Benchmark."""
import time
import json
import uuid
import threading
import concurrent.futures
from typing import Dict, List, Any
import uvicorn
import urllib.request

from app.main import app as fastapi_app
from app.core.database import SessionLocal, engine, Base
from app.models import CSE, AnalysisRun, ReportType
from app.db.seed import seed_baseline_reference_data
from app.reporting.builder import ReportBuilder
from app.reporting.schemas import ReportGenerateRequest


class LiveServer:
    def __init__(self, host="127.0.0.1", port=8889):
        self.host = host
        self.port = port
        self.config = uvicorn.Config(fastapi_app, host=self.host, port=self.port, log_level="warning")
        self.server = uvicorn.Server(self.config)
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        for _ in range(50):
            try:
                urllib.request.urlopen(f"http://{self.host}:{self.port}/api/v1/health/live", timeout=1)
                return
            except Exception:
                time.sleep(0.1)
        raise RuntimeError("LiveServer failed to start within 5 seconds.")

    def stop(self):
        self.server.should_exit = True
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)


def run_concurrency_benchmark():
    print("=================================================================")
    print("SAT-SA PHASE 19 — MULTI-CLIENT CONCURRENCY & ISOLATION BENCHMARK")
    print("=================================================================")

    server = LiveServer(host="127.0.0.1", port=8889)
    server.start()

    client_concurrency_tiers = [1, 5, 10, 25, 50]
    results = {
        "benchmark": "MULTI_CLIENT_CONCURRENCY_BENCHMARK",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tiers": []
    }

    try:
        endpoints = [
            "/api/v1/health/live",
            "/api/v1/health/ready",
            "/api/v1/prioritization/metrics/latest",
            "/api/v1/prioritization/cses",
            "/api/v1/prioritization/queue/latest",
            "/api/v1/reports",
            "/api/v1/audit/verify",
            "/api/v1/audit/logs"
        ]

        for concurrency in client_concurrency_tiers:
            requests_per_client = 10
            total_requests = concurrency * requests_per_client
            print(f"\n[*] Testing Concurrency Tier: {concurrency} Concurrent Clients ({total_requests} total requests)...")

            latencies = []
            errors = 0

            def make_request(idx):
                ep = endpoints[idx % len(endpoints)]
                url = f"http://127.0.0.1:8889{ep}"
                t0 = time.perf_counter()
                try:
                    req = urllib.request.Request(url)
                    with urllib.request.urlopen(req, timeout=5) as response:
                        code = response.getcode()
                        lat = time.perf_counter() - t0
                        if code == 200:
                            return (True, lat)
                        return (False, lat)
                except Exception as e:
                    return (False, time.perf_counter() - t0)

            t_start = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [executor.submit(make_request, i) for i in range(total_requests)]
                for fut in concurrent.futures.as_completed(futures):
                    success, lat = fut.result()
                    if success:
                        latencies.append(lat)
                    else:
                        errors += 1

            total_duration = round(time.perf_counter() - t_start, 3)
            successful_reqs = len(latencies)
            success_rate = round((successful_reqs / total_requests) * 100, 2)
            avg_latency_ms = round((sum(latencies) / len(latencies)) * 1000, 2) if latencies else 0
            p95_latency_ms = round(sorted(latencies)[int(len(latencies) * 0.95)] * 1000, 2) if latencies else 0
            throughput = round(successful_reqs / total_duration, 1)

            tier_data = {
                "concurrency": concurrency,
                "total_requests": total_requests,
                "successful_requests": successful_reqs,
                "error_count": errors,
                "success_rate_pct": success_rate,
                "duration_seconds": total_duration,
                "throughput_req_per_sec": throughput,
                "avg_latency_ms": avg_latency_ms,
                "p95_latency_ms": p95_latency_ms
            }
            results["tiers"].append(tier_data)
            print(f"[+] Tier {concurrency} Clients: {successful_reqs}/{total_requests} OK ({success_rate}%) | Duration: {total_duration}s | Throughput: {throughput} req/s | Avg Latency: {avg_latency_ms} ms | p95: {p95_latency_ms} ms")

    finally:
        server.stop()

    import os
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    out_dir = os.path.join(root_dir, "data", "validation", "phase19")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "PHASE19_CONCURRENCY_BENCHMARK.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    with open(os.path.join(root_dir, "backend", "data", "validation", "phase19", "PHASE19_CONCURRENCY_BENCHMARK.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n=================================================================")
    print("[OK] CONCURRENCY BENCHMARK COMPLETED SUCCESSFULLY!")
    print("=================================================================")
    return results


if __name__ == "__main__":
    run_concurrency_benchmark()
