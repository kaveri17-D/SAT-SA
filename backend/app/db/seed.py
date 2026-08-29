import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models import RuleVersion, ModelVersion, VersionStatus
from app.core.logging import logger

# Baseline Supervisory Baseline Rules (Seed / Reference Data)
BASELINE_RULES = [
    {
        "rule_id": "GAP-01",
        "version": "1.0.0",
        "name": "Critical Alert Closed Without Escalation",
        "definition_json": {
            "category": "EXECUTION_GAP",
            "trigger": "Alert.severity == 'CRITICAL' AND Investigation.outcome == 'CLOSED' AND Escalation == NULL",
            "severity": "CRITICAL",
            "base_risk_contribution": 30.0,
            "description": "Critical severity alert was investigated and closed without an escalation record."
        }
    },
    {
        "rule_id": "GAP-02",
        "version": "1.0.0",
        "name": "High/Critical Alert Missing Investigation",
        "definition_json": {
            "category": "EXECUTION_GAP",
            "trigger": "Alert.severity IN ('CRITICAL', 'HIGH') AND Investigation == NULL",
            "severity": "HIGH",
            "base_risk_contribution": 25.0,
            "description": "High or Critical alert closed or abandoned without any investigation record."
        }
    },
    {
        "rule_id": "GAP-03",
        "version": "1.0.0",
        "name": "Hasty Investigation Duration Below Baseline",
        "definition_json": {
            "category": "EXECUTION_GAP",
            "trigger": "Investigation.duration_seconds < (PeerBenchmark.investigation_duration_p25 * 0.2)",
            "severity": "MEDIUM",
            "base_risk_contribution": 15.0,
            "description": "Investigation duration was significantly shorter than standard peer operational baseline."
        }
    },
    {
        "rule_id": "GAP-04",
        "version": "1.0.0",
        "name": "Repeated Critical Alerts Without Remediation",
        "definition_json": {
            "category": "EXECUTION_GAP",
            "trigger": "COUNT(Alert.category) > 5 ON Asset WITHIN 7 DAYS AND Evidence.remediation == NULL",
            "severity": "HIGH",
            "base_risk_contribution": 20.0,
            "description": "Recurrent critical alerts on the same asset without evidence of corrective remediation."
        }
    },
    {
        "rule_id": "GAP-05",
        "version": "1.0.0",
        "name": "Closure Disposition Inconsistent with Severity",
        "definition_json": {
            "category": "EXECUTION_GAP",
            "trigger": "Alert.severity == 'CRITICAL' AND Closure.disposition == 'FALSE_POSITIVE' AND Closure.justification == NULL",
            "severity": "HIGH",
            "base_risk_contribution": 20.0,
            "description": "Critical alert closed as False Positive without mandatory detailed examiner justification."
        }
    },
    {
        "rule_id": "GAP-06",
        "version": "1.0.0",
        "name": "Expected Escalation Workflow Transition Missing",
        "definition_json": {
            "category": "EXECUTION_GAP",
            "trigger": "Case.status == 'CLOSED' AND Case.type IN ('RANSOMWARE', 'DATA_EXFIL') AND Escalation == NULL",
            "severity": "CRITICAL",
            "base_risk_contribution": 30.0,
            "description": "High-impact security incident case closed without mandatory escalation workflow transition."
        }
    },
    {
        "rule_id": "NEG-01",
        "version": "1.0.0",
        "name": "Critical Asset Telemetry & Activity Absence",
        "definition_json": {
            "category": "NEGATIVE_SPACE",
            "trigger": "Asset.criticality == 'CRITICAL' AND Asset.status == 'ACTIVE' AND COUNT(Alerts/Telemetry) == 0 WITHIN 30 DAYS",
            "severity": "CRITICAL",
            "base_risk_contribution": 25.0,
            "description": "Active critical sector asset has unexpectedly zero operational evidence or telemetry recorded."
        }
    },
    {
        "rule_id": "NEG-02",
        "version": "1.0.0",
        "name": "Sudden Monitoring Blind Spot & Silence Window",
        "definition_json": {
            "category": "NEGATIVE_SPACE",
            "trigger": "Asset.historical_daily_alerts > 10 AND CurrentPeriodAlerts == 0 AND MaintenanceLog == NULL",
            "severity": "HIGH",
            "base_risk_contribution": 20.0,
            "description": "Sudden unannounced collapse in alert stream for monitored asset without logged maintenance window."
        }
    },
    {
        "rule_id": "PEER-01",
        "version": "1.0.0",
        "name": "Peer-Relative Escalation Rate Deviation",
        "definition_json": {
            "category": "PEER_DEVIATION",
            "trigger": "CSE.escalation_rate < (PeerBenchmark.escalation_rate_p25 - 2.0 * PeerBenchmark.std_dev)",
            "severity": "HIGH",
            "base_risk_contribution": 20.0,
            "description": "CSE's escalation rate is significantly lower than peer baseline for similar sector and scale."
        }
    }
]

BASELINE_MODELS = [
    {
        "model_name": "IFOREST_ANOMALY",
        "version": "1.0.0",
        "training_dataset_ref": "SYNTHETIC_GROUND_TRUTH_V1",
        "metrics_json": {"contamination": 0.05, "n_estimators": 100, "random_state": 42},
        "packaged_path": "models/iforest_v1.0.0.joblib"
    },
    {
        "model_name": "KMEANS_PEER",
        "version": "1.0.0",
        "training_dataset_ref": "SYNTHETIC_GROUND_TRUTH_V1",
        "metrics_json": {"n_clusters": 4, "random_state": 42},
        "packaged_path": "models/kmeans_peer_v1.0.0.joblib"
    }
]


def seed_baseline_reference_data(db: Session):
    """Seed system baseline rule and model version records into database."""
    logger.info("Seeding SAT-SA supervisory reference rule versions...")
    
    for rule_data in BASELINE_RULES:
        existing = db.query(RuleVersion).filter(
            RuleVersion.rule_id == rule_data["rule_id"],
            RuleVersion.version == rule_data["version"]
        ).first()
        if not existing:
            rule = RuleVersion(
                rule_id=rule_data["rule_id"],
                version=rule_data["version"],
                name=rule_data["name"],
                definition_json=rule_data["definition_json"],
                status=VersionStatus.ACTIVE,
                created_by="SYSTEM_SEED"
            )
            db.add(rule)
            
    logger.info("Seeding SAT-SA supervisory reference model versions...")
    for model_data in BASELINE_MODELS:
        existing = db.query(ModelVersion).filter(
            ModelVersion.model_name == model_data["model_name"],
            ModelVersion.version == model_data["version"]
        ).first()
        if not existing:
            model = ModelVersion(
                model_name=model_data["model_name"],
                version=model_data["version"],
                training_dataset_ref=model_data["training_dataset_ref"],
                metrics_json=model_data["metrics_json"],
                status=VersionStatus.ACTIVE,
                packaged_path=model_data["packaged_path"]
            )
            db.add(model)
            
    db.commit()
    logger.info("Baseline reference seeding complete.")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_baseline_reference_data(db)
    finally:
        db.close()
