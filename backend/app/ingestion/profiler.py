import csv
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class DatasetProfile:
    file_name: str
    total_records: int
    total_columns: int
    column_names: List[str]
    null_counts: Dict[str, int]
    null_percentages: Dict[str, float]
    duplicate_record_count: int
    duplicate_percentage: float
    timestamp_min: Optional[str]
    timestamp_max: Optional[str]
    severity_distribution: Dict[str, int]
    category_distribution: Dict[str, int]
    entity_distribution: Dict[str, int]
    invalid_record_count: int
    schema_anomalies: List[str]
    profiled_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DatasetProfiler:
    """Produces detailed statistical profiles and markdown summaries for ingested datasets."""

    @staticmethod
    def profile_csv(file_path: str) -> DatasetProfile:
        total_records = 0
        null_counts: Dict[str, int] = {}
        severity_dist: Dict[str, int] = {}
        cat_dist: Dict[str, int] = {}
        entity_dist: Dict[str, int] = {}
        schema_anomalies: List[str] = []
        timestamps: List[str] = []
        seen_rows = set()
        duplicate_count = 0
        invalid_count = 0

        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            columns = reader.fieldnames or []
            for col in columns:
                null_counts[col] = 0

            for row in reader:
                total_records += 1
                
                # Check duplicates
                row_tuple = tuple(sorted(row.items()))
                if row_tuple in seen_rows:
                    duplicate_count += 1
                else:
                    seen_rows.add(row_tuple)

                # Track nulls
                for col in columns:
                    val = row.get(col, "")
                    if val is None or str(val).strip() == "":
                        null_counts[col] += 1

                # Severity
                sev = str(row.get("severity", "")).upper()
                if sev:
                    severity_dist[sev] = severity_dist.get(sev, 0) + 1

                # Category
                cat = str(row.get("category", row.get("event_type", "")))
                if cat:
                    cat_dist[cat] = cat_dist.get(cat, 0) + 1

                # Entity / CSE
                cse = str(row.get("cse_id", row.get("entity_id", "")))
                if cse:
                    entity_dist[cse] = entity_dist.get(cse, 0) + 1

                # Timestamp
                ts = row.get("timestamp") or row.get("created_at")
                if ts:
                    timestamps.append(str(ts))

        null_pcts = {
            col: round((count / total_records) * 100.0, 2) if total_records > 0 else 0.0
            for col, count in null_counts.items()
        }
        dup_pct = round((duplicate_count / total_records) * 100.0, 2) if total_records > 0 else 0.0

        ts_min = min(timestamps) if timestamps else None
        ts_max = max(timestamps) if timestamps else None

        profile = DatasetProfile(
            file_name=os.path.basename(file_path),
            total_records=total_records,
            total_columns=len(columns),
            column_names=columns,
            null_counts=null_counts,
            null_percentages=null_pcts,
            duplicate_record_count=duplicate_count,
            duplicate_percentage=dup_pct,
            timestamp_min=ts_min,
            timestamp_max=ts_max,
            severity_distribution=severity_dist,
            category_distribution=cat_dist,
            entity_distribution=entity_dist,
            invalid_record_count=invalid_count,
            schema_anomalies=schema_anomalies,
            profiled_at=datetime.utcnow().isoformat()
        )
        return profile

    @staticmethod
    def save_profile_reports(profile: DatasetProfile, json_path: str, md_path: str):
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, indent=2)

        md = f"""# Dataset Profile Report: {profile.file_name}

- **Profiled At**: `{profile.profiled_at}`
- **Total Records**: {profile.total_records:,}
- **Total Columns**: {profile.total_columns}
- **Duplicate Records**: {profile.duplicate_record_count} ({profile.duplicate_percentage}%)
- **Temporal Range**: `{profile.timestamp_min or 'N/A'}` to `{profile.timestamp_max or 'N/A'}`

---

## 1. Schema & Field Null Rates

| Column Name | Null Count | Null Percentage |
| :--- | :---: | :---: |
"""
        for col, pct in profile.null_percentages.items():
            md += f"| `{col}` | {profile.null_counts.get(col, 0)} | {pct:.1f}% |\n"

        md += """
---

## 2. Severity Distribution

| Severity | Count | Percentage |
| :--- | :---: | :---: |
"""
        for sev, cnt in profile.severity_distribution.items():
            pct = (cnt / profile.total_records) * 100.0 if profile.total_records > 0 else 0.0
            md += f"| **{sev}** | {cnt:,} | {pct:.1f}% |\n"

        md += """
---

## 3. Entity Distribution (Top 10)

| Entity / CSE ID | Alert Count |
| :--- | :---: |
"""
        top_entities = sorted(profile.entity_distribution.items(), key=lambda x: x[1], reverse=True)[:10]
        for ent, cnt in top_entities:
            md += f"| `{ent}` | {cnt:,} |\n"

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md)
