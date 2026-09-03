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
  SimpleWorkflowData,
  AuditLogEntry,
  EvidenceIntegrityResult
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

export async function fetchCSEProfiles(analysisRunId?: string): Promise<CSEProfile[]> {
  const query = analysisRunId && analysisRunId !== 'latest' ? `?analysis_run_id=${analysisRunId}` : '';
  const res = await fetch(`${API_BASE}/prioritization/cses${query}`);
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

export async function verifyEvidenceIntegrity(findingId: string): Promise<EvidenceIntegrityResult> {
  const res = await fetch(`${API_BASE}/evidence/${findingId}/verify`);
  if (!res.ok) throw new Error(`Failed to verify evidence integrity (${res.status})`);
  return res.json();
}


export async function fetchRiskScore(cseId: string): Promise<RiskScoreDetail> {
  const res = await fetch(`${API_BASE}/risk/cse/${cseId}`);
  if (!res.ok) throw new Error(`Failed to fetch risk score (${res.status})`);
  return res.json();
}

export async function fetchLatestRiskScores(): Promise<RiskScoreDetail[]> {
  const res = await fetch(`${API_BASE}/risk/scores/latest`);
  if (!res.ok) throw new Error(`Failed to fetch latest risk scores (${res.status})`);
  return res.json();
}

export async function fetchRiskScoresForRun(analysisRunId = 'latest'): Promise<RiskScoreDetail[]> {
  const url = analysisRunId === 'latest'
    ? `${API_BASE}/risk/scores/latest`
    : `${API_BASE}/risk/run/${analysisRunId}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch risk scores for run (${res.status})`);
  return res.json();
}

export async function fetchSimpleWorkflow(
  analysisRunId = 'latest',
  params?: { cseId?: string; findingId?: string; alertId?: string }
): Promise<SimpleWorkflowData> {
  const query = new URLSearchParams();
  if (params?.cseId) query.set('cse_id', params.cseId);
  if (params?.findingId) query.set('finding_id', params.findingId);
  if (params?.alertId) query.set('alert_id', params.alertId);
  const qStr = query.toString() ? `?${query.toString()}` : '';
  const res = await fetch(`${API_BASE}/graph/simple/${analysisRunId}${qStr}`);
  if (!res.ok) throw new Error(`Failed to fetch simple workflow (${res.status})`);
  return res.json();
}

export async function fetchGraphSummary(analysisRunId = 'latest'): Promise<GraphData> {
  const res = await fetch(`${API_BASE}/graph/summary/${analysisRunId}`);
  if (!res.ok) throw new Error(`Failed to fetch graph summary (${res.status})`);
  return res.json();
}

export async function fetchFullGraph(analysisRunId = 'latest', maxNodes = 1000): Promise<GraphData> {
  const res = await fetch(`${API_BASE}/graph/full/${analysisRunId}?max_nodes=${maxNodes}`);
  if (!res.ok) throw new Error(`Failed to fetch full graph (${res.status})`);
  return res.json();
}

export async function fetchGraphNodeDetail(nodeId: string): Promise<{
  node: Record<string, any>;
  neighbors: Array<Record<string, any>>;
  edges: Array<Record<string, any>>;
  degree: number;
}> {
  const res = await fetch(`${API_BASE}/graph/node/${nodeId}`);
  if (!res.ok) throw new Error(`Failed to fetch node detail (${res.status})`);
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

export async function fetchReports(params?: {
  assessment_id?: string;
  cse_id?: string;
  report_type?: string;
  limit?: number;
  offset?: number;
}): Promise<{ total_count: number; reports: any[] }> {
  const query = new URLSearchParams();
  if (params?.assessment_id) query.set('assessment_id', params.assessment_id);
  if (params?.cse_id) query.set('cse_id', params.cse_id);
  if (params?.report_type) query.set('report_type', params.report_type);
  if (params?.limit) query.set('limit', params.limit.toString());
  if (params?.offset) query.set('offset', params.offset.toString());

  const res = await fetch(`${API_BASE}/reports?${query.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch reports (${res.status})`);
  return res.json();
}

export async function fetchReportDetail(reportId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/reports/${reportId}`);
  if (!res.ok) throw new Error(`Failed to fetch report detail (${res.status})`);
  return res.json();
}

export async function generateReport(payload: {
  assessment_id: string;
  report_type: string;
  cse_id?: string;
  title?: string;
  description?: string;
  generated_by?: string;
}): Promise<any> {
  const res = await fetch(`${API_BASE}/reports/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error(`Failed to generate report (${res.status})`);
  return res.json();
}

export function getReportExportUrl(reportId: string, format: 'json' | 'html'): string {
  return `${API_BASE}/reports/${reportId}/export?format=${format}`;
}

export async function fetchAuditLogs(params?: {
  user_id?: string;
  actor_role?: string;
  action?: string;
  entity_type?: string;
  entity_id?: string;
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<{ total_count: number; logs: any[] }> {
  const query = new URLSearchParams();
  if (params?.user_id) query.set('user_id', params.user_id);
  if (params?.actor_role) query.set('actor_role', params.actor_role);
  if (params?.action) query.set('action', params.action);
  if (params?.entity_type) query.set('entity_type', params.entity_type);
  if (params?.entity_id) query.set('entity_id', params.entity_id);
  if (params?.status) query.set('status', params.status);
  if (params?.limit) query.set('limit', params.limit.toString());
  if (params?.offset) query.set('offset', params.offset.toString());

  const res = await fetch(`${API_BASE}/audit/logs?${query.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch audit logs (${res.status})`);
  return res.json();
}

export async function verifyAuditTrail(): Promise<any> {
  const res = await fetch(`${API_BASE}/audit/verify`);
  if (!res.ok) throw new Error(`Failed to verify audit trail (${res.status})`);
  return res.json();
}

