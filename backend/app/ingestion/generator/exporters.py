import json
import os
import pandas as pd
from typing import Dict, Any


def export_dataset_to_csv(data: Dict[str, Any], output_dir: str):
    """Export generated dataset entities into clean CSV and JSON ground-truth files."""
    os.makedirs(output_dir, exist_ok=True)

    # 1. Export CSEs
    cses_df = pd.DataFrame([{
        "id": str(c.id),
        "name": c.name,
        "sector": c.sector,
        "entity_type": c.entity_type,
        "size_tier": c.size_tier,
        "metadata_json": json.dumps(c.metadata_json)
    } for c in data["cses"]])
    cses_df.to_csv(os.path.join(output_dir, "cses.csv"), index=False)

    # 2. Export Assets
    assets_df = pd.DataFrame([{
        "id": str(a.id),
        "cse_id": str(a.cse_id),
        "name": a.name,
        "asset_type": a.asset_type,
        "criticality": a.criticality.value if hasattr(a.criticality, 'value') else str(a.criticality),
        "status": a.status,
        "decommissioned_at": a.decommissioned_at.isoformat() if a.decommissioned_at else ""
    } for a in data["assets"]])
    assets_df.to_csv(os.path.join(output_dir, "assets.csv"), index=False)

    # 3. Export Analysts
    analysts_df = pd.DataFrame([{
        "id": str(an.id),
        "cse_id": str(an.cse_id),
        "handle": an.handle,
        "role": an.role
    } for an in data["analysts"]])
    analysts_df.to_csv(os.path.join(output_dir, "analysts.csv"), index=False)

    # 4. Export Alerts
    alerts_df = pd.DataFrame([{
        "id": str(alt.id),
        "cse_id": str(alt.cse_id),
        "asset_id": str(alt.asset_id),
        "source_system": alt.source_system,
        "category": alt.category,
        "severity": alt.severity.value if hasattr(alt.severity, 'value') else str(alt.severity),
        "raw_severity": alt.raw_severity,
        "status": alt.status,
        "created_at": alt.created_at.isoformat()
    } for alt in data["alerts"]])
    alerts_df.to_csv(os.path.join(output_dir, "alerts.csv"), index=False)

    # 5. Export Investigations
    invs_df = pd.DataFrame([{
        "id": str(inv.id),
        "alert_id": str(inv.alert_id),
        "analyst_id": str(inv.analyst_id) if inv.analyst_id else "",
        "started_at": inv.started_at.isoformat(),
        "ended_at": inv.ended_at.isoformat() if inv.ended_at else "",
        "duration_seconds": inv.duration_seconds if inv.duration_seconds is not None else "",
        "notes": inv.notes or "",
        "outcome": inv.outcome or ""
    } for inv in data["investigations"]])
    invs_df.to_csv(os.path.join(output_dir, "investigations.csv"), index=False)

    # 6. Export Escalations
    escs_df = pd.DataFrame([{
        "id": str(esc.id),
        "investigation_id": str(esc.investigation_id),
        "escalated_to": esc.escalated_to,
        "escalated_at": esc.escalated_at.isoformat(),
        "reason": esc.reason or ""
    } for esc in data["escalations"]])
    escs_df.to_csv(os.path.join(output_dir, "escalations.csv"), index=False)

    # 7. Export Cases
    cases_df = pd.DataFrame([{
        "id": str(cs.id),
        "cse_id": str(cs.cse_id),
        "status": cs.status,
        "opened_at": cs.opened_at.isoformat(),
        "closed_at": cs.closed_at.isoformat() if cs.closed_at else ""
    } for cs in data["cases"]])
    cases_df.to_csv(os.path.join(output_dir, "cases.csv"), index=False)

    # 8. Export Closures
    closures_df = pd.DataFrame([{
        "id": str(cl.id),
        "case_id": str(cl.case_id),
        "disposition_type": cl.disposition_type.value if hasattr(cl.disposition_type, 'value') else str(cl.disposition_type),
        "closed_by": cl.closed_by,
        "closed_at": cl.closed_at.isoformat(),
        "justification": cl.justification or ""
    } for cl in data["closures"]])
    closures_df.to_csv(os.path.join(output_dir, "closures.csv"), index=False)

    # 9. Export Maintenance Logs
    maint_df = pd.DataFrame(data["maintenance_logs"])
    maint_df.to_csv(os.path.join(output_dir, "maintenance_logs.csv"), index=False)

    # 10. Export Ground Truth Manifest (Isolated)
    manifest_dict = data["manifest"].to_dict()
    with open(os.path.join(output_dir, "ground_truth.json"), "w", encoding="utf-8") as f:
        json.dump(manifest_dict, f, indent=2)
