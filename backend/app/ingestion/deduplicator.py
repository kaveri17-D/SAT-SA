import hashlib
from typing import Set, Dict, Any, Tuple


class Deduplicator:
    """Deduplication handler ensuring ingestion idempotency."""

    def __init__(self):
        self.seen_ids: Set[str] = set()

    def generate_record_hash(self, record: Dict[str, Any], entity_type: str) -> str:
        """Generate a deterministic fingerprint hash for a record."""
        rec_id = str(record.get("id", ""))
        if rec_id:
            return f"{entity_type}:{rec_id}"

        # Hash key fields if explicit ID is missing
        key_str = f"{entity_type}:{record.get('cse_id')}:{record.get('asset_id')}:{record.get('created_at')}:{record.get('category')}"
        return hashlib.sha256(key_str.encode("utf-8")).hexdigest()

    def is_duplicate(self, record: Dict[str, Any], entity_type: str) -> bool:
        rec_hash = self.generate_record_hash(record, entity_type)
        if rec_hash in self.seen_ids:
            return True
        self.seen_ids.add(rec_hash)
        return False
