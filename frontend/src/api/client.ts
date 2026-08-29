import {
  HealthStatus,
  DashboardMetrics,
  CSEProfile,
  QueueItem,
  EvidencePackage,
  RiskScoreDetail,
  GraphData,
  GraphPathInfo,
  GraphAnomaly,
  AuditLogEntry
} from '../types/api';

const API_BASE = '/api/v1';

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed (${res.status})`);
  return res.json();
}

export async function fetchDashboardMetrics(): Promise<DashboardMetrics> {
  const res = await fetch(`${API_BASE}/prioritization/metrics/latest`);
  if (!res.ok) throw new Error(`Failed to fetch dashboard metrics (${res.status})`);
  return res.json();
}

export async function fetchCSEProfiles(): Promise<CSEProfile[]> {
  const res = await fetch(`${API_BASE}/prioritization/cses`);
  if (!res.ok) throw new Error(`Failed to fetch CSE profiles (${res.status})`);
  return res.json();
}

export async function fetchReviewQueue(analysisRunId = 'latest'): Promise<{
  analysis_run_id: string;
  queue_count: number;
  metrics: Record<string, any>;
  queue: QueueItem[];
}> {
  const res = await fetch(`${API_BASE}/prioritization/queue/${analysisRunId}`);
  if (!res.ok) throw new Error(`Failed to fetch review queue (${res.status})`);
  return res.json();
}

export async function fetchQueueItemDetail(queueItemId: string): Promise<{
  queue_item_id: string;
  analysis_run_id: string;
  finding_id: string;
  cse_id: string;
  rank: number;
  priority_score: number;
  priority_band: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  status: string;
  rationale: string;
  contributing_factors: Record<string, number>;
  explanation: Record<string, any>;
  diversity_notes: string;
  provenance: Record<string, any>;
  audit_history: AuditLogEntry[];
}> {
  const res = await fetch(`${API_BASE}/prioritization/item/${queueItemId}`);
  if (!res.ok) throw new Error(`Failed to fetch queue item detail (${res.status})`);
  return res.json();
}

export async function updateQueueItemStatus(
  queueItemId: string,
  newStatus: string,
  notes = '',
  userId = 'EXAMINER_01'
): Promise<{
  message: string;
  queue_item_id: string;
  status: string;
  audit_log_id: string;
  updated_at: string;
}> {
  const res = await fetch(`${API_BASE}/prioritization/item/${queueItemId}/status`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: newStatus, user_id: userId, notes })
  });
  if (!res.ok) throw new Error(`Failed to update item status (${res.status})`);
  return res.json();
}

export async function fetchEvidencePackage(findingId: string): Promise<EvidencePackage> {
  const res = await fetch(`${API_BASE}/evidence/finding/${findingId}`);
  if (!res.ok) throw new Error(`Failed to fetch evidence package (${res.status})`);
  return res.json();
}

export async function fetchRiskScore(cseId: string): Promise<RiskScoreDetail> {
  const res = await fetch(`${API_BASE}/risk/cse/${cseId}`);
  if (!res.ok) throw new Error(`Failed to fetch risk score (${res.status})`);
  return res.json();
}

export async function fetchGraphSummary(analysisRunId = 'latest'): Promise<GraphData> {
  const res = await fetch(`${API_BASE}/graph/summary/${analysisRunId}`);
  if (!res.ok) throw new Error(`Failed to fetch graph summary (${res.status})`);
  return res.json();
}

export async function fetchGraphPath(alertId: string): Promise<GraphPathInfo> {
  const res = await fetch(`${API_BASE}/graph/path/${alertId}`);
  if (!res.ok) throw new Error(`Failed to fetch graph path (${res.status})`);
  return res.json();
}

export async function fetchGraphAnomalies(analysisRunId = 'latest'): Promise<GraphAnomaly[]> {
  const res = await fetch(`${API_BASE}/graph/anomalies/${analysisRunId}`);
  if (!res.ok) throw new Error(`Failed to fetch graph anomalies (${res.status})`);
  return res.json();
}
