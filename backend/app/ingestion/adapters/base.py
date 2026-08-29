from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Iterator
from dataclasses import dataclass, field
from enum import Enum


class FieldProvenance(str, Enum):
    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    UNAVAILABLE = "UNAVAILABLE"
    SYNTHETICALLY_AUGMENTED = "SYNTHETICALLY_AUGMENTED"


@dataclass
class DatasetMetadata:
    dataset_name: str
    source: str
    license: str
    version: str
    description: str
    is_hybrid: bool = False
    ground_truth_present: bool = False
    field_provenance_map: Dict[str, FieldProvenance] = field(default_factory=dict)
    limitations: List[str] = field(default_factory=list)


@dataclass
class CanonicalRecord:
    entity_type: str  # "CSE", "Asset", "Alert", "Investigation", "MaintenanceLog"
    payload: Dict[str, Any]
    raw_payload: Dict[str, Any]
    provenance_metadata: Dict[str, Any] = field(default_factory=dict)


class BaseIngestionAdapter(ABC):
    """Base Ingestion Adapter for streaming files into canonical dictionary batches."""

    def __init__(self, source_path_or_uri: str):
        self.source_path_or_uri = source_path_or_uri

    @abstractmethod
    def detect_entity_type(self) -> str:
        """Detect entity type (alerts, assets, cses, etc.) from path or content."""
        pass

    @abstractmethod
    def stream_batches(self, chunk_size: int = 5000) -> Iterator[List[Dict[str, Any]]]:
        """Yield batches of records as dictionaries for high-throughput streaming."""
        pass


class BaseDatasetAdapter(ABC):
    """Abstract adapter interface converting external/realistic formats into canonical SAT-SA schema."""

    def __init__(self, metadata: DatasetMetadata):
        self.metadata = metadata

    @abstractmethod
    def parse_file(self, file_path: str) -> Iterator[CanonicalRecord]:
        """Stream or iterate canonical records from external file."""
        pass

    @abstractmethod
    def validate_schema(self, headers: List[str]) -> bool:
        """Validate header compatibility."""
        pass


