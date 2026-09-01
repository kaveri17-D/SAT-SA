"""Official CISA Known Exploited Vulnerabilities (KEV) Catalog Parser."""
import json
import re
from typing import Dict, List, Tuple, Any
from app.intelligence.models import KEVRecord, DataQualityReport


class CISAKEVParser:
    """Parses CISA Known Exploited Vulnerabilities (KEV) catalog JSON."""

    @staticmethod
    def parse_catalog(catalog_data: Dict[str, Any]) -> Tuple[List[KEVRecord], DataQualityReport]:
        vulns = catalog_data.get("vulnerabilities", [])
        total = len(vulns)
        valid = 0
        rejected = 0
        duplicates = 0
        malformed_ids = 0
        missing_fields = 0
        issues = []

        seen_cves = set()
        records: List[KEVRecord] = []

        cve_regex = re.compile(r"^CVE-\d{4}-\d{4,7}$")

        for item in vulns:
            if not isinstance(item, dict):
                rejected += 1
                continue
            cve_id = item.get("cveID", "").strip()
            vendor = item.get("vendorProject", "").strip()
            product = item.get("product", "").strip()
            vuln_name = item.get("vulnerabilityName", "").strip()
            date_added = item.get("dateAdded", "").strip()
            desc = item.get("shortDescription", "").strip()
            action = item.get("requiredAction", "").strip()
            ransomware = item.get("knownRansomwareCampaignUse", "Unknown").strip()
            notes = item.get("notes", "").strip()
            due_date = item.get("dueDate", None)

            if not cve_id:
                missing_fields += 1
                rejected += 1
                continue

            if not cve_regex.match(cve_id):
                malformed_ids += 1
                rejected += 1
                issues.append({"cve_id": cve_id, "error": "Malformed CVE identifier format."})
                continue

            if cve_id in seen_cves:
                duplicates += 1
                continue
            seen_cves.add(cve_id)

            if not vendor or not product:
                missing_fields += 1

            records.append(KEVRecord(
                cve_id=cve_id,
                vendor_project=vendor or "Unknown",
                product=product or "Unknown",
                vulnerability_name=vuln_name or f"Vulnerability {cve_id}",
                date_added=date_added,
                short_description=desc,
                required_action=action or "Apply vendor updates.",
                known_ransomware_campaign_use=ransomware,
                notes=notes,
                due_date=due_date
            ))
            valid += 1

        report = DataQualityReport(
            source_name="CISA Known Exploited Vulnerabilities Catalog",
            total_records=total,
            valid_records=valid,
            rejected_records=rejected,
            duplicate_records=duplicates,
            malformed_ids=malformed_ids,
            missing_required_fields=missing_fields,
            unmapped_entities=0,
            conflicting_records=0,
            issues=issues
        )

        return records, report
