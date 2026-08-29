import React from 'react';
import { DashboardMetrics, CSEProfile } from '../../types/api';
import { PriorityBandBadge } from '../common/Badges';
import { Building2, ShieldAlert, AlertTriangle, Layers, FileText, CheckCircle2, Lock } from 'lucide-react';

interface DashboardProps {
  metrics: DashboardMetrics | null;
  cses: CSEProfile[];
  onSelectCSE: (cse: CSEProfile) => void;
  onNavigateToQueue: () => void;
}

export const SupervisoryDashboard: React.FC<DashboardProps> = ({
  metrics,
  cses,
  onSelectCSE,
  onNavigateToQueue
}) => {
  return (
    <div className="space-y-6">
      {/* Executive Positioning Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-900 to-slate-950 border border-slate-800 rounded-lg p-5 relative overflow-hidden shadow-lg">
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-gradient-to-l from-cyan-500/10 to-transparent pointer-events-none" />
        <div className="max-w-3xl space-y-1.5">
          <div className="text-[11px] font-mono text-cyan-400 tracking-wider uppercase font-semibold flex items-center gap-2">
            <Lock className="w-3.5 h-3.5 text-emerald-400" />
            NCIIPC Air-Gapped Supervisory Intelligence Console
          </div>
          <p className="text-sm font-medium text-slate-200 leading-relaxed italic">
            "SAT-SA is an offline, evidence-first supervisory intelligence platform that detects both improper SOC execution and missing expected evidence, compares behaviour with peers, and prioritizes cases for human examination."
          </p>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 font-mono space-y-2">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>TOTAL CSEs MONITORED</span>
            <Building2 className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {metrics?.total_cses ?? 0}
          </div>
          <div className="text-[11px] text-rose-400 font-semibold flex items-center gap-1">
            <ShieldAlert className="w-3 h-3" />
            <span>{metrics?.critical_cses ?? 0} High/Critical Risk</span>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 font-mono space-y-2">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>CONFIRMED FINDINGS</span>
            <FileText className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {metrics?.total_findings ?? 0}
          </div>
          <div className="text-[11px] text-amber-300 font-semibold flex items-center gap-1">
            <AlertTriangle className="w-3 h-3 text-amber-400" />
            <span>{metrics?.critical_findings ?? 0} Critical Severity</span>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 font-mono space-y-2">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>EVIDENCE COMPLETENESS</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400">
            {metrics?.avg_evidence_completeness ?? 100}%
          </div>
          <div className="text-[11px] text-slate-400">
            Across canonical database records
          </div>
        </div>

        <div
          onClick={onNavigateToQueue}
          className="bg-slate-900 border border-cyan-900/60 hover:border-cyan-500 rounded-lg p-4 font-mono space-y-2 cursor-pointer transition"
        >
          <div className="flex items-center justify-between text-cyan-400 text-xs">
            <span>HIGH PRIORITY QUEUE</span>
            <Layers className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-cyan-300">
            {metrics?.high_priority_reviews ?? 0}
          </div>
          <div className="text-[11px] text-cyan-400 font-semibold hover:underline">
            Open Ranked Queue ➔
          </div>
        </div>
      </div>

      {/* Critical Sector Entity Overview Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3 className="text-xs font-mono font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-2">
            <Building2 className="w-4 h-4 text-cyan-400" />
            Critical Sector Entities Risk Summary
          </h3>
          <span className="text-xs font-mono text-slate-400">{cses.length} Total Entities</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {cses.map(cse => (
            <div
              key={cse.cse_id}
              onClick={() => onSelectCSE(cse)}
              className="bg-slate-950 border border-slate-800 hover:border-slate-700 rounded-lg p-3.5 font-mono space-y-2 cursor-pointer transition"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-white text-xs truncate max-w-[180px]">{cse.name}</span>
                <PriorityBandBadge band={cse.risk_band} score={cse.risk_score} />
              </div>
              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span>Sector: <strong className="text-slate-200">{cse.sector}</strong></span>
                <span>Tier: <strong className="text-cyan-300">{cse.size_tier}</strong></span>
              </div>
              <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-900">
                <span>Assets: {cse.asset_count}</span>
                <span>Findings: <strong className="text-amber-400">{cse.finding_count}</strong></span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
