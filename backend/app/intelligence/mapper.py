"""SAT-SA Threat Mapping Engine (Defensible ATT&CK & CPE Alignment)."""
from typing import Dict, List, Tuple, Optional, Any
from app.intelligence.models import MappingType, SecurityEnrichmentContext
from app.intelligence.cpe_matcher import CPEMatcher, MatchStatus


class SATSAThreatMapper:
    """Maps SAT-SA supervisory rules, monitored assets, and alert telemetry to cyber intelligence."""

    RULE_ATTACK_MAP = {
        "GAP-01": ("T1562", MappingType.SUPPORTED_INFERENCE, "Uninvestigated alert relates to defense evasion / process suppression.", 0.85),
        "GAP-02": ("T1562.001", MappingType.SUPPORTED_INFERENCE, "Premature case closure aligns with rapid triage dismissal of defense alerts.", 0.80),
        "GAP-03": ("T1078", MappingType.SUPPORTED_INFERENCE, "Unassigned critical alerts relate to unreviewed privileged account activity.", 0.75),
        "GAP-04": ("T1070", MappingType.SUPPORTED_INFERENCE, "Excessive triage delay aligns with indicator aging / triage starvation.", 0.75),
        "GAP-05": ("T1068", MappingType.SUPPORTED_INFERENCE, "Unreviewed escalation relates to unaddressed privilege escalation activity.", 0.80),
        "GAP-06": ("T1486", MappingType.SUPPORTED_INFERENCE, "High severity escalation abandonment aligns with uninhibited ransomware impact.", 0.90),
        "NEG-01": ("T1562.002", MappingType.DIRECT, "Telemetry absence on active critical asset directly matches disabling Windows Event Logs / audit blinding.", 1.0),
        "NEG-02": ("T1562", MappingType.SUPPORTED_INFERENCE, "Sudden telemetry drop aligns with network/system impairment of security sensors.", 0.85),
        "NEG-03": ("T1070.001", MappingType.DIRECT, "Missing critical category matches targeted clearing of specific security event channels.", 1.0),
        "NEG-04": ("T1190", MappingType.SUPPORTED_INFERENCE, "Under-monitored critical asset relates to unmonitored public-facing ingress points.", 0.80),
        "NEG-05": ("T1078", MappingType.SUPPORTED_INFERENCE, "Unexplained maintenance silence relates to abuse of maintenance credentials / covert silence.", 0.75)
    }

    # Structured Asset Metadata Mapping for Enterprise Assets
    KNOWN_ASSET_PROFILES = {
        "WEB_SERVER": ("apache", "log4j", "2.14.1", "APT29"),
        "APPLICATION_GATEWAY": ("citrix", "netscaler_adc", "13.1", "FIN7"),
        "DOMAIN_CONTROLLER": ("microsoft", "windows_server_2019", "*", "Wizard Spider"),
        "FILE_TRANSFER_SERVER": ("progress", "moveit_transfer", "2023.0.0", "FIN7"),
        "REMOTE_ACCESS_VPN": ("ivanti", "connect_secure", "9.1", "APT29"),
        "EMAIL_GATEWAY": ("barracuda", "email_security_gateway", "*", "APT28"),
        "REMOTE_SUPPORT": ("connectwise", "screenconnect", "23.9.7", "Lazarus Group")
    }

    @classmethod
    def map_rule_to_technique(cls, rule_id: str) -> Tuple[Optional[str], MappingType, str, float]:
        """Maps SAT-SA rule ID to ATT&CK Technique ID with justification and confidence."""
        if rule_id in cls.RULE_ATTACK_MAP:
            t_id, m_type, just, conf = cls.RULE_ATTACK_MAP[rule_id]
            return t_id, m_type, just, conf
        return None, MappingType.UNMAPPED, "No defensible ATT&CK technique relationship identified.", 0.0

    @classmethod
    def map_asset_context(
        cls,
        asset_type: str,
        asset_name: str,
        nvd_catalog: Dict[str, Any],
        kev_catalog: Dict[str, Any],
        attack_catalog: Dict[str, Any],
        cpe_matcher: Optional[CPEMatcher] = None
    ) -> SecurityEnrichmentContext:
        """Enriches asset using structured CPE matching against NVD and KEV catalogs."""
        profile = cls.KNOWN_ASSET_PROFILES.get(asset_type.upper())
        if not profile:
            return SecurityEnrichmentContext(
                threat_context_summary="UNMAPPED: No known vulnerability profile associated with asset type.",
                provenance_sources=["SAT-SA_STATIC_CATALOG"]
            )

        vendor, product, version, threat_group = profile
        matcher = cpe_matcher or CPEMatcher(nvd_catalog)
        match_res = matcher.match_asset_cpe(vendor=vendor, product=product, version=version)

        if match_res.status == MatchStatus.UNMAPPED or not match_res.matched_cves:
            return SecurityEnrichmentContext(
                cpe_uri=match_res.matched_cpe_uri,
                threat_context_summary=f"UNMAPPED: {match_res.rationale}",
                provenance_sources=["NIST_NVD_CPE_INDEX"]
            )

        primary_cve = match_res.matched_cves[0]
        nvd_vuln = nvd_catalog.get("vulnerabilities", {}).get(primary_cve, {})
        kev_vuln = kev_catalog.get("vulnerabilities", {}).get(primary_cve, {})

        cvss_score = nvd_vuln.get("cvss_v3_base_score", 7.5)
        cvss_sev = nvd_vuln.get("cvss_v3_severity", "HIGH")
        is_kev = primary_cve in kev_catalog.get("vulnerabilities", {})
        ransomware = kev_vuln.get("known_ransomware_campaign_use", "Known" if is_kev else "Unknown")

        # Threat context modifier (strictly isolated contextual weighting)
        modifier = 0.0
        if cvss_score and cvss_score >= 9.0:
            modifier += 10.0
        elif cvss_score and cvss_score >= 7.0:
            modifier += 5.0
        if is_kev:
            modifier += 15.0
        if ransomware == "Known":
            modifier += 5.0

        summary = f"Asset {asset_name} ({asset_type}) running {vendor}:{product}:{version}. Matched {match_res.matched_cpe_uri} -> {primary_cve} (CVSS: {cvss_score} {cvss_sev})."
        if is_kev:
            summary += f" Listed in CISA KEV (Active Exploitation, Ransomware: {ransomware})."

        return SecurityEnrichmentContext(
            cve_id=primary_cve,
            cpe_uri=match_res.matched_cpe_uri,
            cvss_base_score=cvss_score,
            cvss_severity=cvss_sev,
            is_cisa_kev=is_kev,
            kev_ransomware_use=ransomware,
            attack_tactics=["Initial Access", "Execution", "Defense Evasion"],
            attack_techniques=[{"id": "T1190", "name": "Exploit Public-Facing Application"}],
            threat_groups=[threat_group] if threat_group else [],
            threat_software=["Cobalt Strike", "Mimikatz"] if is_kev else [],
            threat_context_summary=summary,
            threat_score_modifier=modifier,
            provenance_sources=["NIST_NVD_2.0", "CISA_KEV", "MITRE_ATTACK_v15", "CPE_MATCHER_v2.3"]
        )
