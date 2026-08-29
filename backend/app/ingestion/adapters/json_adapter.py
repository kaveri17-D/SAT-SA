import json
import os
from typing import Generator, List, Dict, Any
from app.ingestion.adapters.base import BaseIngestionAdapter


class JSONIngestionAdapter(BaseIngestionAdapter):
    """JSON Ingestion Adapter supporting JSON array files and JSON lines format."""

    def detect_entity_type(self) -> str:
        filename = os.path.basename(self.source_path_or_uri).lower()
        for entity in ["alerts", "assets", "cses", "investigations", "escalations", "cases", "closures", "analysts"]:
            if entity in filename:
                return entity
        return "unknown"

    def stream_batches(self, chunk_size: int = 5000) -> Generator[List[Dict[str, Any]], None, None]:
        with open(self.source_path_or_uri, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content.startswith("["):
                data = json.loads(content)
                for i in range(0, len(data), chunk_size):
                    yield data[i:i + chunk_size]
            else:
                # JSON Lines format
                lines = content.splitlines()
                batch = []
                for line in lines:
                    if line.strip():
                        batch.append(json.loads(line))
                        if len(batch) >= chunk_size:
                            yield batch
                            batch = []
                if batch:
                    yield batch
