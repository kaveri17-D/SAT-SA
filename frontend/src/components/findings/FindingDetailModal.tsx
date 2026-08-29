import React, { useState, useEffect } from 'react';
import {
  fetchQueueItemDetail,
  fetchEvidencePackage,
  fetchRiskScore,
  fetchGraphSummary,
  fetchGraphPath,
  fetchGraphAnomalies
} from '../../api/client';
import {
  EvidencePackage,
  RiskScoreDetail,
  GraphData,
  GraphPathInfo,
  GraphAnomaly,
  AuditLogEntry,
  QueueItem
} from '../../types/api';
import { PriorityBandBadge, SeverityBadge, StatusBadge, CompletenessGauge } from '../common/Badges';
import { ExpectedVsObservedDiagram } from '../diagrams/ExpectedVsObservedDiagram';
import { EvidenceGraphViewer } from '../graph/EvidenceGraphViewer';
import { AuditTrailPanel } from '../audit/AuditTrailPanel';
import { ExaminerActionModal } from '../audit/ExaminerActionModal';
import {
  ShieldAlert,
  FileText,
  Layers,
  Award,
  Database,
  History,
  AlertCircle,
  ExternalLink
} from 'lucide-react';

interface FindingDetailModalProps {
  queueItem: QueueItem | null;
  isOpen: boolean;
  onClose: () => void;
  onRefreshQueue?: () => void;
}

