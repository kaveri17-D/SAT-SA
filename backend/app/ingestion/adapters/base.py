from abc import ABC, abstractmethod
from typing import Generator, List, Dict, Any


class BaseIngestionAdapter(ABC):
    """Abstract adapter interface for streaming data from CSV, JSON, or future DB/API sources."""

    def __init__(self, source_path_or_uri: str):
        self.source_path_or_uri = source_path_or_uri

    @abstractmethod
    def detect_entity_type(self) -> str:
        """Detect entity type (alerts, assets, cses, investigations, etc.)."""
        pass

    @abstractmethod
    def stream_batches(self, chunk_size: int = 5000) -> Generator[List[Dict[str, Any]], None, None]:
        """Stream data in chunked batches for memory efficiency on large datasets."""
        pass
