"""Robust CPE 2.3 URI Parser, Comparator and Asset Vulnerability Matcher."""
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any


class MatchStatus(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    VERSION_MATCH = "VERSION_MATCH"
    AMBIGUOUS_MATCH = "AMBIGUOUS_MATCH"
    UNMAPPED = "UNMAPPED"


@dataclass
class CPE23Uri:
    part: str  # a (application), o (operating system), h (hardware)
    vendor: str
    product: str
    version: str
    update: str = "*"
    edition: str = "*"
    language: str = "*"
    sw_edition: str = "*"
    target_sw: str = "*"
    target_hw: str = "*"
    other: str = "*"

    @classmethod
    def from_string(cls, cpe_str: str) -> Optional["CPE23Uri"]:
        """Parses a CPE 2.3 formatted string into a structured CPE23Uri object."""
        if not cpe_str or not cpe_str.startswith("cpe:2.3:"):
            return None
        parts = cpe_str.split(":")
        if len(parts) < 5:
            return None
        
        # Fill missing trailing attributes with wildcard '*'
        while len(parts) < 13:
            parts.append("*")

        return cls(
            part=parts[2].lower(),
            vendor=parts[3].lower(),
            product=parts[4].lower(),
            version=parts[5].lower(),
            update=parts[6].lower(),
            edition=parts[7].lower(),
            language=parts[8].lower(),
            sw_edition=parts[9].lower(),
            target_sw=parts[10].lower(),
            target_hw=parts[11].lower(),
            other=parts[12].lower(),
        )

    def matches(self, criteria: "CPE23Uri") -> bool:
        """Determines if this CPE satisfies the target criteria with wildcard handling."""
        if criteria.part != "*" and self.part != criteria.part:
            return False
        if criteria.vendor != "*" and self.vendor != criteria.vendor:
            return False
        if criteria.product != "*" and self.product != criteria.product:
            return False
        if criteria.version != "*" and criteria.version != self.version:
            # Check version match or wildcard
            if self.version != "*" and criteria.version != "*":
                return False
        return True


from dataclasses import dataclass, field


@dataclass
class CPEMatchResult:
    status: MatchStatus
    matched_cpe_uri: Optional[str] = None
    matched_cves: List[str] = field(default_factory=list)
    vendor: Optional[str] = None
    product: Optional[str] = None
    version: Optional[str] = None
    confidence: float = 0.0
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "matched_cpe_uri": self.matched_cpe_uri,
            "matched_cves": self.matched_cves or [],
            "vendor": self.vendor,
            "product": self.product,
            "version": self.version,
            "confidence": self.confidence,
            "rationale": self.rationale,
        }


class CPEMatcher:
    """Indexes NVD CPE configurations and matches asset software descriptions."""

    def __init__(self, nvd_catalog: Optional[Dict[str, Any]] = None):
        self.nvd_catalog = nvd_catalog or {}
        self.cpe_entries: List[Tuple[CPE23Uri, str, str]] = []  # (cpe_obj, raw_cpe_str, cve_id)
        self._build_index()

    def _build_index(self):
        vulns = self.nvd_catalog.get("vulnerabilities", {})
        for cve_id, v_data in vulns.items():
            for cpe_str in v_data.get("cpe_match_criteria", []):
                parsed = CPE23Uri.from_string(cpe_str)
                if parsed:
                    self.cpe_entries.append((parsed, cpe_str, cve_id))

    def match_asset_cpe(self, vendor: str, product: str, version: str = "*") -> CPEMatchResult:
        """Matches structured asset attributes against indexed NVD CPE criteria."""
        v_norm = vendor.strip().lower()
        p_norm = product.strip().lower()
        ver_norm = version.strip().lower() if version else "*"

        if not v_norm or not p_norm:
            return CPEMatchResult(
                status=MatchStatus.UNMAPPED,
                rationale="Missing required vendor or product name for CPE matching."
            )

        asset_cpe = CPE23Uri(
            part="a",
            vendor=v_norm,
            product=p_norm,
            version=ver_norm
        )

        exact_matches = []
        wildcard_matches = []

        for cpe_obj, raw_str, cve_id in self.cpe_entries:
            if cpe_obj.vendor == v_norm and cpe_obj.product == p_norm:
                if cpe_obj.version == ver_norm and ver_norm != "*":
                    exact_matches.append((cve_id, raw_str))
                elif cpe_obj.version == "*" or ver_norm == "*":
                    wildcard_matches.append((cve_id, raw_str))

        if exact_matches:
            cves = sorted(list(set([m[0] for m in exact_matches])))
            return CPEMatchResult(
                status=MatchStatus.EXACT_MATCH,
                matched_cpe_uri=exact_matches[0][1],
                matched_cves=cves,
                vendor=v_norm,
                product=p_norm,
                version=ver_norm,
                confidence=1.0,
                rationale=f"Exact CPE 2.3 match for {v_norm}:{p_norm}:{ver_norm} associated with {len(cves)} CVEs."
            )

        if wildcard_matches:
            cves = sorted(list(set([m[0] for m in wildcard_matches])))
            if len(cves) > 5:
                return CPEMatchResult(
                    status=MatchStatus.AMBIGUOUS_MATCH,
                    matched_cpe_uri=wildcard_matches[0][1],
                    matched_cves=cves,
                    vendor=v_norm,
                    product=p_norm,
                    version=ver_norm,
                    confidence=0.5,
                    rationale=f"Ambiguous wildcard match across {len(cves)} CVEs for {v_norm}:{p_norm}."
                )
            return CPEMatchResult(
                status=MatchStatus.VERSION_MATCH,
                matched_cpe_uri=wildcard_matches[0][1],
                matched_cves=cves,
                vendor=v_norm,
                product=p_norm,
                version=ver_norm,
                confidence=0.85,
                rationale=f"Version wildcard CPE match for {v_norm}:{p_norm} associated with {len(cves)} CVEs."
            )

        return CPEMatchResult(
            status=MatchStatus.UNMAPPED,
            vendor=v_norm,
            product=p_norm,
            version=ver_norm,
            rationale=f"No matching CPE criteria found in NVD catalog for {v_norm}:{p_norm}."
        )
