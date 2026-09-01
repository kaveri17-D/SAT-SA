"""Official NIST NVD 2.0 Vulnerability Feed Parser."""
import json
import re
from typing import Dict, List, Tuple, Any
from app.intelligence.models import NVDRecord, DataQualityReport


class NVDParser:
    """Parses NIST National Vulnerability Database (NVD) 2.0 JSON feeds."""

    @staticmethod
    def parse_feed(feed_data: Dict[str, Any]) -> Tuple[List[NVDRecord], DataQualityReport]:
        vulns = feed_data.get("vulnerabilities", [])
        total = len(vulns)
        valid = 0
        rejected = 0
        duplicates = 0
        malformed_ids = 0
        missing_fields = 0
        issues = []

        seen_cves = set()
        records: List[NVDRecord] = []
        cve_regex = re.compile(r"^CVE-\d{4}-\d{4,7}$")

        for item in vulns:
            if not isinstance(item, dict):
                rejected += 1
                continue
            cve_obj = item.get("cve", {})
            if not isinstance(cve_obj, dict):
                rejected += 1
                continue
            cve_id = cve_obj.get("id", "").strip()

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

            # Descriptions (English)
            descriptions = cve_obj.get("descriptions", [])
            desc_text = ""
            for d in descriptions:
                if d.get("lang") == "en":
                    desc_text = d.get("value", "")
                    break
            if not desc_text and descriptions:
                desc_text = descriptions[0].get("value", "")

            published = cve_obj.get("published", "")
            modified = cve_obj.get("lastModified", "")

            # CVSS Metrics (v3.1 > v3.0 > v2.0)
            metrics = cve_obj.get("metrics", {})
            cvss_v3_score = None
            cvss_v3_sev = None
            cvss_v3_vec = None
            cvss_v2_score = None

            if "cvssMetricV31" in metrics and metrics["cvssMetricV31"]:
                primary_v31 = metrics["cvssMetricV31"][0].get("cvssData", {})
                cvss_v3_score = float(primary_v31.get("baseScore", 0.0))
                cvss_v3_sev = primary_v31.get("baseSeverity", "UNKNOWN")
                cvss_v3_vec = primary_v31.get("vectorString", "")
            elif "cvssMetricV30" in metrics and metrics["cvssMetricV30"]:
                primary_v30 = metrics["cvssMetricV30"][0].get("cvssData", {})
                cvss_v3_score = float(primary_v30.get("baseScore", 0.0))
                cvss_v3_sev = primary_v30.get("baseSeverity", "UNKNOWN")
                cvss_v3_vec = primary_v30.get("vectorString", "")

            if "cvssMetricV2" in metrics and metrics["cvssMetricV2"]:
                primary_v2 = metrics["cvssMetricV2"][0].get("cvssData", {})
                cvss_v2_score = float(primary_v2.get("baseScore", 0.0))

            # CWEs
            cwes = []
            for w in cve_obj.get("weaknesses", []):
                for desc in w.get("description", []):
                    cwe_val = desc.get("value", "")
                    if cwe_val and cwe_val != "NVD-CWE-noinfo":
                        cwes.append(cwe_val)

            # CPE Configurations
            cpes = []
            for config in cve_obj.get("configurations", []):
                for node in config.get("nodes", []):
                    for match in node.get("cpeMatch", []):
                        criteria = match.get("criteria", "")
                        if criteria:
                            cpes.append(criteria)

            # References
            refs = [r.get("url", "") for r in cve_obj.get("references", []) if r.get("url")]

            records.append(NVDRecord(
                cve_id=cve_id,
                description=desc_text,
                published_date=published,
                last_modified_date=modified,
                cvss_v3_base_score=cvss_v3_score,
                cvss_v3_severity=cvss_v3_sev,
                cvss_v3_vector=cvss_v3_vec,
                cvss_v2_base_score=cvss_v2_score,
                cwe_ids=cwes,
                cpe_match_criteria=cpes,
                references=refs
            ))
            valid += 1

        report = DataQualityReport(
            source_name="NIST National Vulnerability Database (NVD 2.0)",
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
