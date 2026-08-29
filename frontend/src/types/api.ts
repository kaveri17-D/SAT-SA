export interface HealthStatus {
  status: string;
  service: string;
  environment: string;
  database: string;
  airgap_mode: boolean;
  version: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  role: string;
  user_id: string;
}

export interface DashboardMetrics {
  total_cses: number;
  critical_cses: number;
  total_findings: number;
  critical_findings: number;
  avg_evidence_completeness: number;
  high_priority_reviews: number;
  open_cases: number;
  airgap_status: string;
}

export interface CSEProfile {
  cse_id: string;
  name: string;
  sector: string;
  entity_type: string;
  size_tier: string;
  asset_count: number;
  finding_count: number;
  risk_score: number;
  risk_band: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface QueueItemContributingFactors {
  risk_significance: number;
  finding_severity: number;
  asset_criticality: number;
  evidence_completeness: number;
  evidence_confidence: number;
  novelty: number;
  peer_deviation: number;
  review_urgency: number;
}

export interface QueueItemExplanation {
  rank: number;
  priority_score: number;
  priority_band: string;
  risk_score: number;
  confidence: number;
  evidence_completeness: number;
  severity: string;
  asset_criticality: number;
  contributing_factors: QueueItemContributingFactors;
  factor_weights: Record<string, number>;
  qualifications: string[];
  diversity_note: string;
}

export interface QueueItem {
  queue_item_id: string;
  rank: number;
  priority_score: number;
  priority_band: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  finding_id: string;
  cse_id: string;
  status: 'NEW' | 'IN_REVIEW' | 'ESCALATED' | 'DISMISSED' | 'RESOLVED';
  rationale: string;
  contributing_factors: QueueItemContributingFactors;
  explanation: QueueItemExplanation;
  diversity_notes: string;
  provenance: Record<string, any>;
}

export interface EvidenceRecord {
  evidence_id: string;
  evidence_type: string;
  source_table: string;
  source_record_id: string;
  completeness_score: number;
  confidence_modifier: number;
  payload: Record<string, any>;
}

export interface EvidencePackage {
  finding_id: string;
  cse_id: string;
  asset_id?: string;
  rule_id: string;
  finding_type: string;
  severity: string;
  status: string;
  evidence_completeness: number;
  confidence: number;
  expected_behaviour: string;
  observed_behaviour: string;
  deviation: string;
  records: EvidenceRecord[];
  provenance: Record<string, any>;
}

export interface RiskContribution {
  finding_id: string;
  category: string;
  rule_id: string;
  raw_contribution: number;
  effective_contribution: number;
  confidence: number;
}

export interface RiskScoreDetail {
  cse_id: string;
  raw_score: number;
  normalized_score: number;
  risk_band: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  overall_confidence: number;
  contributions: RiskContribution[];
  explanation: Record<string, any>;
  provenance: Record<string, any>;
}

export interface GraphNode {
  id: string;
  entity_type: string;
  canonical_record_id: string;
  cse_id?: string;
  timestamp?: string;
  status?: string;
  criticality?: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
  timestamp?: string;
  cse_id?: string;
}

export interface GraphData {
  graph_metadata: {
    analysis_run_id?: string;
    created_at?: string;
  };
  metrics: {
    node_count: number;
    edge_count: number;
    weakly_connected_components: number;
    node_type_breakdown: Record<string, number>;
    edge_type_breakdown: Record<string, number>;
    escalation_investigation_ratio: number;
    closure_case_ratio: number;
    orphan_nodes_count: number;
    missing_expected_count: number;
  };
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface MissingTransition {
  from: string;
  to: string;
  reason: string;
}

export interface GraphPathInfo {
  alert_id: string;
  cse_id: string;
  severity: string;
  expected_path: string[];
  observed_sequence: string[];
  missing_transitions: MissingTransition[];
  is_anomalous: boolean;
  temporal_sequence_valid: boolean;
  temporal_violations: string[];
}

export interface GraphAnomaly {
  anomaly_type: string;
  severity: string;
  title: string;
  description: string;
  expected_state: string;
  observed_state: string;
  deviation: string;
  source_node: string;
  cse_id?: string;
  evidence_type: string;
}

export interface AuditLogEntry {
  audit_id: string;
  user_id: string;
  action: string;
  timestamp: string;
  details: Record<string, any>;
}
