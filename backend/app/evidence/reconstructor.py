from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import uuid
from app.models import CSE, Asset, Alert, Investigation, Analyst, Escalation, Case, Closure


@dataclass
class OperationalWorkflowNode:
    """Canonical workflow chain node representing an alert's lifecycle."""
    alert: Alert
    asset: Optional[Asset] = None
    cse: Optional[CSE] = None
    investigation: Optional[Investigation] = None
    analyst: Optional[Analyst] = None
    escalation: Optional[Escalation] = None
    case: Optional[Case] = None
    closure: Optional[Closure] = None

    @property
    def has_investigation(self) -> bool:
        return self.investigation is not None

    @property
    def has_escalation(self) -> bool:
        return self.escalation is not None

    @property
    def has_case(self) -> bool:
        return self.case is not None

    @property
    def has_closure(self) -> bool:
        return self.closure is not None

    def to_evidence_refs(self) -> List[Dict[str, str]]:
        """Construct canonical evidence references for findings."""
        refs = [
            {"source_table": "alerts", "source_record_id": str(self.alert.id), "description": f"Alert {self.alert.category} ({self.alert.severity.value})"}
        ]
        if self.asset:
            refs.append({"source_table": "assets", "source_record_id": str(self.asset.id), "description": f"Asset {self.asset.name} ({self.asset.criticality.value})"})
        if self.investigation:
            refs.append({"source_table": "investigations", "source_record_id": str(self.investigation.id), "description": f"Investigation (duration: {self.investigation.duration_seconds}s)"})
        if self.escalation:
            refs.append({"source_table": "escalations", "source_record_id": str(self.escalation.id), "description": f"Escalation to {self.escalation.escalated_to}"})
        if self.case:
            refs.append({"source_table": "cases", "source_record_id": str(self.case.id), "description": f"Case {self.case.id}"})
        if self.closure:
            refs.append({"source_table": "closures", "source_record_id": str(self.closure.id), "description": f"Closure disposition {self.closure.disposition_type.value}"})
        return refs


class WorkflowReconstructor:
    """Reconstructs operational workflows from canonical database records."""

    @staticmethod
    def reconstruct_for_alerts(alerts: List[Alert]) -> List[OperationalWorkflowNode]:
        """Build workflow chains for a list of canonical Alert objects."""
        nodes = []
        for alert in alerts:
            node = OperationalWorkflowNode(
                alert=alert,
                asset=alert.asset,
                cse=alert.cse,
                investigation=alert.investigation
            )
            if node.investigation:
                node.analyst = node.investigation.analyst
                node.escalation = node.investigation.escalation
            
            # Find linked cases via CSE/alert matching if any
            if alert.cse and alert.cse.cases:
                # Find case opened within +/- 1 hour of alert/escalation
                for case in alert.cse.cases:
                    if abs((case.opened_at - alert.created_at).total_seconds()) < 86400:
                        node.case = case
                        node.closure = case.closure
                        break

            nodes.append(node)
        return nodes
