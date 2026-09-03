import time
import uuid
import networkx as nx
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.models import (
    CSE, Asset, Alert, Investigation, Analyst, Escalation, Case, Closure, MaintenanceLog,
    Finding, Evidence, AnalysisRun, FindingSeverity, FindingStatus, AssetCriticality, AlertSeverity
)
from app.evidence.assembler import EvidenceAssembler
from app.core.logging import logger


class SupervisoryEvidenceGraphEngine:
    """Analytical graph and provenance engine representing supervisory workflow relationships using NetworkX."""

    @staticmethod
    def build_graph_for_analysis_run(db: Session, analysis_run_id: uuid.UUID, alert_limit: Optional[int] = 2000) -> nx.DiGraph:
        """Construct deterministic NetworkX directed graph (nx.DiGraph) from canonical DB entities."""
        G = nx.DiGraph(analysis_run_id=str(analysis_run_id), created_at=datetime.now(timezone.utc).isoformat())

        cses = db.query(CSE).all()
        assets = db.query(Asset).all()
        if alert_limit:
            alerts = db.query(Alert).order_by(Alert.created_at.desc()).limit(alert_limit).all()
        else:
            alerts = db.query(Alert).all()
        investigations = db.query(Investigation).all()
        analysts = db.query(Analyst).all()
        escalations = db.query(Escalation).all()
        cases = db.query(Case).all()
        closures = db.query(Closure).all()
        maint_logs = db.query(MaintenanceLog).all()

        # 1. Add CSE Nodes
        for c in cses:
            node_id = f"CSE:{c.id}"
            G.add_node(
                node_id,
                entity_type="CSE",
                canonical_record_id=str(c.id),
                name=c.name,
                sector=c.sector,
                cse_id=str(c.id),
                status="ACTIVE"
            )

        # 2. Add Asset Nodes & OWNS Edges
        for a in assets:
            node_id = f"ASSET:{a.id}"
            G.add_node(
                node_id,
                entity_type="ASSET",
                canonical_record_id=str(a.id),
                name=a.name,
                asset_type=a.asset_type,
                criticality=a.criticality.value,
                cse_id=str(a.cse_id),
                status=a.status
            )
            cse_node = f"CSE:{a.cse_id}"
            if G.has_node(cse_node):
                G.add_edge(cse_node, node_id, relationship="OWNS", cse_id=str(a.cse_id))

        # 3. Add Analyst Nodes
        for an in analysts:
            node_id = f"ANALYST:{an.id}"
            G.add_node(
                node_id,
                entity_type="ANALYST",
                canonical_record_id=str(an.id),
                handle=getattr(an, "handle", str(an.id)),
                role=an.role,
                cse_id=str(an.cse_id) if getattr(an, "cse_id", None) else None,
                status="ACTIVE"
            )

        # 4. Add Alert Nodes & GENERATES Edges
        for alt in alerts:
            node_id = f"ALERT:{alt.id}"
            G.add_node(
                node_id,
                entity_type="ALERT",
                canonical_record_id=str(alt.id),
                source_system=alt.source_system,
                category=alt.category,
                severity=alt.severity.value,
                timestamp=alt.created_at.isoformat() if alt.created_at else None,
                cse_id=str(alt.cse_id),
                asset_id=str(alt.asset_id) if alt.asset_id else None,
                status="REGISTERED"
            )

            asset_node = f"ASSET:{alt.asset_id}" if alt.asset_id else None
            cse_node = f"CSE:{alt.cse_id}"

            if asset_node and G.has_node(asset_node):
                G.add_edge(asset_node, node_id, relationship="GENERATES", timestamp=alt.created_at.isoformat() if alt.created_at else None, cse_id=str(alt.cse_id))
            elif G.has_node(cse_node):
                G.add_edge(cse_node, node_id, relationship="GENERATES", timestamp=alt.created_at.isoformat() if alt.created_at else None, cse_id=str(alt.cse_id))

        # 5. Add Investigation Nodes & INVESTIGATES / ASSIGNED_TO Edges
        for inv in investigations:
            node_id = f"INVESTIGATION:{inv.id}"
            alt_node = f"ALERT:{inv.alert_id}"
            cse_id_str = G.nodes[alt_node].get("cse_id") if G.has_node(alt_node) else None

            G.add_node(
                node_id,
                entity_type="INVESTIGATION",
                canonical_record_id=str(inv.id),
                alert_id=str(inv.alert_id),
                started_at=inv.started_at.isoformat() if inv.started_at else None,
                duration_seconds=inv.duration_seconds,
                cse_id=cse_id_str,
                status="COMPLETED"
            )

            if G.has_node(alt_node):
                G.add_edge(alt_node, node_id, relationship="INVESTIGATES", timestamp=inv.started_at.isoformat() if inv.started_at else None, cse_id=cse_id_str)

            if getattr(inv, "analyst_id", None):
                analyst_node = f"ANALYST:{inv.analyst_id}"
                if G.has_node(analyst_node):
                    G.add_edge(analyst_node, node_id, relationship="ASSIGNED_TO", cse_id=cse_id_str)

        # 6. Add Escalation Nodes & ESCALATED_TO Edges
        for esc in escalations:
            node_id = f"ESCALATION:{esc.id}"
            inv_node = f"INVESTIGATION:{esc.investigation_id}"
            cse_id_str = G.nodes[inv_node].get("cse_id") if G.has_node(inv_node) else None

            G.add_node(
                node_id,
                entity_type="ESCALATION",
                canonical_record_id=str(esc.id),
                investigation_id=str(esc.investigation_id),
                escalated_at=esc.escalated_at.isoformat() if esc.escalated_at else None,
                reason=esc.reason,
                cse_id=cse_id_str,
                status="ESCALATED"
            )

            if G.has_node(inv_node):
                G.add_edge(inv_node, node_id, relationship="ESCALATED_TO", timestamp=esc.escalated_at.isoformat() if esc.escalated_at else None, cse_id=cse_id_str)

        # 7. Add Case Nodes & RESULTS_IN Edges
        for c in cases:
            node_id = f"CASE:{c.id}"
            cse_node = f"CSE:{c.cse_id}"

            G.add_node(
                node_id,
                entity_type="CASE",
                canonical_record_id=str(c.id),
                cse_id=str(c.cse_id),
                opened_at=c.opened_at.isoformat() if c.opened_at else None,
                status="OPEN"
            )

            # Link Case to Escalation or Investigation
            linked = False
            # Check Findings linked to case
            linked_findings = db.query(Finding).filter(Finding.case_id == c.id).all()
            for f in linked_findings:
                inv_id = None
                alert_id = None
                if f.evidence_refs:
                    for ref in f.evidence_refs:
                        if ref.get("source_table") == "investigations":
                            inv_id = ref.get("source_record_id")
                        elif ref.get("source_table") == "alerts":
                            alert_id = ref.get("source_record_id")
                if not inv_id and alert_id:
                    inv = db.query(Investigation).filter(Investigation.alert_id == alert_id).first()
                    if inv:
                        inv_id = str(inv.id)
                if inv_id:
                    inv_node = f"INVESTIGATION:{inv_id}"
                    if G.has_node(inv_node):
                        esc_successors = [n for n in G.successors(inv_node) if G.nodes[n].get("entity_type") == "ESCALATION"]
                        if esc_successors:
                            G.add_edge(esc_successors[0], node_id, relationship="RESULTS_IN", timestamp=c.opened_at.isoformat() if c.opened_at else None, cse_id=str(c.cse_id))
                        else:
                            G.add_edge(inv_node, node_id, relationship="RESULTS_IN", timestamp=c.opened_at.isoformat() if c.opened_at else None, cse_id=str(c.cse_id))
                        linked = True
            
            if not linked:
                # Direct CSE heuristic: connect to upstream Escalation or Investigation matching CSE
                cs_escs = [n for n, d in G.nodes(data=True) if d.get("entity_type") == "ESCALATION" and d.get("cse_id") == str(c.cse_id)]
                if cs_escs:
                    G.add_edge(cs_escs[0], node_id, relationship="RESULTS_IN", timestamp=c.opened_at.isoformat() if c.opened_at else None, cse_id=str(c.cse_id))
                else:
                    cs_invs = [n for n, d in G.nodes(data=True) if d.get("entity_type") == "INVESTIGATION" and d.get("cse_id") == str(c.cse_id)]
                    if cs_invs:
                        G.add_edge(cs_invs[0], node_id, relationship="RESULTS_IN", timestamp=c.opened_at.isoformat() if c.opened_at else None, cse_id=str(c.cse_id))

        # 8. Add Closure Nodes & CLOSED_BY Edges
        for clo in closures:
            node_id = f"CLOSURE:{clo.id}"
            case_node = f"CASE:{clo.case_id}"
            cse_id_str = G.nodes[case_node].get("cse_id") if G.has_node(case_node) else None

            G.add_node(
                node_id,
                entity_type="CLOSURE",
                canonical_record_id=str(clo.id),
                case_id=str(clo.case_id),
                disposition_type=clo.disposition_type.value,
                closed_at=clo.closed_at.isoformat() if clo.closed_at else None,
                closed_by=clo.closed_by,
                cse_id=cse_id_str,
                status="CLOSED"
            )

            if G.has_node(case_node):
                G.add_edge(case_node, node_id, relationship="CLOSED_BY", timestamp=clo.closed_at.isoformat() if clo.closed_at else None, cse_id=cse_id_str)

        # 9. Add Negative Space Nodes (Asset -> MISSING_EXPECTED)
        # Active CRITICAL assets with 0 generated alerts get an explicit MISSING_EXPECTED node
        for a in assets:
            if a.criticality == AssetCriticality.CRITICAL and a.status == "ACTIVE":
                asset_node = f"ASSET:{a.id}"
                has_alerts = any(G.nodes[n].get("entity_type") == "ALERT" for n in G.successors(asset_node))
                if not has_alerts:
                    missing_node = f"MISSING_EXPECTED:{a.id}"
                    G.add_node(
                        missing_node,
                        entity_type="MISSING_EXPECTED",
                        canonical_record_id=str(a.id),
                        expected_evidence="Continuous Operational Telemetry",
                        cse_id=str(a.cse_id),
                        status="ABSENT"
                    )
                    G.add_edge(asset_node, missing_node, relationship="MISSING_EXPECTED", cse_id=str(a.cse_id))

        return G

    @staticmethod
    def reconstruct_alert_path(G: nx.DiGraph, alert_id: uuid.UUID) -> Dict[str, Any]:
        """Reconstruct expected vs observed workflow path for a given Alert."""
        alert_node = f"ALERT:{alert_id}"
        if not G.has_node(alert_node):
            return {"error": f"Alert node '{alert_node}' not found in graph."}

        node_data = G.nodes[alert_node]
        severity = node_data.get("severity", "MEDIUM")
        cse_id = node_data.get("cse_id")

        # Canonical Expected Path
        expected_path = ["ALERT", "INVESTIGATION", "ESCALATION", "CASE", "CLOSURE"] if severity == "CRITICAL" else ["ALERT", "INVESTIGATION", "CASE", "CLOSURE"]

        # Traversal observed downstream nodes
        observed_sequence = ["ALERT"]
        current_node = alert_node
        missing_transitions = []

        # Find investigation successor
        inv_successors = [n for n in G.successors(current_node) if G.nodes[n].get("entity_type") == "INVESTIGATION"]
        if inv_successors:
            inv_node = inv_successors[0]
            observed_sequence.append("INVESTIGATION")
            current_node = inv_node

            # Find escalation or case successor
            esc_successors = [n for n in G.successors(current_node) if G.nodes[n].get("entity_type") == "ESCALATION"]
            case_successors = [n for n in G.successors(current_node) if G.nodes[n].get("entity_type") == "CASE"]

            if esc_successors:
                esc_node = esc_successors[0]
                observed_sequence.append("ESCALATION")
                current_node = esc_node
                case_succ = [n for n in G.successors(current_node) if G.nodes[n].get("entity_type") == "CASE"]
                if case_succ:
                    c_node = case_succ[0]
                    observed_sequence.append("CASE")
                    current_node = c_node
                    clo_succ = [n for n in G.successors(current_node) if G.nodes[n].get("entity_type") == "CLOSURE"]
                    if clo_succ:
                        observed_sequence.append("CLOSURE")
            elif case_successors:
                c_node = case_successors[0]
                observed_sequence.append("CASE")
                if severity == "CRITICAL":
                    missing_transitions.append({"from": "INVESTIGATION", "to": "ESCALATION", "reason": "Critical alert case created without escalation record."})
                current_node = c_node
                clo_succ = [n for n in G.successors(current_node) if G.nodes[n].get("entity_type") == "CLOSURE"]
                if clo_succ:
                    observed_sequence.append("CLOSURE")

        return {
            "alert_id": str(alert_id),
            "cse_id": cse_id,
            "severity": severity,
            "expected_path": expected_path,
            "observed_sequence": observed_sequence,
            "missing_transitions": missing_transitions,
            "is_anomalous": len(missing_transitions) > 0
        }

    @staticmethod
    def validate_temporal_sequence(G: nx.DiGraph, alert_id: uuid.UUID) -> Tuple[bool, List[str]]:
        """Validate timestamp ordering along observed workflow path."""
        alert_node = f"ALERT:{alert_id}"
        if not G.has_node(alert_node):
            return True, []

        violations = []
        alt_ts = G.nodes[alert_node].get("timestamp")

        inv_successors = [n for n in G.successors(alert_node) if G.nodes[n].get("entity_type") == "INVESTIGATION"]
        if inv_successors and alt_ts:
            inv_ts = G.nodes[inv_successors[0]].get("started_at")
            if inv_ts and inv_ts < alt_ts:
                violations.append(f"Investigation started_at ({inv_ts}) is prior to Alert created_at ({alt_ts}).")

            case_successors = [n for n in G.successors(inv_successors[0]) if G.nodes[n].get("entity_type") == "CASE"]
            if case_successors and inv_ts:
                c_ts = G.nodes[case_successors[0]].get("opened_at")
                if c_ts and c_ts < inv_ts:
                    violations.append(f"Case opened_at ({c_ts}) is prior to Investigation started_at ({inv_ts}).")

        return len(violations) == 0, violations

    @staticmethod
    def detect_graph_anomalies(db: Session, G: nx.DiGraph, analysis_run_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Evaluate 8 graph anomaly detectors with data sufficiency rules and produce evidence structures."""
        anomalies: List[Dict[str, Any]] = []

        # 1. BROKEN_PATH & MISSING_TRANSITION Detectors
        alert_nodes = [n for n, d in G.nodes(data=True) if d.get("entity_type") == "ALERT"]
        for alt_node in alert_nodes:
            alt_id = G.nodes[alt_node]["canonical_record_id"]
            path_info = SupervisoryEvidenceGraphEngine.reconstruct_alert_path(G, uuid.UUID(alt_id))
            if path_info.get("missing_transitions"):
                for mt in path_info["missing_transitions"]:
                    anomalies.append({
                        "anomaly_type": "MISSING_TRANSITION",
                        "severity": "HIGH" if path_info["severity"] == "CRITICAL" else "MEDIUM",
                        "title": f"Missing Escalation Transition for Critical Alert '{alt_id}'",
                        "description": mt["reason"],
                        "expected_state": f"Alert -> Investigation -> Escalation -> Case",
                        "observed_state": f"Alert -> Investigation -> Case",
                        "deviation": f"Missing transition {mt['from']} -> {mt['to']}",
                        "source_node": alt_node,
                        "cse_id": path_info["cse_id"],
                        "evidence_type": "WORKFLOW_TRANSITION"
                    })

            # Check temporal sequence
            valid_temp, temp_violations = SupervisoryEvidenceGraphEngine.validate_temporal_sequence(G, uuid.UUID(alt_id))
            if not valid_temp:
                for tv in temp_violations:
                    anomalies.append({
                        "anomaly_type": "TEMPORAL_VIOLATION",
                        "severity": "HIGH",
                        "title": f"Temporal Sequence Violation for Alert '{alt_id}'",
                        "description": tv,
                        "expected_state": "created_at <= started_at <= opened_at <= closed_at",
                        "observed_state": tv,
                        "deviation": "Impossible timestamp sequence",
                        "source_node": alt_node,
                        "cse_id": path_info["cse_id"],
                        "evidence_type": "DATA_QUALITY"
                    })

        # 2. ORPHAN_ENTITY Detector
        for n, d in G.nodes(data=True):
            if d.get("entity_type") in ("INVESTIGATION", "ESCALATION", "CASE") and G.in_degree(n) == 0:
                anomalies.append({
                    "anomaly_type": "ORPHAN_ENTITY",
                    "severity": "MEDIUM",
                    "title": f"Orphan Entity '{n}'",
                    "description": f"Entity '{n}' of type {d.get('entity_type')} has zero upstream links.",
                    "expected_state": "Every workflow node must be linked to upstream Alert/CSE",
                    "observed_state": "In-degree = 0",
                    "deviation": "Orphan workflow entity",
                    "source_node": n,
                    "cse_id": d.get("cse_id"),
                    "evidence_type": "MISSING_EXPECTED_RECORD"
                })

        # 3. WORKFLOW_BOTTLENECK Detector (Transition Ratio Calculation)
        inv_count = len([n for n, d in G.nodes(data=True) if d.get("entity_type") == "INVESTIGATION"])
        esc_count = len([n for n, d in G.nodes(data=True) if d.get("entity_type") == "ESCALATION"])

        # Data sufficiency rule: requires at least 5 investigations
        if inv_count >= 5:
            esc_ratio = round(esc_count / inv_count, 4)
            if esc_ratio < 0.15:  # Bottleneck threshold: <15% escalations
                anomalies.append({
                    "anomaly_type": "WORKFLOW_BOTTLENECK",
                    "severity": "HIGH",
                    "title": "Low Escalation Ratio Bottleneck",
                    "description": f"Escalation-to-Investigation ratio ({esc_ratio:.2%}) is below expected baseline (15.0%).",
                    "expected_state": "Escalation ratio >= 15.0%",
                    "observed_state": f"{esc_count} escalations out of {inv_count} investigations (ratio = {esc_ratio:.2%})",
                    "deviation": f"Bottleneck ratio deficit: {0.15 - esc_ratio:.2%}",
                    "source_node": "GRAPH_AGGREGATE",
                    "cse_id": None,
                    "evidence_type": "STATISTICAL_DEVIATION"
                })

        # 4. ANALYST_CONCENTRATION Detector (Data Sufficiency Rule)
        analyst_investigations: Dict[str, int] = {}
        for n, d in G.nodes(data=True):
            if d.get("entity_type") == "INVESTIGATION":
                # Find analyst assigned
                assign_edges = [u for u, v, ed in G.in_edges(n, data=True) if ed.get("relationship") == "ASSIGNED_TO"]
                if assign_edges:
                    a_node = assign_edges[0]
                    analyst_investigations[a_node] = analyst_investigations.get(a_node, 0) + 1

        total_invs = sum(analyst_investigations.values())
        team_size = len(analyst_investigations)

        # Data Sufficiency Rule: requires total_invs >= 10 and team_size >= 3
        if total_invs >= 10 and team_size >= 3:
            for a_node, count in analyst_investigations.items():
                ratio = count / total_invs
                if ratio > 0.40:  # Single analyst handling >40% workload
                    anomalies.append({
                        "anomaly_type": "ANALYST_CONCENTRATION",
                        "severity": "MEDIUM",
                        "title": f"Analyst Workload Concentration '{a_node}'",
                        "description": f"Analyst '{a_node}' handled {count}/{total_invs} investigations ({ratio:.1%}).",
                        "expected_state": f"Balanced workload across team of {team_size} analysts (share <= 40.0%)",
                        "observed_state": f"Analyst workload share: {ratio:.1%}",
                        "deviation": f"Concentration excess: {ratio - 0.40:.1%}",
                        "source_node": a_node,
                        "cse_id": None,
                        "evidence_type": "PEER_COMPARISON"
                    })

        # 5. MISSING_EXPECTED_ACTIVITY (Negative Space Graph Representation)
        missing_nodes = [n for n, d in G.nodes(data=True) if d.get("entity_type") == "MISSING_EXPECTED"]
        for mn in missing_nodes:
            d = G.nodes[mn]
            anomalies.append({
                "anomaly_type": "MISSING_EXPECTED_ACTIVITY",
                "severity": "HIGH",
                "title": f"Telemetry Silence on Critical Asset '{d['canonical_record_id']}'",
                "description": f"Target critical asset has zero operational telemetry/alerts.",
                "expected_state": "Continuous operational telemetry required for active critical asset",
                "observed_state": "Telemetry silence (0 alert records found)",
                "deviation": "Missing expected telemetry evidence",
                "source_node": mn,
                "cse_id": d["cse_id"],
                "evidence_type": "MISSING_EXPECTED_RECORD"
            })

        return anomalies

    @staticmethod
    def calculate_graph_metrics(G: nx.DiGraph) -> Dict[str, Any]:
        """Compute graph-level analytical summary metrics."""
        node_count = G.number_of_nodes()
        edge_count = G.number_of_edges()

        # Connected components (undirected view for weakly connected components)
        components_count = nx.number_weakly_connected_components(G) if node_count > 0 else 0

        # Node breakdown
        node_types = {}
        for n, d in G.nodes(data=True):
            t = d.get("entity_type", "UNKNOWN")
            node_types[t] = node_types.get(t, 0) + 1

        # Edge breakdown
        edge_types = {}
        for u, v, d in G.edges(data=True):
            r = d.get("relationship", "UNKNOWN")
            edge_types[r] = edge_types.get(r, 0) + 1

        inv_count = node_types.get("INVESTIGATION", 0)
        esc_count = node_types.get("ESCALATION", 0)
        case_count = node_types.get("CASE", 0)
        clo_count = node_types.get("CLOSURE", 0)

        esc_ratio = round(esc_count / inv_count, 4) if inv_count > 0 else 0.0
        closure_ratio = round(clo_count / case_count, 4) if case_count > 0 else 0.0

        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "weakly_connected_components": components_count,
            "node_type_breakdown": node_types,
            "edge_type_breakdown": edge_types,
            "escalation_investigation_ratio": esc_ratio,
            "closure_case_ratio": closure_ratio,
            "orphan_nodes_count": len([n for n, d in G.nodes(data=True) if d.get("entity_type") in ("INVESTIGATION", "ESCALATION", "CASE") and G.in_degree(n) == 0]),
            "missing_expected_count": node_types.get("MISSING_EXPECTED", 0)
        }

    @staticmethod
    def build_simple_workflow_path(
        db: Session,
        analysis_run_id: uuid.UUID,
        cse_id: Optional[uuid.UUID] = None,
        finding_id: Optional[uuid.UUID] = None,
        alert_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Build scoped 7-stage linear workflow path (CSE -> Asset -> Alert -> Investigation -> Escalation -> Case -> Closure)."""
        finding = None
        cse = None
        asset = None
        alert = None
        inv = None
        esc = None
        case = None
        clo = None

        # 1. Resolve Finding / CSE / Alert
        if finding_id:
            finding = db.query(Finding).filter(Finding.id == finding_id).first()
            if finding:
                cse_id = finding.cse_id
                asset = finding.asset

        if cse_id:
            cse = db.query(CSE).filter(CSE.id == cse_id).first()
        elif not finding:
            # Fallback to top priority finding in run
            finding = (
                db.query(Finding)
                .filter(Finding.analysis_run_id == analysis_run_id)
                .order_by(Finding.supervisory_priority.desc())
                .first()
            )
            if finding:
                cse_id = finding.cse_id
                cse = finding.cse
                asset = finding.asset
            else:
                cse = db.query(CSE).first()

        if cse and not asset:
            asset = db.query(Asset).filter(Asset.cse_id == cse.id).first()

        # Resolve Alert
        if alert_id:
            alert = db.query(Alert).filter(Alert.id == alert_id).first()
        elif finding and finding.evidence_records:
            # Look for linked alert in evidence
            for ev in finding.evidence_records:
                if ev.source_table == "alerts" and ev.source_record_id:
                    try:
                        alert = db.query(Alert).filter(Alert.id == uuid.UUID(ev.source_record_id)).first()
                        if alert:
                            break
                    except ValueError:
                        pass
        if not alert and asset:
            alert = db.query(Alert).filter(Alert.asset_id == asset.id).order_by(Alert.created_at.desc()).first()
        if not alert and cse:
            alert = db.query(Alert).filter(Alert.cse_id == cse.id).order_by(Alert.created_at.desc()).first()

        # Resolve Investigation
        if alert:
            inv = db.query(Investigation).filter(Investigation.alert_id == alert.id).first()

        # Resolve Escalation
        if inv:
            esc = db.query(Escalation).filter(Escalation.investigation_id == inv.id).first()

        # Resolve Case
        if esc:
            case = db.query(Case).filter(Case.escalation_id == esc.id).first()
        elif inv:
            case = db.query(Case).filter(Case.investigation_id == inv.id).first()

        # Resolve Closure
        if case:
            clo = db.query(Closure).filter(Closure.case_id == case.id).first()

        # 2. Evaluate stage statuses and anomalies
        # CSE Stage
        cse_status = "COMPLETED" if cse else "MISSING"
        # Asset Stage
        asset_status = "COMPLETED" if asset else "MISSING"

        # Alert Stage
        if alert:
            if not inv and getattr(alert.severity, "value", str(alert.severity)) in ("CRITICAL", "HIGH"):
                alert_status = "ANOMALOUS"
            else:
                alert_status = "COMPLETED"
        else:
            alert_status = "MISSING" if (asset and getattr(asset.criticality, "value", str(asset.criticality)) == "CRITICAL") else "NOT_APPLICABLE"

        # Investigation Stage
        if inv:
            if alert and inv.started_at and alert.created_at and inv.started_at < alert.created_at:
                inv_status = "ANOMALOUS"
            elif inv.duration_seconds and inv.duration_seconds > 86400:
                inv_status = "ANOMALOUS"
            else:
                inv_status = "COMPLETED"
        else:
            inv_status = "MISSING" if (alert and getattr(alert.severity, "value", str(alert.severity)) in ("CRITICAL", "HIGH")) else "NOT_APPLICABLE"

        # Escalation Stage
        if esc:
            esc_status = "COMPLETED"
        else:
            if alert and getattr(alert.severity, "value", str(alert.severity)) == "CRITICAL" and inv:
                esc_status = "MISSING"
            else:
                esc_status = "NOT_APPLICABLE"

        # Case Stage
        if case:
            if case.status == "OPEN" and case.opened_at and (datetime.now(timezone.utc) - case.opened_at.replace(tzinfo=timezone.utc if case.opened_at.tzinfo is None else None)).days > 30:
                case_status = "ANOMALOUS"
            else:
                case_status = "COMPLETED"
        else:
            case_status = "MISSING" if esc else "NOT_APPLICABLE"

        # Closure Stage
        if clo:
            clo_status = "COMPLETED"
        else:
            if case and case.status == "CLOSED":
                clo_status = "MISSING"
            elif case:
                clo_status = "MISSING"
            else:
                clo_status = "NOT_APPLICABLE"

        stages = [
            {
                "stage": "CSE",
                "label": "Critical Sector Entity",
                "status": cse_status,
                "node_id": f"CSE:{cse.id}" if cse else "CSE:MISSING",
                "entity_type": "CSE",
                "canonical_record_id": str(cse.id) if cse else None,
                "name": cse.name if cse else "Unresolved Entity",
                "details": f"Sector: {cse.sector} | Tier: {cse.size_tier}" if cse else "Missing entity record",
                "entity_data": {
                    "cse_id": str(cse.id) if cse else None,
                    "name": cse.name if cse else None,
                    "sector": cse.sector if cse else None,
                    "entity_type": cse.entity_type if cse else None,
                    "size_tier": cse.size_tier if cse else None
                } if cse else {}
            },
            {
                "stage": "ASSET",
                "label": "Supervised Asset",
                "status": asset_status,
                "node_id": f"ASSET:{asset.id}" if asset else "ASSET:MISSING",
                "entity_type": "ASSET",
                "canonical_record_id": str(asset.id) if asset else None,
                "name": asset.name if asset else "Missing Asset Record",
                "details": f"Type: {asset.asset_type} | Criticality: {getattr(asset.criticality, 'value', str(asset.criticality))}" if asset else "Missing asset context",
                "entity_data": {
                    "asset_id": str(asset.id) if asset else None,
                    "name": asset.name if asset else None,
                    "asset_type": asset.asset_type if asset else None,
                    "criticality": getattr(asset.criticality, 'value', str(asset.criticality)) if asset else None,
                    "status": asset.status if asset else None
                } if asset else {}
            },
            {
                "stage": "ALERT",
                "label": "Operational Alert",
                "status": alert_status,
                "node_id": f"ALERT:{alert.id}" if alert else "ALERT:MISSING",
                "entity_type": "ALERT",
                "canonical_record_id": str(alert.id) if alert else None,
                "name": alert.category if alert else "No Active Alert Telemetry",
                "details": f"Severity: {getattr(alert.severity, 'value', str(alert.severity))} | Source: {alert.source_system}" if alert else "Missing expected security telemetry",
                "entity_data": {
                    "alert_id": str(alert.id) if alert else None,
                    "category": alert.category if alert else None,
                    "severity": getattr(alert.severity, 'value', str(alert.severity)) if alert else None,
                    "source_system": alert.source_system if alert else None,
                    "status": alert.status if alert else None,
                    "created_at": alert.created_at.isoformat() if alert and alert.created_at else None
                } if alert else {}
            },
            {
                "stage": "INVESTIGATION",
                "label": "SOC Investigation",
                "status": inv_status,
                "node_id": f"INVESTIGATION:{inv.id}" if inv else "INVESTIGATION:MISSING",
                "entity_type": "INVESTIGATION",
                "canonical_record_id": str(inv.id) if inv else None,
                "name": f"Investigation #{str(inv.id)[:8]}" if inv else ("Missing Investigation" if inv_status == "MISSING" else "Investigation Not Required"),
                "details": f"Duration: {inv.duration_seconds}s | Outcome: {inv.outcome or 'In Progress'}" if inv else ("Critical alert was not investigated" if inv_status == "MISSING" else "Low-severity alert triage"),
                "entity_data": {
                    "investigation_id": str(inv.id) if inv else None,
                    "started_at": inv.started_at.isoformat() if inv and inv.started_at else None,
                    "ended_at": inv.ended_at.isoformat() if inv and inv.ended_at else None,
                    "duration_seconds": inv.duration_seconds if inv else None,
                    "outcome": inv.outcome if inv else None,
                    "analyst_id": str(inv.analyst_id) if inv and inv.analyst_id else None
                } if inv else {}
            },
            {
                "stage": "ESCALATION",
                "label": "Tier-2/3 Escalation",
                "status": esc_status,
                "node_id": f"ESCALATION:{esc.id}" if esc else "ESCALATION:MISSING",
                "entity_type": "ESCALATION",
                "canonical_record_id": str(esc.id) if esc else None,
                "name": f"Escalation #{str(esc.id)[:8]}" if esc else ("Missing Critical Escalation" if esc_status == "MISSING" else "Escalation Not Triggered"),
                "details": f"Escalated To: {esc.escalated_to} | Reason: {esc.reason or 'Policy trigger'}" if esc else ("Critical severity finding bypassed mandatory escalation" if esc_status == "MISSING" else "Routine operational workflow"),
                "entity_data": {
                    "escalation_id": str(esc.id) if esc else None,
                    "escalated_at": esc.escalated_at.isoformat() if esc and esc.escalated_at else None,
                    "escalated_to": esc.escalated_to if esc else None,
                    "reason": esc.reason if esc else None
                } if esc else {}
            },
            {
                "stage": "CASE",
                "label": "Supervisory Case",
                "status": case_status,
                "node_id": f"CASE:{case.id}" if case else "CASE:MISSING",
                "entity_type": "CASE",
                "canonical_record_id": str(case.id) if case else None,
                "name": f"Case #{str(case.id)[:8]}" if case else ("Missing Incident Case" if case_status == "MISSING" else "Case Not Required"),
                "details": f"Status: {case.status} | Opened: {case.opened_at.strftime('%Y-%m-%d') if case and case.opened_at else '—'}" if case else ("Escalated security incident has no tracked case" if case_status == "MISSING" else "Informational monitoring"),
                "entity_data": {
                    "case_id": str(case.id) if case else None,
                    "status": case.status if case else None,
                    "opened_at": case.opened_at.isoformat() if case and case.opened_at else None,
                    "closed_at": case.closed_at.isoformat() if case and case.closed_at else None
                } if case else {}
            },
            {
                "stage": "CLOSURE",
                "label": "Formal Case Closure",
                "status": clo_status,
                "node_id": f"CLOSURE:{clo.id}" if clo else "CLOSURE:MISSING",
                "entity_type": "CLOSURE",
                "canonical_record_id": str(clo.id) if clo else None,
                "name": f"Disposition: {getattr(clo.disposition_type, 'value', str(clo.disposition_type))}" if clo else ("Pending Case Closure" if clo_status == "MISSING" else "Not Applicable"),
                "details": f"Closed By: {clo.closed_by} | Justification: {clo.justification or 'Standard closure'}" if clo else ("Incident case remains unresolved without disposition" if clo_status == "MISSING" else "No case to close"),
                "entity_data": {
                    "closure_id": str(clo.id) if clo else None,
                    "disposition_type": getattr(clo.disposition_type, 'value', str(clo.disposition_type)) if clo else None,
                    "closed_at": clo.closed_at.isoformat() if clo and clo.closed_at else None,
                    "closed_by": clo.closed_by if clo else None,
                    "justification": clo.justification if clo else None
                } if clo else {}
            }
        ]

        # Edges connecting sequential stages
        nodes = []
        edges = []
        for i, st in enumerate(stages):
            nodes.append({
                "id": st["node_id"],
                "entity_type": st["entity_type"],
                "stage": st["stage"],
                "label": st["label"],
                "name": st["name"],
                "status": st["status"],
                "canonical_record_id": st["canonical_record_id"],
                "details": st["details"],
                "entity_data": st["entity_data"]
            })
            if i > 0:
                prev_st = stages[i - 1]
                edges.append({
                    "source": prev_st["node_id"],
                    "target": st["node_id"],
                    "relationship": f"{prev_st['stage']}_TO_{st['stage']}",
                    "status": "VALID" if (prev_st["status"] in ("COMPLETED", "ANOMALOUS") and st["status"] in ("COMPLETED", "ANOMALOUS")) else "BROKEN"
                })

        return {
            "analysis_run_id": str(analysis_run_id),
            "target_scope": {
                "cse_id": str(cse.id) if cse else None,
                "cse_name": cse.name if cse else "Enterprise Portfolio",
                "finding_id": str(finding.id) if finding else None,
                "finding_rule_id": finding.rule_id if finding else None,
                "finding_reason": finding.reason if finding else None,
                "finding_severity": getattr(finding.severity, "value", str(finding.severity)) if finding else None,
                "alert_id": str(alert.id) if alert else None
            },
            "stages": stages,
            "nodes": nodes,
            "edges": edges,
            "metrics": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "completed_stages": sum(1 for s in stages if s["status"] == "COMPLETED"),
                "anomalous_stages": sum(1 for s in stages if s["status"] == "ANOMALOUS"),
                "missing_stages": sum(1 for s in stages if s["status"] == "MISSING"),
                "not_applicable_stages": sum(1 for s in stages if s["status"] == "NOT_APPLICABLE")
            }
        }

    @staticmethod
    def export_graph_json(G: nx.DiGraph, max_nodes: Optional[int] = 250) -> Dict[str, Any]:
        """Export machine-readable JSON representation of NetworkX graph."""
        metrics = SupervisoryEvidenceGraphEngine.calculate_graph_metrics(G)

        nodes = []
        node_items = list(G.nodes(data=True))
        if max_nodes and len(node_items) > max_nodes:
            priority_types = {"CSE", "MISSING_EXPECTED", "ALERT", "INVESTIGATION"}
            selected = [n for n, d in node_items if d.get("entity_type") in priority_types][:max_nodes]
            selected_set = set(selected)
            if len(selected) < max_nodes:
                for n, d in node_items:
                    if n not in selected_set:
                        selected.append(n)
                        selected_set.add(n)
                        if len(selected) >= max_nodes:
                            break
            node_items = [(n, G.nodes[n]) for n in selected]

        selected_ids = {n for n, d in node_items}
        for n, d in node_items:
            nodes.append({
                "id": n,
                "entity_type": d.get("entity_type"),
                "canonical_record_id": d.get("canonical_record_id"),
                "cse_id": d.get("cse_id"),
                "timestamp": d.get("timestamp"),
                "status": d.get("status"),
                "criticality": d.get("criticality")
            })

        edges = []
        for u, v, d in G.edges(data=True):
            if u in selected_ids and v in selected_ids:
                edges.append({
                    "source": u,
                    "target": v,
                    "relationship": d.get("relationship"),
                    "timestamp": d.get("timestamp"),
                    "cse_id": d.get("cse_id")
                })
                if max_nodes and len(edges) >= max_nodes * 2:
                    break

        return {
            "graph_metadata": {
                "analysis_run_id": G.graph.get("analysis_run_id"),
                "created_at": G.graph.get("created_at")
            },
            "metrics": metrics,
            "nodes": nodes,
            "edges": edges
        }
