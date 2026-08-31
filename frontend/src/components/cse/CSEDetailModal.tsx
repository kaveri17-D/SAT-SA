import React, { useState, useEffect } from 'react';
import { CSEProfile, RiskScoreDetail } from '../../types/api';
import { fetchRiskScore } from '../../api/client';
import { PriorityBandBadge, SeverityBadge } from '../common/Badges';
import { Building2, Award, FileText } from 'lucide-react';


interface CSEModalProps {
  cse: CSEProfile | null;
  isOpen: boolean;
  onClose: () => void;
  onInspectFinding?: (findingId: string) => void;
}

export const CSEDetailModal: React.FC<CSEModalProps> = ({ cse, isOpen, onClose, onInspectFinding }) => {
  const [riskDetail, setRiskDetail] = useState<RiskScoreDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!cse || !isOpen) return;

    setLoading(true);
    setError(null);
    fetchRiskScore(cse.cse_id)
      .then(res => setRiskDetail(res))
      .catch(err => setError(err.message || 'Failed to fetch risk score detail'))
      .finally(() => setLoading(false));
  }, [cse, isOpen]);

  if (!isOpen || !cse) return null;

  const categoryBreakdown = riskDetail?.explanation?.category_breakdown || {
    execution_gap: 0,
    negative_space: 0,
    peer_deviation: 0,
    investigation_anomaly: 0,
    asset_criticality: 0
  };

  const totalScore = riskDetail?.normalized_score ?? cse.risk_score;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 font-mono">
      <div className="bg-slate-900 border border-slate-800 rounded-lg max-w-3xl w-full p-6 shadow-2xl space-y-5 max-h-[90vh] overflow-y-auto">
        {/* Header Bar */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Building2 className="w-5 h-5 text-cyan-400" />
              <h3 className="text-base font-bold text-white uppercase tracking-wider">
                Critical Sector Entity: {cse.name}
              </h3>
            </div>
            <p className="text-xs text-slate-400">
              Canonical CSE ID: <span className="text-slate-200">{cse.cse_id}</span>
            </p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white font-bold text-lg px-2">
            &times;
          </button>
        </div>

        {/* Executive Entity Profile Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-slate-950 p-4 rounded-lg border border-slate-800 text-xs">
          <div>
            <span className="text-slate-400 text-[10px] uppercase block">SECTOR</span>
            <strong className="text-white text-sm">{cse.sector}</strong>
          </div>
          <div>
            <span className="text-slate-400 text-[10px] uppercase block">ENTITY TYPE</span>
            <strong className="text-cyan-300 text-sm">{cse.entity_type}</strong>
          </div>
          <div>
            <span className="text-slate-400 text-[10px] uppercase block">SIZE TIER</span>
            <strong className="text-slate-200 text-sm">{cse.size_tier}</strong>
          </div>
          <div>
            <span className="text-slate-400 text-[10px] uppercase block">SUPERVISORY RISK</span>
            <PriorityBandBadge band={cse.risk_band} score={totalScore} />
          </div>
        </div>

        {loading ? (
          <div className="p-8 text-center text-slate-400 text-xs space-y-2">
            <div className="animate-spin w-5 h-5 border-2 border-cyan-400 border-t-transparent rounded-full mx-auto" />
            <p>Loading Explainable Risk Score Decomposition...</p>
          </div>
        ) : error ? (
          <div className="p-4 bg-rose-950/80 border border-rose-800 text-rose-200 text-xs rounded">
            {error}
          </div>
        ) : riskDetail ? (
          <div className="space-y-6">
            {/* Visual Risk Component Contributions Breakdown */}
            <div className="bg-slate-950 border border-slate-800 p-5 rounded-lg space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h4 className="text-xs font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-2">
                  <Award className="w-4 h-4 text-amber-400" />
                  Explainable Supervisory Risk Decomposition ({totalScore.toFixed(1)} / 100)
                </h4>
                <span className="text-[11px] text-slate-400">
                  Confidence: <strong className="text-emerald-400">{((riskDetail.overall_confidence ?? 1.0) * 100).toFixed(0)}%</strong>
                </span>
              </div>

              <div className="space-y-3 pt-1 text-xs">
                {[
                  { label: 'Execution Gap (SLA Violations)', key: 'execution_gap', color: 'bg-rose-500', pts: categoryBreakdown.execution_gap },
                  { label: 'Negative Space (Silent Telemetry)', key: 'negative_space', color: 'bg-amber-500', pts: categoryBreakdown.negative_space },
                  { label: 'Peer Deviation (Sector Outliers)', key: 'peer_deviation', color: 'bg-purple-500', pts: categoryBreakdown.peer_deviation },
                  { label: 'Investigation Anomalies', key: 'investigation_anomaly', color: 'bg-blue-500', pts: categoryBreakdown.investigation_anomaly },
                  { label: 'Asset Criticality Multiplier', key: 'asset_criticality', color: 'bg-cyan-500', pts: categoryBreakdown.asset_criticality }
                ].map(cat => (
                  <div key={cat.key} className="space-y-1">
                    <div className="flex justify-between text-[11px]">
                      <span className="text-slate-300 font-semibold">{cat.label}</span>
                      <span className="text-cyan-300 font-bold">+{Number(cat.pts || 0).toFixed(1)} pts</span>
                    </div>
                    <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden border border-slate-800">
                      <div
                        className={`h-full ${cat.color} transition-all duration-500`}
                        style={{ width: `${Math.min(100, Math.max(0, (cat.pts || 0) * 2.5))}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Confirmed Contributing Findings */}
            <div className="bg-slate-950 border border-slate-800 p-5 rounded-lg space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h4 className="text-xs font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-2">
                  <FileText className="w-4 h-4 text-cyan-400" />
                  Confirmed Contributing Findings ({(riskDetail.contributions || []).length})
                </h4>
              </div>

              <div className="space-y-2 text-xs">
                {(riskDetail.contributions || []).map((c, i) => (
                  <div key={i} className="bg-slate-900 p-3.5 rounded border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 font-bold">
                        <span className="text-white">{c.rule_id}</span>
                        <span className="text-slate-400 text-[11px]">({c.category || c.component_category})</span>
                        {c.severity && <SeverityBadge severity={c.severity} />}
                      </div>
                      <div className="text-right">
                        <span className="text-rose-400 font-bold block">+{(c.effective_contribution ?? 0).toFixed(1)} pts</span>
                        <span className="text-slate-400 text-[10px]">Confidence: {((c.confidence ?? 1.0) * 100).toFixed(0)}%</span>
                      </div>
                    </div>

                    {c.reason && (
                      <p className="text-[11px] text-slate-300 bg-slate-950 p-2 rounded border border-slate-800/80">
                        {c.reason}
                      </p>
                    )}

                    <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1">
                      <span>Finding ID: <span className="text-slate-300">{c.finding_id}</span></span>
                      {onInspectFinding && (
                        <button
                          onClick={() => onInspectFinding(c.finding_id)}
                          className="text-cyan-400 hover:text-cyan-300 font-bold underline"
                        >
                          Inspect Finding &rarr;
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="p-4 bg-slate-950 text-slate-400 rounded text-xs">
            No risk decomposition details available for this CSE.
          </div>
        )}

        <div className="flex justify-end pt-3 border-t border-slate-800">
          <button onClick={onClose} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded font-bold text-xs">
            Close Profile
          </button>
        </div>
      </div>
    </div>
  );
};

