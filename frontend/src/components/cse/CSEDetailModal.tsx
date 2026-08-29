import React, { useState, useEffect } from 'react';
import { CSEProfile, RiskScoreDetail } from '../../types/api';
import { fetchRiskScore } from '../../api/client';
import { PriorityBandBadge } from '../common/Badges';
import { Building2 } from 'lucide-react';

interface CSEModalProps {
  cse: CSEProfile | null;
  isOpen: boolean;
  onClose: () => void;
}

export const CSEDetailModal: React.FC<CSEModalProps> = ({ cse, isOpen, onClose }) => {
  const [riskDetail, setRiskDetail] = useState<RiskScoreDetail | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!cse || !isOpen) return;

    setLoading(true);
    fetchRiskScore(cse.cse_id)
      .then(res => setRiskDetail(res))
      .catch(() => setRiskDetail(null))
      .finally(() => setLoading(false));
  }, [cse, isOpen]);

  if (!isOpen || !cse) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-lg max-w-2xl w-full p-6 shadow-2xl space-y-5 text-xs font-mono">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Building2 className="w-5 h-5 text-cyan-400" />
            <h3 className="text-sm font-mono font-bold text-white uppercase">
              Critical Sector Entity Profile: {cse.name}
            </h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white font-bold text-sm">✕</button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-slate-950 p-4 rounded border border-slate-800">
          <div>
            <span className="text-slate-400 text-[10px] uppercase block">SECTOR</span>
            <strong className="text-white text-xs">{cse.sector}</strong>
          </div>
          <div>
            <span className="text-slate-400 text-[10px] uppercase block">ENTITY TYPE</span>
            <strong className="text-cyan-300 text-xs">{cse.entity_type}</strong>
          </div>
          <div>
            <span className="text-slate-400 text-[10px] uppercase block">SIZE TIER</span>
            <strong className="text-slate-200 text-xs">{cse.size_tier}</strong>
          </div>
          <div>
            <span className="text-slate-400 text-[10px] uppercase block">SUPERVISORY RISK</span>
            <PriorityBandBadge band={cse.risk_band} score={cse.risk_score} />
          </div>
        </div>

        {loading ? (
          <div className="p-6 text-center text-slate-400">Loading CSE Risk Score Decomposition...</div>
        ) : riskDetail ? (
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-cyan-400 uppercase">Risk Contributions Breakdown</h4>
            <div className="space-y-2">
              {(riskDetail.contributions || []).map((c, i) => (
                <div key={i} className="bg-slate-950 p-3 rounded border border-slate-800 flex items-center justify-between">
                  <div>
                    <span className="text-white font-bold block">{c.rule_id} ({c.category})</span>
                    <span className="text-slate-400 text-[10px]">Finding: {c.finding_id}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-rose-400 font-bold block">+{(c.effective_contribution ?? 0).toFixed(1)} pts</span>
                    <span className="text-slate-500 text-[10px]">Confidence: {((c.confidence ?? 1.0) * 100).toFixed(0)}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="p-4 bg-slate-950 text-slate-400 rounded">No risk decomposition details found for this CSE.</div>
        )}

        <div className="flex justify-end pt-3 border-t border-slate-800">
          <button onClick={onClose} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded font-bold">
            Close Profile
          </button>
        </div>
      </div>
    </div>
  );
};
