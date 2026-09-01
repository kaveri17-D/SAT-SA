"""Cross-Source Consistency & Conflict Validator."""
from typing import Dict, List, Any


class CrossSourceConsistencyValidator:
    """Validates cross-source overlaps, verifies consistency, and records discrepancies."""

    @staticmethod
    def validate_cross_source(
        nvd_data: Dict[str, Any],
        kev_data: Dict[str, Any],
        attack_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        nvd_vulns = nvd_data.get("vulnerabilities", {})
        kev_vulns = kev_data.get("vulnerabilities", {})
        attack_techs = attack_data.get("techniques", {})

        overlap_cves = set(nvd_vulns.keys()).intersection(set(kev_vulns.keys()))
        conflicts = []
        consistent_records = 0

        for cve_id in overlap_cves:
            nvd_item = nvd_vulns[cve_id]
            kev_item = kev_vulns[cve_id]

            # Check CVSS presence
            if nvd_item.get("cvss_v3_base_score") is None:
                conflicts.append({
                    "cve_id": cve_id,
                    "issue_type": "MISSING_NVD_CVSS",
                    "details": f"CVE {cve_id} is in CISA KEV but lacks NVD CVSS v3.1 metrics."
                })

            # Check product name consistency
            nvd_desc = nvd_item.get("description", "").lower()
            kev_prod = kev_item.get("product", "").lower()
            if kev_prod and kev_prod not in nvd_desc and kev_item.get("vendor_project", "").lower() not in nvd_desc:
                conflicts.append({
                    "cve_id": cve_id,
                    "issue_type": "PRODUCT_NAME_DIVERGENCE",
                    "details": f"Product '{kev_item.get('product')}' from KEV not explicitly referenced in NVD description."
                })
            else:
                consistent_records += 1

        return {
            "total_nvd_records": len(nvd_vulns),
            "total_kev_records": len(kev_vulns),
            "total_attack_techniques": len(attack_techs),
            "overlap_cve_count": len(overlap_cves),
            "overlap_cves_count": len(overlap_cves),
            "matching_cves": sorted(list(overlap_cves)),
            "nvd_only_cves": sorted(list(set(nvd_vulns.keys()) - set(kev_vulns.keys()))),
            "kev_only_cves": sorted(list(set(kev_vulns.keys()) - set(nvd_vulns.keys()))),
            "consistent_overlap_count": consistent_records,
            "conflict_count": len(conflicts),
            "conflicts": conflicts
        }
