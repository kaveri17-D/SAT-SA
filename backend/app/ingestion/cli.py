import argparse
import os
import sys
from app.ingestion.pipeline import IngestionPipeline
from app.core.database import SessionLocal


def main():
    parser = argparse.ArgumentParser(description="SAT-SA Supervisory Data Ingestion CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available ingestion commands")

    ingest_parser = subparsers.add_parser("ingest", help="Ingest a CSV/JSON file or directory into SAT-SA")
    ingest_parser.add_argument("path", help="Path to CSV/JSON file or directory containing exports")
    ingest_parser.add_argument("--chunk-size", type=int, default=5000, help="Streaming chunk size (default: 5000)")
    ingest_parser.add_argument("--user", type=str, default="CLI_SUPERVISOR", help="Examiner handle performing import")

    args = parser.parse_args()

    if args.command != "ingest":
        parser.print_help()
        sys.exit(1)

    path = args.path
    if not os.path.exists(path):
        print(f"Error: Path '{path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    pipeline = IngestionPipeline(db=db, imported_by=args.user)

    files_to_process = []
    if os.path.isdir(path):
        # Process files in dependency order
        ordered_names = ["cses.csv", "assets.csv", "analysts.csv", "alerts.csv", "investigations.csv", "escalations.csv", "cases.csv", "closures.csv"]
        for name in ordered_names:
            full_p = os.path.join(path, name)
            if os.path.exists(full_p):
                files_to_process.append(full_p)
        for fname in os.listdir(path):
            if fname == "ground_truth.json":
                continue
            full_p = os.path.join(path, fname)
            if full_p not in files_to_process and (fname.endswith(".csv") or fname.endswith(".json")):
                files_to_process.append(full_p)
    else:
        files_to_process.append(path)

    print("=================================================================")
    print("SAT-SA Supervisory Intelligence — Canonical Data Ingestion")
    print("=================================================================")
    print(f"Target Path    : {path}")
    print(f"Files Found    : {len(files_to_process)}")
    print(f"Chunk Size     : {args.chunk_size}")
    print("-----------------------------------------------------------------")

    total_rows = 0
    total_accepted = 0
    total_quarantined = 0

    for fpath in files_to_process:
        print(f"Ingesting: {os.path.basename(fpath)} ... ", end="", flush=True)
        try:
            result = pipeline.process_file(fpath, chunk_size=args.chunk_size)
            print(f"DONE | Rows: {result.row_count} | Accepted: {result.accepted_count} | Quarantined: {result.quarantined_count} | Quality: {result.completeness_score}%")
            total_rows += result.row_count
            total_accepted += result.accepted_count
            total_quarantined += result.quarantined_count
        except Exception as e:
            print(f"FAILED | Error: {str(e)}")

    print("=================================================================")
    print(f"Summary: Processed {total_rows} rows across {len(files_to_process)} file(s).")
    print(f"Accepted Records   : {total_accepted}")
    print(f"Quarantined Records: {total_quarantined}")
    print("=================================================================")


if __name__ == "__main__":
    main()