export const FindingDetailModal: React.FC<FindingDetailModalProps> = ({
  queueItem,
  isOpen,
  onClose,
  onRefreshQueue
}) => {
  const [activeTab, setActiveTab] = useState<'OVERVIEW' | 'EVIDENCE' | 'RISK' | 'GRAPH' | 'AUDIT'>('OVERVIEW');
  const [evidence, setEvidence] = useState<EvidencePackage | null>(null);
  const [risk, setRisk] = useState<RiskScoreDetail | null>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [pathInfo, setPathInfo] = useState<GraphPathInfo | null>(null);
  const [anomalies, setAnomalies] = useState<GraphAnomaly[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [currentStatus, setCurrentStatus] = useState<string>('NEW');
  const [isActionModalOpen, setIsActionModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!queueItem || !isOpen) return;

    let isMounted = true;
    setLoading(true);
    setError(null);
    setCurrentStatus(queueItem.status);

    async function loadData() {
      try {
        const [itemDetail, evPkg, rskDetail, grpSummary, grpAnom] = await Promise.all([
          fetchQueueItemDetail(queueItem!.queue_item_id),
          fetchEvidencePackage(queueItem!.finding_id),
          fetchRiskScore(queueItem!.cse_id),
          fetchGraphSummary('latest'),
          fetchGraphAnomalies('latest')
        ]);

        if (!isMounted) return;

        setEvidence(evPkg);
        setRisk(rskDetail);
        setGraphData(grpSummary);
        setAnomalies(grpAnom);
        setAuditLogs(itemDetail.audit_history || []);
        setCurrentStatus(itemDetail.status);

        // Attempt path reconstruction if alert_id present in evidence records
        const recordsList = evPkg.records || evPkg.supporting_records || [];
        const alertRecord = recordsList.find(r => r.source_table === 'alerts' || r.source_entity_type === 'Alert' || r.source_entity_type === 'alerts');
        if (alertRecord && alertRecord.source_record_id) {
          try {
            const path = await fetchGraphPath(alertRecord.source_record_id);
            if (isMounted) setPathInfo(path);
          } catch {
            // Path reconstruction fallback if alert record is mock/null
          }
        }
      } catch (err: any) {
        if (isMounted) setError(err.message || 'Failed to load complete evidence package.');
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadData();

    return () => {
      isMounted = false;
    };
  }, [queueItem, isOpen]);

  if (!isOpen || !queueItem) return null;

  const handleActionSuccess = (newStatus: string) => {
    setCurrentStatus(newStatus);
    if (onRefreshQueue) onRefreshQueue();
    // Reload queue item detail to get updated audit history
    fetchQueueItemDetail(queueItem.queue_item_id).then(detail => {
      setAuditLogs(detail.audit_history || []);
    });
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-lg max-w-5xl w-full my-8 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header Bar */}
        <div className="border-b border-slate-800 bg-slate-950 px-6 py-4 flex items-center justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold text-cyan-400 bg-cyan-950 border border-cyan-800 px-2 py-0.5 rounded">
                RANK #{queueItem.rank}
              </span>
              <h2 className="text-base font-bold text-white font-mono flex items-center gap-2">
                Finding Inspection Panel
                <span className="text-xs text-slate-400 font-normal">({queueItem.finding_id})</span>
              </h2>
            </div>
            <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
              <span>CSE: <strong className="text-slate-200">{queueItem.cse_id.slice(0, 13)}</strong></span>
              <span>|</span>
              <PriorityBandBadge band={queueItem.priority_band} score={queueItem.priority_score} />
              <span>|</span>
              <StatusBadge status={currentStatus} />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsActionModalOpen(true)}
              className="px-3.5 py-1.5 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-mono font-bold text-xs shadow-lg shadow-cyan-600/20 transition flex items-center gap-1.5"
            >
              <ShieldAlert className="w-4 h-4" />
              <span>Record Action</span>
            </button>
            <button onClick={onClose} className="text-slate-400 hover:text-white font-bold text-lg px-2">
              ✕
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-slate-800 bg-slate-900/60 px-6 flex items-center gap-4 text-xs font-mono">
          {[
            { id: 'OVERVIEW', label: '1. What & Why (Overview)', icon: <FileText className="w-3.5 h-3.5" /> },
            { id: 'EVIDENCE', label: '2. Evidence Inspector', icon: <Database className="w-3.5 h-3.5" /> },
            { id: 'RISK', label: '3. Risk Decomposition', icon: <Award className="w-3.5 h-3.5" /> },
            { id: 'GRAPH', label: '4. Supervisory Graph', icon: <Layers className="w-3.5 h-3.5" /> },
            { id: 'AUDIT', label: '5. Examiner Audit Logs', icon: <History className="w-3.5 h-3.5" /> }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-3 px-1 border-b-2 font-bold flex items-center gap-1.5 transition ${
                activeTab === tab.id
                  ? 'border-cyan-400 text-cyan-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Body Content */}
        <div className="flex-1 p-6 overflow-y-auto space-y-6">
          {loading && (
            <div className="p-12 text-center text-slate-400 font-mono text-xs space-y-2">
              <div className="animate-spin w-6 h-6 border-2 border-cyan-400 border-t-transparent rounded-full mx-auto" />
              <p>Assembling Evidence Package & Provenance...</p>
            </div>
          )}

          {error && (
            <div className="bg-rose-950/80 border border-rose-800 text-rose-200 p-4 rounded text-xs font-mono flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {!loading && !error && (
            <>
              {/* TAB 1: OVERVIEW */}
              {activeTab === 'OVERVIEW' && (
                <div className="space-y-6">
                  {/* WHAT WAS DETECTED */}
                  <div className="bg-slate-950 border border-slate-800 rounded-lg p-5 space-y-3">
                    <h3 className="text-xs font-mono font-bold text-cyan-400 uppercase tracking-wider">
                      A. WHAT WAS DETECTED
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono">
                      <div>
                        <span className="text-slate-400 block text-[10px]">RULE ID</span>
                        <strong className="text-white text-sm">{evidence?.rule_id || 'GAP-01'}</strong>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px]">FINDING CATEGORY</span>
                        <strong className="text-cyan-300">{evidence?.finding_type || 'EXECUTION_GAP'}</strong>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px]">SEVERITY</span>
                        <SeverityBadge severity={evidence?.severity || 'CRITICAL'} />
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px]">DISPOSITION STATUS</span>
                        <StatusBadge status={currentStatus} />
                      </div>
                    </div>
                  </div>

                  {/* WHY IT WAS DETECTED & EXPECTED VS OBSERVED FLOWCHART */}
                  <ExpectedVsObservedDiagram
                    pathInfo={pathInfo}
                    expectedBehaviour={evidence?.expected_behaviour}
                    observedBehaviour={evidence?.observed_behaviour}
                    deviation={evidence?.deviation}
                  />

                  {/* WHY IT IS PRIORITIZED */}
                  <div className="bg-slate-950 border border-slate-800 rounded-lg p-5 space-y-3">
                    <h3 className="text-xs font-mono font-bold text-cyan-400 uppercase tracking-wider">
                      B. WHY IT IS PRIORITIZED FOR REVIEW (8-Factor Weight Rationale)
                    </h3>
                    <p className="text-xs text-slate-300 font-mono italic">
                      "{queueItem.rationale}"
                    </p>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2">
                      {Object.entries(queueItem.contributing_factors).map(([factor, score]) => (
                        <div key={factor} className="bg-slate-900 border border-slate-800 p-2.5 rounded text-xs font-mono">
                          <span className="text-slate-400 text-[10px] uppercase block">{factor.replace('_', ' ')}</span>
                          <span className="text-cyan-300 font-bold">{Number(score).toFixed(1)} / 100</span>
                        </div>
                      ))}
                    </div>

                    {queueItem.diversity_notes && (
                      <div className="bg-slate-900 border border-slate-800 p-3 rounded text-xs font-mono text-slate-300">
                        <span className="text-amber-400 font-bold block mb-1">Diversity Queue Qualification:</span>
                        {queueItem.diversity_notes}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* TAB 2: EVIDENCE INSPECTOR */}
              {activeTab === 'EVIDENCE' && evidence && (
                <div className="space-y-6">
                  <div className="bg-slate-950 border border-slate-800 rounded-lg p-5 space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                      <h3 className="text-xs font-mono font-bold text-cyan-400 uppercase tracking-wider">
                        Canonical Supporting Evidence Package
                      </h3>
                      <div className="flex items-center gap-4 text-xs font-mono">
                        <div>Completeness: <CompletenessGauge score={evidence.evidence_completeness} /></div>
                        <div>Confidence: <strong className="text-emerald-400">{((evidence.confidence ?? 1.0) * 100).toFixed(0)}%</strong></div>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <div className="text-xs font-mono text-slate-400 font-semibold uppercase">Supporting Database Source Records</div>
                      {(evidence.records || evidence.supporting_records || []).map((rec, i) => (
                        <div key={i} className="bg-slate-900 border border-slate-800 rounded p-3.5 text-xs font-mono space-y-2">
                          <div className="flex items-center justify-between text-cyan-300 font-bold">
                            <span className="flex items-center gap-1.5">
                              <ExternalLink className="w-3.5 h-3.5 text-cyan-400" />
                              Table: <span className="text-white">{rec.source_table || rec.source_entity_type || 'Unknown'}</span> (ID: {rec.source_record_id})
                            </span>
                            <span className="text-[10px] text-slate-400">Type: {rec.evidence_type}</span>
                          </div>

                          <div className="bg-slate-950 p-2.5 rounded border border-slate-800 overflow-x-auto text-[11px] text-slate-300">
                            <pre>{JSON.stringify(rec.payload, null, 2)}</pre>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 3: RISK DECOMPOSITION */}
              {activeTab === 'RISK' && risk && (
                <div className="space-y-6">
                  <div className="bg-slate-950 border border-slate-800 rounded-lg p-5 space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                      <div>
                        <h3 className="text-xs font-mono font-bold text-cyan-400 uppercase tracking-wider">
                          CSE Supervisory Risk Score Decomposition
                        </h3>
                        <p className="text-xs text-slate-400">CSE ID: {risk.cse_id}</p>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-mono font-bold text-rose-400">{(risk.normalized_score ?? 0).toFixed(1)} / 100</div>
                        <PriorityBandBadge band={risk.risk_band} />
                      </div>
                    </div>

                    <div className="space-y-3">
                      <div className="text-xs font-mono text-slate-400 font-semibold uppercase">Confirmed Contributing Findings</div>
                      {(risk.contributions || []).map((c, idx) => (
                        <div key={idx} className="bg-slate-900 border border-slate-800 rounded p-3 text-xs font-mono flex items-center justify-between">
                          <div>
                            <span className="font-bold text-white block">{c.rule_id} ({c.category})</span>
                            <span className="text-slate-400 text-[11px]">Finding ID: {c.finding_id}</span>
                          </div>
                          <div className="text-right">
                            <span className="text-rose-400 font-bold block">+{(c.effective_contribution ?? 0).toFixed(1)} pts</span>
                            <span className="text-slate-400 text-[10px]">Confidence Mod: {((c.confidence ?? 1.0) * 100).toFixed(0)}%</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 4: SUPERVISORY GRAPH */}
              {activeTab === 'GRAPH' && (
                <EvidenceGraphViewer graphData={graphData} anomalies={anomalies} />
              )}

              {/* TAB 5: AUDIT LOGS */}
              {activeTab === 'AUDIT' && (
                <AuditTrailPanel logs={auditLogs} />
              )}
            </>
          )}
        </div>

        {/* Footer Bar */}
        <div className="border-t border-slate-800 bg-slate-950 px-6 py-3 flex items-center justify-between text-xs font-mono text-slate-400">
          <div>SAT-SA Offline Supervisory Intelligence — Evidence Immutable</div>
          <button
            onClick={() => setIsActionModalOpen(true)}
            className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold"
          >
            Update Examiner Status
          </button>
        </div>
      </div>

      {/* Examiner Action Modal */}
      <ExaminerActionModal
        queueItemId={queueItem.queue_item_id}
        currentStatus={currentStatus}
        isOpen={isActionModalOpen}
        onClose={() => setIsActionModalOpen(false)}
        onSuccess={handleActionSuccess}
      />
    </div>
  );
};
