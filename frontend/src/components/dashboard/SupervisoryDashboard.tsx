import React, { useState, useMemo } from 'react';
import { DashboardMetrics, CSEProfile } from '../../types/api';
import { PriorityBandBadge } from '../common/Badges';
import { Building2, ShieldAlert, AlertTriangle, Layers, FileText, CheckCircle2, Lock, Search, Filter, ArrowUpDown, Database, Activity } from 'lucide-react';

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
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedBand, setSelectedBand] = useState<string>('ALL');
  const [sortBy, setSortBy] = useState<'risk' | 'findings' | 'name'>('risk');

  // Compute Risk Distribution breakdown counts
  const bandCounts = useMemo(() => {
    const counts = { CRITICAL: 0, HIGH: 0, MODERATE: 0, LOW: 0 };
    cses.forEach(c => {
      const band = (c.risk_band || 'LOW').toUpperCase();
      if (band in counts) {
        counts[band as keyof typeof counts]++;
      } else {
        counts.LOW++;
      }
    });
    return counts;
  }, [cses]);

  // Filter & Sort CSE profiles
  const filteredCSEs = useMemo(() => {
    return cses
      .filter(c => {
        const matchesSearch = c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                              c.sector.toLowerCase().includes(searchTerm.toLowerCase()) ||
                              c.entity_type.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesBand = selectedBand === 'ALL' || (c.risk_band || 'LOW').toUpperCase() === selectedBand;
        return matchesSearch && matchesBand;
      })
      .sort((a, b) => {
        if (sortBy === 'risk') return (b.risk_score || 0) - (a.risk_score || 0);
        if (sortBy === 'findings') return (b.finding_count || 0) - (a.finding_count || 0);
        return a.name.localeCompare(b.name);
      });
  }, [cses, searchTerm, selectedBand, sortBy]);

  return (
    <div className="space-y-6">
      {/* Active Analysis Run Context Banner */}
      <div className="bg-slate-900/90 border border-cyan-800/40 rounded-lg p-4 font-mono text-xs text-slate-300 flex flex-wrap items-center justify-between gap-4 shadow-md">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-cyan-950 border border-cyan-700/50 rounded text-cyan-400">
            <Activity className="w-4 h-4 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-cyan-300">ACTIVE ANALYSIS RUN:</span>
              <span className="text-white font-mono bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                {metrics?.analysis_run_id || '3052411c-0af5-49f6-8667-f55dcbf03b4b'}
              </span>
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5 flex items-center gap-4">
              <span>Dataset Import: <strong className="text-slate-200">{metrics?.dataset_import_id ? metrics.dataset_import_id.slice(0, 18) : '52abc9cf-6a48-4c74'} (seed=42)</strong></span>
              <span>Rule Version: <strong className="text-emerald-400">v{metrics?.rule_version || '1.0.0'}</strong></span>
              <span>Engine Status: <strong className="text-emerald-400">{metrics?.status || 'COMPLETED'}</strong></span>
            </div>

          </div>
        </div>

        <div className="flex items-center gap-2 text-[11px]">
          <span className="px-2.5 py-1 bg-emerald-950 text-emerald-300 border border-emerald-800 rounded font-semibold flex items-center gap-1.5">
            <Lock className="w-3 h-3 text-emerald-400" />
            STRICT AIR-GAP ACTIVE
          </span>
        </div>
      </div>

      {/* Executive Positioning Statement */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-900 to-slate-950 border border-slate-800 rounded-lg p-5 relative overflow-hidden shadow-lg">
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-gradient-to-l from-cyan-500/10 to-transparent pointer-events-none" />
        <div className="max-w-3xl space-y-1.5">
          <div className="text-[11px] font-mono text-cyan-400 tracking-wider uppercase font-semibold flex items-center gap-2">
            <Database className="w-3.5 h-3.5 text-cyan-400" />
            NCIIPC Air-Gapped Supervisory Intelligence Console
          </div>
          <p className="text-sm font-medium text-slate-200 leading-relaxed italic">
            "SAT-SA is an offline, evidence-first supervisory intelligence platform that detects improper SOC execution, missing expected evidence, compares behaviour with peers, and prioritizes cases for human examination."
          </p>
        </div>
      </div>

      {/* KPI Metric Cards Grid */}
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
          className="bg-slate-900 border border-cyan-900/60 hover:border-cyan-500 rounded-lg p-4 font-mono space-y-2 cursor-pointer transition shadow-sm"
        >
          <div className="flex items-center justify-between text-cyan-400 text-xs">
            <span>HIGH PRIORITY QUEUE</span>
            <Layers className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-cyan-300">
            {metrics?.high_priority_reviews ?? 0}
          </div>
          <div className="text-[11px] text-cyan-400 font-semibold hover:underline flex items-center justify-between">
            <span>Open Ranked Queue</span>
            <span>➔</span>
          </div>
        </div>
      </div>

      {/* Risk Band Distribution Component */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-3 font-mono">
        <div className="flex items-center justify-between text-xs text-slate-300 font-bold uppercase tracking-wider">
          <span className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-cyan-400" />
            Supervisory Risk Band Distribution
          </span>
          <span className="text-slate-400 font-normal">{cses.length} Total Entities Classified</span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs pt-1">
          <div
            onClick={() => setSelectedBand(selectedBand === 'CRITICAL' ? 'ALL' : 'CRITICAL')}
            className={`p-3 rounded border cursor-pointer transition flex items-center justify-between ${
              selectedBand === 'CRITICAL'
                ? 'bg-rose-950 border-rose-600 text-rose-200'
                : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-rose-800'
            }`}
          >
            <div>
              <div className="text-[10px] text-rose-400 font-bold">CRITICAL RISK (&ge;75)</div>
              <div className="text-xl font-bold text-white mt-0.5">{bandCounts.CRITICAL}</div>
            </div>
            <ShieldAlert className="w-5 h-5 text-rose-400 opacity-80" />
          </div>

          <div
            onClick={() => setSelectedBand(selectedBand === 'HIGH' ? 'ALL' : 'HIGH')}
            className={`p-3 rounded border cursor-pointer transition flex items-center justify-between ${
              selectedBand === 'HIGH'
                ? 'bg-amber-950 border-amber-600 text-amber-200'
                : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-amber-800'
            }`}
          >
            <div>
              <div className="text-[10px] text-amber-400 font-bold">HIGH RISK (50–74)</div>
              <div className="text-xl font-bold text-white mt-0.5">{bandCounts.HIGH}</div>
            </div>
            <AlertTriangle className="w-5 h-5 text-amber-400 opacity-80" />
          </div>

          <div
            onClick={() => setSelectedBand(selectedBand === 'MODERATE' ? 'ALL' : 'MODERATE')}
            className={`p-3 rounded border cursor-pointer transition flex items-center justify-between ${
              selectedBand === 'MODERATE'
                ? 'bg-yellow-950 border-yellow-600 text-yellow-200'
                : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-yellow-800'
            }`}
          >
            <div>
              <div className="text-[10px] text-yellow-400 font-bold">MODERATE (25–49)</div>
              <div className="text-xl font-bold text-white mt-0.5">{bandCounts.MODERATE}</div>
            </div>
            <Layers className="w-5 h-5 text-yellow-400 opacity-80" />
          </div>

          <div
            onClick={() => setSelectedBand(selectedBand === 'LOW' ? 'ALL' : 'LOW')}
            className={`p-3 rounded border cursor-pointer transition flex items-center justify-between ${
              selectedBand === 'LOW'
                ? 'bg-emerald-950 border-emerald-600 text-emerald-200'
                : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-emerald-800'
            }`}
          >
            <div>
              <div className="text-[10px] text-emerald-400 font-bold">LOW RISK (&lt;25)</div>
              <div className="text-xl font-bold text-white mt-0.5">{bandCounts.LOW}</div>
            </div>
            <CheckCircle2 className="w-5 h-5 text-emerald-400 opacity-80" />
          </div>
        </div>
      </div>

      {/* Critical Sector Entity Overview Table & Controls */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3 font-mono">
          <div className="flex items-center gap-2">
            <Building2 className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-bold text-cyan-400 uppercase tracking-wider">
              Critical Sector Entities Risk Summary
            </h3>
            <span className="text-[11px] bg-slate-800 px-2 py-0.5 rounded text-slate-300">
              Showing {filteredCSEs.length} of {cses.length}
            </span>
          </div>

          {/* Search, Filter, Sort Controls */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Search CSE, sector..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="bg-slate-950 border border-slate-800 focus:border-cyan-500 text-slate-200 pl-8 pr-3 py-1.5 rounded text-xs focus:outline-none w-48 font-mono"
              />
            </div>

            <div className="flex items-center gap-1 bg-slate-950 border border-slate-800 rounded px-2 py-1">
              <ArrowUpDown className="w-3 h-3 text-slate-400" />
              <span className="text-slate-400 text-[11px]">Sort:</span>
              <select
                value={sortBy}
                onChange={e => setSortBy(e.target.value as any)}
                className="bg-transparent text-slate-200 focus:outline-none font-mono text-xs"
              >
                <option value="risk" className="bg-slate-900 text-slate-200">Risk Score</option>
                <option value="findings" className="bg-slate-900 text-slate-200">Findings Count</option>
                <option value="name" className="bg-slate-900 text-slate-200">Entity Name</option>
              </select>
            </div>

            {selectedBand !== 'ALL' && (
              <button
                onClick={() => setSelectedBand('ALL')}
                className="px-2 py-1 bg-slate-800 hover:bg-slate-700 rounded text-[11px] text-cyan-300 font-bold"
              >
                Reset Filter ({selectedBand}) &times;
              </button>
            )}
          </div>
        </div>

        {/* Filtered CSE Cards Grid */}
        {filteredCSEs.length === 0 ? (
          <div className="bg-slate-950 border border-slate-800 rounded p-8 text-center font-mono text-xs text-slate-400 space-y-2">
            <Building2 className="w-8 h-8 text-slate-600 mx-auto" />
            <div>No Critical Sector Entities match the current filters.</div>
            <button
              onClick={() => { setSearchTerm(''); setSelectedBand('ALL'); }}
              className="text-cyan-400 font-bold underline hover:text-cyan-300"
            >
              Reset Search & Filter Criteria
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {filteredCSEs.map(cse => (
              <div
                key={cse.cse_id}
                onClick={() => onSelectCSE(cse)}
                className="bg-slate-950 border border-slate-800 hover:border-slate-700 rounded-lg p-3.5 font-mono space-y-2 cursor-pointer transition shadow-sm hover:shadow-md"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold text-white text-xs truncate max-w-[180px]">{cse.name}</span>
                  <PriorityBandBadge band={cse.risk_band} score={cse.risk_score} />
                </div>
                <div className="flex items-center justify-between text-[11px] text-slate-400">
                  <span>Sector: <strong className="text-slate-200">{cse.sector}</strong></span>
                  <span>Tier: <strong className="text-cyan-300">{cse.size_tier}</strong></span>
                </div>
                <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1.5 border-t border-slate-900">
                  <span>Assets: <strong className="text-slate-300">{cse.asset_count}</strong></span>
                  <span>Findings: <strong className="text-amber-400">{cse.finding_count}</strong></span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

