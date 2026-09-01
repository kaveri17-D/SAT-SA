"""JSON Report Exporter."""
import json
from typing import Dict, Any
from app.models import ReportSnapshot


class JSONReportExporter:
    """Exports report snapshot into structured canonical JSON."""

    @staticmethod
    def export(snapshot: ReportSnapshot) -> str:
        envelope = {
            "export_version": "1.0.0",
            "report_id": str(snapshot.id),
            "report_number": snapshot.report_number,
            "report_type": snapshot.report_type.value if hasattr(snapshot.report_type, "value") else str(snapshot.report_type),
            "title": snapshot.title,
            "generated_at": snapshot.generated_at.isoformat(),
            "generated_by": snapshot.generated_by,
            "sha256_checksum": snapshot.sha256_checksum,
            "is_tampered": snapshot.is_tampered,
            "summary": snapshot.summary_json,
            "content": snapshot.content_json,
            "metadata": snapshot.metadata_json or {}
        }
        return json.dumps(envelope, indent=2, sort_keys=True)
