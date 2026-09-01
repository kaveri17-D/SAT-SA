"""Official STIX 2.1 MITRE ATT&CK Enterprise Bundle Parser."""
import json
import re
from typing import Dict, List, Tuple, Any, Optional
from app.intelligence.models import (
    AttackBundle, AttackTactic, AttackTechnique, AttackGroup, AttackSoftware,
    AttackMitigation, AttackRelationship, DataQualityReport
)


class AttackSTIXParser:
    """Parses MITRE ATT&CK Enterprise STIX 2.1 JSON datasets."""

    @staticmethod
    def parse_bundle(bundle_data: Dict[str, Any]) -> Tuple[AttackBundle, DataQualityReport]:
        objects = bundle_data.get("objects", [])
        total = len(objects)
        valid = 0
        rejected = 0
        malformed_ids = 0
        missing_fields = 0
        deprecated_or_revoked = 0
        issues = []

        tactics: List[AttackTactic] = []
        techniques: List[AttackTechnique] = []
        groups: List[AttackGroup] = []
        software: List[AttackSoftware] = []
        mitigations: List[AttackMitigation] = []
        relationships: List[AttackRelationship] = []

        for obj in objects:
            if not isinstance(obj, dict):
                rejected += 1
                continue

            obj_type = obj.get("type")
            stix_id = obj.get("id", "")
            
            # Check revoked or deprecated
            if obj.get("revoked", False) or obj.get("x_mitre_deprecated", False):
                rejected += 1
                deprecated_or_revoked += 1
                continue

            try:
                if obj_type == "x-mitre-tactic":
                    ext_refs = obj.get("external_references", [])
                    tactic_id = ext_refs[0].get("external_id", stix_id) if ext_refs else stix_id
                    name = obj.get("name", "")
                    shortname = obj.get("x_mitre_shortname", name.lower().replace(" ", "-"))
                    desc = obj.get("description", "")
                    version = obj.get("x_mitre_version", "1.0")

                    if not name:
                        missing_fields += 1
                        continue

                    tactics.append(AttackTactic(
                        id=tactic_id,
                        stix_id=stix_id,
                        name=name,
                        shortname=shortname,
                        description=desc,
                        external_references=ext_refs,
                        version=version
                    ))
                    valid += 1

                elif obj_type == "attack-pattern":
                    ext_refs = obj.get("external_references", [])
                    tech_id = ext_refs[0].get("external_id", "") if ext_refs else ""
                    if not tech_id or not re.match(r"^T\d{4}(\.\d{3})?$", tech_id):
                        malformed_ids += 1
                        tech_id = tech_id or stix_id

                    name = obj.get("name", "")
                    desc = obj.get("description", "")
                    kill_chain = obj.get("kill_chain_phases", [])
                    tactic_refs = [kc.get("phase_name", "") for kc in kill_chain if kc.get("kill_chain_name") == "mitre-attack"]
                    is_sub = obj.get("x_mitre_is_subtechnique", False)
                    platforms = obj.get("x_mitre_platforms", [])
                    data_sources = obj.get("x_mitre_data_sources", [])
                    detection = obj.get("x_mitre_detection", "")
                    version = obj.get("x_mitre_version", "1.0")

                    if not name:
                        missing_fields += 1
                        continue

                    techniques.append(AttackTechnique(
                        id=tech_id,
                        stix_id=stix_id,
                        name=name,
                        description=desc,
                        tactics=tactic_refs,
                        is_subtechnique=is_sub,
                        platforms=platforms,
                        data_sources=data_sources,
                        detection_strategy=detection,
                        version=version
                    ))
                    valid += 1

                elif obj_type == "intrusion-set":
                    ext_refs = obj.get("external_references", [])
                    group_id = ext_refs[0].get("external_id", stix_id) if ext_refs else stix_id
                    name = obj.get("name", "")
                    aliases = obj.get("aliases", [])
                    desc = obj.get("description", "")
                    version = obj.get("x_mitre_version", "1.0")

                    if not name:
                        missing_fields += 1
                        continue

                    groups.append(AttackGroup(
                        id=group_id,
                        stix_id=stix_id,
                        name=name,
                        aliases=aliases,
                        description=desc,
                        version=version
                    ))
                    valid += 1

                elif obj_type in ("malware", "tool"):
                    ext_refs = obj.get("external_references", [])
                    soft_id = ext_refs[0].get("external_id", stix_id) if ext_refs else stix_id
                    name = obj.get("name", "")
                    platforms = obj.get("x_mitre_platforms", [])
                    desc = obj.get("description", "")
                    version = obj.get("x_mitre_version", "1.0")

                    if not name:
                        missing_fields += 1
                        continue

                    software.append(AttackSoftware(
                        id=soft_id,
                        stix_id=stix_id,
                        name=name,
                        software_type=obj_type,
                        platforms=platforms,
                        version=version
                    ))
                    valid += 1

                elif obj_type == "course-of-action":
                    ext_refs = obj.get("external_references", [])
                    mit_id = ext_refs[0].get("external_id", stix_id) if ext_refs else stix_id
                    name = obj.get("name", "")
                    desc = obj.get("description", "")
                    version = obj.get("x_mitre_version", "1.0")

                    if not name:
                        missing_fields += 1
                        continue

                    mitigations.append(AttackMitigation(
                        id=mit_id,
                        stix_id=stix_id,
                        name=name,
                        description=desc,
                        version=version
                    ))
                    valid += 1

                elif obj_type == "relationship":
                    src = obj.get("source_ref", "")
                    tgt = obj.get("target_ref", "")
                    rel_type = obj.get("relationship_type", "")
                    desc = obj.get("description", "")

                    if src and tgt and rel_type:
                        relationships.append(AttackRelationship(
                            id=stix_id,
                            source_ref=src,
                            target_ref=tgt,
                            relationship_type=rel_type,
                            description=desc
                        ))
                        valid += 1
                    else:
                        missing_fields += 1
                else:
                    # Other STIX objects (marking-definition, identity, etc.)
                    rejected += 1

            except Exception as e:
                rejected += 1
                issues.append({"stix_id": stix_id, "error": str(e)})

        bundle = AttackBundle(
            tactics=tactics,
            techniques=techniques,
            groups=groups,
            software=software,
            mitigations=mitigations,
            relationships=relationships,
            spec_version=bundle_data.get("spec_version", "2.1")
        )

        report = DataQualityReport(
            source_name="MITRE ATT&CK Enterprise STIX 2.1",
            total_records=total,
            valid_records=valid,
            rejected_records=rejected,
            duplicate_records=0,
            malformed_ids=malformed_ids,
            missing_required_fields=missing_fields,
            deprecated_or_revoked=deprecated_or_revoked,
            unmapped_entities=0,
            conflicting_records=0,
            issues=issues
        )

        return bundle, report
