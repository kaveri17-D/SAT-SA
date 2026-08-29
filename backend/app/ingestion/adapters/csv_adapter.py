import os
import pandas as pd
from typing import Generator, List, Dict, Any
from app.ingestion.adapters.base import BaseIngestionAdapter


class CSVIngestionAdapter(BaseIngestionAdapter):
    """CSV Ingestion Adapter with chunked streaming capabilities for large datasets (~20GB scale)."""

    def detect_entity_type(self) -> str:
        filename = os.path.basename(self.source_path_or_uri).lower()
        if "alert" in filename:
            return "alerts"
        elif "asset" in filename:
            return "assets"
        elif "cse" in filename:
            return "cses"
        elif "investigation" in filename:
            return "investigations"
        elif "escalation" in filename:
            return "escalations"
        elif "case" in filename:
            return "cases"
        elif "closure" in filename:
            return "closures"
        elif "analyst" in filename:
            return "analysts"
        else:
            # Peek first row to detect entity by columns
            df_peek = pd.read_csv(self.source_path_or_uri, nrows=2)
            cols = set(df_peek.columns.str.lower())
            if "raw_severity" in cols or "category" in cols:
                return "alerts"
            if "criticality" in cols or "asset_type" in cols:
                return "assets"
            if "size_tier" in cols or "sector" in cols:
                return "cses"
            if "duration_seconds" in cols or "started_at" in cols:
                return "investigations"
            return "unknown"

    def stream_batches(self, chunk_size: int = 5000) -> Generator[List[Dict[str, Any]], None, None]:
        """Stream chunks using pandas read_csv for streaming large CSV files."""
        for chunk in pd.read_csv(self.source_path_or_uri, chunksize=chunk_size, keep_default_na=False):
            records = chunk.to_dict(orient="records")
            yield records
