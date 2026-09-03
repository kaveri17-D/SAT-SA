import React, { useState, useEffect, useMemo } from 'react';
import { CSEProfile, RiskScoreDetail } from '../../types/api';
import { fetchRiskScoresForRun } from '../../api/client';
import { PriorityBandBadge } from '../common/Badges';
import { 
  ShieldAlert, AlertTriangle, CheckCircle2, 
  BarChart3, PieChart, Layers, Building2, 
  ExternalLink, RefreshCw, AlertCircle, Info
} from 'lucide-react';

interface RiskAnalyticsProps {
  cses: CSEProfile[];
  analysisRunId?: string;
  onSelectCSE: (cse: CSEProfile) => void;
}

export const RiskAnalytics: React.FC<RiskAnalyticsProps> = ({
  cses,
  analysisRunId,
  onSelectCSE
}) => {
  const [riskScores, setRiskScores] = useState<RiskScoreDetail[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCseId, setSelectedCseId] = useState<string>('');
  const [sortBy, setSortBy] = useState<'score' | 'name' | 'band'>('score');

  const loadRiskScores = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchRiskScoresForRun(analysisRunId);
      setRiskScores(data);
      if (data.length > 0 && !selectedCseId) {
        const sorted = [...data].sort((a, b) => (b.normalized_score || 0) - (a.normalized_score || 0));
        setSelectedCseId(sorted[0].cse_id);
      }
    } catch (err: any) {
      console.error('Failed to load risk scores:', err);
      setError(err.message || 'Failed to load supervisory risk analytics data.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadRiskScores();
  }, [analysisRunId]);

  // Combine CSE profile info with RiskScore info
  const enrichedCSEs = useMemo(() => {
    const riskMap = new Map<string, RiskScoreDetail>();
    riskScores.forEach(r => riskMap.set(r.cse_id, r));

    return cses.map(cse => {
      const r = riskMap.get(cse.cse_id);
      const score = r ? r.normalized_score : (cse.risk_score || 0);
      const band = r ? r.risk_band : (cse.risk_band || 'LOW');
      const breakdown = r?.component_breakdown || {};
      
      let primaryDriver = 'Baseline Operational Noise';
      let maxVal = -1;
      const factorLabels: Record<string, string> = {
        execution_gap: 'Execution Gap (Delayed / Missing Response)',
        negative_space: 'Negative Space (Silent Telemetry Drop)',
        peer_deviation: 'Peer Deviation (Statistical Sector Outlier)',
        investigation_anomaly: 'Investigation Anomaly (Suspicious Rapid Closure)',
        asset_criticality: 'High Asset Criticality Exposure'
      };

      Object.entries(breakdown).forEach(([key, val]) => {
        if (typeof val === 'number' && val > maxVal && val > 5) {
          maxVal = val;
          primaryDriver = factorLabels[key] || key.replace('_', ' ').toUpperCase();
        }
      });

      return {
        ...cse,
        score,
        band,
        breakdown,
        primaryDriver,
        confidence: r?.overall_confidence ?? 1.0,
        riskDetail: r
      };
    }).sort((a, b) => {
      if (sortBy === 'score') return b.score - a.score;
      if (sortBy === 'band') return b.band.localeCompare(a.band);
      return a.name.localeCompare(b.name);
    });
  }, [cses, riskScores, sortBy]);

  const bandCounts = useMemo(() => {
    const counts = { CRITICAL: 0, HIGH: 0, MODERATE: 0, LOW: 0 };
    enrichedCSEs.forEach(c => {
      const b = (c.band || 'LOW').toUpperCase();
      if (b in counts) {
        counts[b as keyof typeof counts]++;
      } else if (b === 'MEDIUM') {
        counts.MODERATE++;
      } else {
        counts.LOW++;
      }
    });
    return counts;
  }, [enrichedCSEs]);

  const histogramBuckets = useMemo(() => {
    const buckets = [
      { label: '0 – 24 (Low)', min: 0, max: 24.9, count: 0, color: 'bg-emerald-500', border: 'border-emerald-500/30' },
      { label: '25 – 49 (Moderate)', min: 25, max: 49.9, count: 0, color: 'bg-sky-500', border: 'border-sky-500/30' },
      { label: '50 – 74 (High)', min: 50, max: 74.9, count: 0, color: 'bg-amber-500', border: 'border-amber-500/30' },
      { label: '75 – 100 (Critical)', min: 75, max: 100, count: 0, color: 'bg-rose-500', border: 'border-rose-500/30' }
    ];
    enrichedCSEs.forEach(c => {
      const s = c.score;
      const b = buckets.find(b => s >= b.min && s <= b.max);
      if (b) b.count++;
      else if (s >= 100) buckets[3].count++;
      else buckets[0].count++;
    });
    return buckets;
  }, [enrichedCSEs]);

  const activeSelectedCSE = useMemo(() => {
    if (!selectedCseId && enrichedCSEs.length > 0) return enrichedCSEs[0];
    return enrichedCSEs.find(c => c.cse_id === selectedCseId) || enrichedCSEs[0] || null;
  }, [selectedCseId, enrichedCSEs]);

  const totalEntities = enrichedCSEs.length;

  if (error) {
    return (
      <div className="bg-rose-950/40 border border-rose-800/80 rounded-xl p-6 font-mono text-center space-y-4">
        <div className="flex items-center justify-center gap-2 text-rose-400">
          <AlertCircle className="w-6 h-6" />
          <h3 className="text-sm font-bold uppercase tracking-wider">Unable to load supervisory risk analytics</h3>
        </div>
        <p className="text-xs text-rose-200 max-w-lg mx-auto">
          Endpoint returned an error: {error}
        </p>
        <button
          onClick={loadRiskScores}
          className="px-4 py-2 bg-rose-900 hover:bg-rose-800 text-white font-bold rounded-lg text-xs transition inline-flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          Retry Risk Analytics
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Header & Context Banner */}
      <div className="bg-slate-900/90 border border-cyan-800/40 rounded-lg p-4 font-mono text-xs text-slate-300 flex flex-wrap items-center justify-between gap-4 shadow-md">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-cyan-950 border border-cyan-700/50 rounded text-cyan-400">
            <BarChart3 className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-cyan-300">SUPERVISORY RISK ANALYTICS:</span>
              <span className="text-white font-mono bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                {analysisRunId || 'Active Analysis Run'}
              </span>
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5 flex items-center gap-4">
              <span>Monitored Entities: <strong className="text-slate-200">{totalEntities} Critical Sector Entities</strong></span>
              <span>Methodology: <strong className="text-cyan-400">5-Factor Deterministic Supervisory Risk Model</strong></span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadRiskScores}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-cyan-400' : ''}`} />
            <span>Recalculate View</span>
          </button>
        </div>
      </div>

      {/* Top Visualizations Grid: Risk Band Donut & Score Histogram */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Component 1: Risk Band Distribution */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-4 font-mono shadow-md">
          <div className="flex items-center justify-between text-xs text-slate-200 font-bold uppercase tracking-wider border-b border-slate-800 pb-3">
            <span className="flex items-center gap-2">
              <PieChart className="w-4 h-4 text-cyan-400" />
              Supervisory Risk Band Distribution — CSE Risk Scores
            </span>
            <span className="text-slate-400 font-normal">{totalEntities} Total Entities</span>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-1">
            <div className="p-3 bg-slate-950 border border-rose-900/60 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-rose-400 font-bold uppercase">Critical (75–100)</span>
                <ShieldAlert className="w-4 h-4 text-rose-400" />
              </div>
              <div className="text-2xl font-bold text-white mt-1">{bandCounts.CRITICAL}</div>
              <div className="text-[10px] text-slate-400 mt-1">
                {totalEntities > 0 ? ((bandCounts.CRITICAL / totalEntities) * 100).toFixed(1) : 0}% of portfolio
              </div>
              <div className="w-full bg-slate-900 h-1.5 rounded-full mt-2 overflow-hidden">
                <div 
                  className="bg-rose-500 h-full rounded-full transition-all duration-500"
                  style={{ width: `${totalEntities > 0 ? (bandCounts.CRITICAL / totalEntities) * 100 : 0}%` }}
                />
              </div>
            </div>

            <div className="p-3 bg-slate-950 border border-amber-900/60 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-amber-400 font-bold uppercase">High (50–74)</span>
                <AlertTriangle className="w-4 h-4 text-amber-400" />
              </div>
              <div className="text-2xl font-bold text-white mt-1">{bandCounts.HIGH}</div>
              <div className="text-[10px] text-slate-400 mt-1">
                {totalEntities > 0 ? ((bandCounts.HIGH / totalEntities) * 100).toFixed(1) : 0}% of portfolio
              </div>
              <div className="w-full bg-slate-900 h-1.5 rounded-full mt-2 overflow-hidden">
                <div 
                  className="bg-amber-500 h-full rounded-full transition-all duration-500"
                  style={{ width: `${totalEntities > 0 ? (bandCounts.HIGH / totalEntities) * 100 : 0}%` }}
                />
              </div>
            </div>

            <div className="p-3 bg-slate-950 border border-sky-900/60 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-sky-400 font-bold uppercase">Moderate (25–49)</span>
                <Layers className="w-4 h-4 text-sky-400" />
              </div>
              <div className="text-2xl font-bold text-white mt-1">{bandCounts.MODERATE}</div>
              <div className="text-[10px] text-slate-400 mt-1">
                {totalEntities > 0 ? ((bandCounts.MODERATE / totalEntities) * 100).toFixed(1) : 0}% of portfolio
              </div>
              <div className="w-full bg-slate-900 h-1.5 rounded-full mt-2 overflow-hidden">
                <div 
                  className="bg-sky-500 h-full rounded-full transition-all duration-500"
                  style={{ width: `${totalEntities > 0 ? (bandCounts.MODERATE / totalEntities) * 100 : 0}%` }}
                />
              </div>
            </div>

            <div className="p-3 bg-slate-950 border border-emerald-900/60 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-emerald-400 font-bold uppercase">Low (&lt;25)</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="text-2xl font-bold text-white mt-1">{bandCounts.LOW}</div>
              <div className="text-[10px] text-slate-400 mt-1">
                {totalEntities > 0 ? ((bandCounts.LOW / totalEntities) * 100).toFixed(1) : 0}% of portfolio
              </div>
              <div className="w-full bg-slate-900 h-1.5 rounded-full mt-2 overflow-hidden">
                <div 
                  className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                  style={{ width: `${totalEntities > 0 ? (bandCounts.LOW / totalEntities) * 100 : 0}%` }}
                />
              </div>
            </div>
          </div>

          <div className="text-[11px] text-slate-400 pt-1 flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
            <span>Measures composite risk per organization across all assets, findings, and peer benchmarks.</span>
          </div>
        </div>

        {/* Component 2: Risk Score Distribution Histogram */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-4 font-mono shadow-md">
          <div className="flex items-center justify-between text-xs text-slate-200 font-bold uppercase tracking-wider border-b border-slate-800 pb-3">
            <span className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-cyan-400" />
              Risk Score Distribution (0–100 Scale)
            </span>
            <span className="text-slate-400 font-normal">Histogram</span>
          </div>

          <div className="space-y-3 pt-2">
            {histogramBuckets.map((bucket, idx) => {
              const pct = totalEntities > 0 ? (bucket.count / totalEntities) * 100 : 0;
              return (
                <div key={idx} className="space-y-1.5">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-300 font-semibold">{bucket.label}</span>
                    <span className="text-white font-bold">
                      {bucket.count} CSEs <span className="text-slate-400 text-[10px]">({pct.toFixed(0)}%)</span>
                    </span>
                  </div>
                  <div className="w-full bg-slate-950 h-3 rounded border border-slate-800 overflow-hidden flex">
                    <div
                      className={`${bucket.color} h-full transition-all duration-500`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          <div className="text-[11px] text-slate-400 pt-2 border-t border-slate-800/80 flex items-center justify-between">
            <span>Distribution Mean: <strong className="text-cyan-400">{(enrichedCSEs.reduce((sum, c) => sum + c.score, 0) / Math.max(1, totalEntities)).toFixed(1)}/100</strong></span>
            <span>Deterministic Non-Parametric Model</span>
          </div>
        </div>
      </div>

      {/* Component 4: 5-Component Risk Decomposition Explorer */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-4 font-mono shadow-md">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
          <div>
            <h3 className="text-xs font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-2">
              <Layers className="w-4 h-4 text-cyan-400" />
              5-Component Supervisory Risk Decomposition
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Mathematical formula: Score = 0.30·EG + 0.25·NS + 0.20·PD + 0.15·IA + 0.10·AC
            </p>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-xs text-slate-400 font-semibold">Inspect Entity:</label>
            <select
              value={activeSelectedCSE?.cse_id || ''}
              onChange={e => setSelectedCseId(e.target.value)}
              className="bg-slate-950 border border-slate-700 text-white text-xs px-3 py-1.5 rounded focus:outline-none focus:border-cyan-400"
            >
              {enrichedCSEs.map(c => (
                <option key={c.cse_id} value={c.cse_id}>
                  {c.name} ({c.score.toFixed(1)} - {c.band})
                </option>
              ))}
            </select>
          </div>
        </div>

        {activeSelectedCSE && (
          <div className="space-y-4 pt-1">
            <div className="p-3.5 bg-slate-950 border border-slate-800 rounded-lg flex flex-wrap items-center justify-between gap-4">
              <div>
                <div className="text-sm font-bold text-white">{activeSelectedCSE.name}</div>
                <div className="text-xs text-slate-400 flex items-center gap-3 mt-0.5">
                  <span>Sector: <strong className="text-slate-200">{activeSelectedCSE.sector}</strong></span>
                  <span>Type: <strong className="text-slate-200">{activeSelectedCSE.entity_type}</strong></span>
                  <span>Tier: <strong className="text-slate-200">{activeSelectedCSE.size_tier}</strong></span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <div className="text-[10px] text-slate-400 uppercase">Normalized Score</div>
                  <div className="text-2xl font-bold text-cyan-400">{activeSelectedCSE.score.toFixed(1)}<span className="text-xs text-slate-400">/100</span></div>
                </div>
                <PriorityBandBadge band={activeSelectedCSE.band} />
              </div>
            </div>

            {/* Component Factor Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-3 text-xs">
              <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg space-y-1.5">
                <div className="text-[10px] text-sky-400 font-bold uppercase">Execution Gap (30%)</div>
                <div className="text-xl font-bold text-white">
                  {(activeSelectedCSE.breakdown?.execution_gap ?? 0).toFixed(1)}
                </div>
                <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
                  <div 
                    className="bg-sky-500 h-full rounded-full"
                    style={{ width: `${Math.min(100, (activeSelectedCSE.breakdown?.execution_gap ?? 0))}%` }}
                  />
                </div>
                <p className="text-[10px] text-slate-400 leading-tight">Delayed or omitted SOC triage vs expected procedure.</p>
              </div>

              <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg space-y-1.5">
                <div className="text-[10px] text-purple-400 font-bold uppercase">Negative Space (25%)</div>
                <div className="text-xl font-bold text-white">
                  {(activeSelectedCSE.breakdown?.negative_space ?? 0).toFixed(1)}
                </div>
                <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
                  <div 
                    className="bg-purple-500 h-full rounded-full"
                    style={{ width: `${Math.min(100, (activeSelectedCSE.breakdown?.negative_space ?? 0))}%` }}
                  />
                </div>
                <p className="text-[10px] text-slate-400 leading-tight">Telemetry gaps and missing expected audit records.</p>
              </div>

              <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg space-y-1.5">
                <div className="text-[10px] text-amber-400 font-bold uppercase">Peer Deviation (20%)</div>
                <div className="text-xl font-bold text-white">
                  {(activeSelectedCSE.breakdown?.peer_deviation ?? 0).toFixed(1)}
                </div>
                <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
                  <div 
                    className="bg-amber-500 h-full rounded-full"
                    style={{ width: `${Math.min(100, (activeSelectedCSE.breakdown?.peer_deviation ?? 0))}%` }}
                  />
                </div>
                <p className="text-[10px] text-slate-400 leading-tight">Statistical deviation from peer group baseline.</p>
              </div>

              <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg space-y-1.5">
                <div className="text-[10px] text-rose-400 font-bold uppercase">Investigation Anomaly (15%)</div>
                <div className="text-xl font-bold text-white">
                  {(activeSelectedCSE.breakdown?.investigation_anomaly ?? 0).toFixed(1)}
                </div>
                <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
                  <div 
                    className="bg-rose-500 h-full rounded-full"
                    style={{ width: `${Math.min(100, (activeSelectedCSE.breakdown?.investigation_anomaly ?? 0))}%` }}
                  />
                </div>
                <p className="text-[10px] text-slate-400 leading-tight">Suspiciously rapid closures or triage omissions.</p>
              </div>

              <div className="p-3 bg-slate-950 border border-emerald-900/60 rounded-lg space-y-1.5">
                <div className="text-[10px] text-emerald-400 font-bold uppercase">Asset Criticality (10%)</div>
                <div className="text-xl font-bold text-white">
                  {(activeSelectedCSE.breakdown?.asset_criticality ?? 0).toFixed(1)}
                </div>
                <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
                  <div 
                    className="bg-emerald-500 h-full rounded-full"
                    style={{ width: `${Math.min(100, (activeSelectedCSE.breakdown?.asset_criticality ?? 0))}%` }}
                  />
                </div>
                <p className="text-[10px] text-slate-400 leading-tight">National critical infrastructure asset weighting.</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Component 3: Top Risk CSEs Ranked Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-4 font-mono shadow-md">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
          <div>
            <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
              <Building2 className="w-4 h-4 text-cyan-400" />
              Top Risk Critical Sector Entities (Ranked Portfolio)
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Sourced directly from canonical RiskScore records computed by the Supervisory Risk Engine.
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-400">Sort by:</span>
            <button
              onClick={() => setSortBy('score')}
              className={`px-2.5 py-1 rounded border transition ${
                sortBy === 'score' ? 'bg-cyan-950 border-cyan-700 text-cyan-300 font-bold' : 'border-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              Risk Score
            </button>
            <button
              onClick={() => setSortBy('name')}
              className={`px-2.5 py-1 rounded border transition ${
                sortBy === 'name' ? 'bg-cyan-950 border-cyan-700 text-cyan-300 font-bold' : 'border-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              Entity Name
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 text-[11px] uppercase bg-slate-950/50">
                <th className="p-3">Rank</th>
                <th className="p-3">Critical Sector Entity</th>
                <th className="p-3">Sector / Type</th>
                <th className="p-3 text-center">Assets</th>
                <th className="p-3 text-center">Findings</th>
                <th className="p-3 text-right">Risk Score</th>
                <th className="p-3 text-center">Risk Band</th>
                <th className="p-3">Primary Risk Driver</th>
                <th className="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {enrichedCSEs.length === 0 ? (
                <tr>
                  <td colSpan={9} className="p-8 text-center text-slate-400">
                    No CSE risk evaluations found for this analysis run.
                  </td>
                </tr>
              ) : (
                enrichedCSEs.map((cse, idx) => (
                  <tr
                    key={cse.cse_id}
                    className={`hover:bg-slate-800/50 transition cursor-pointer ${
                      activeSelectedCSE?.cse_id === cse.cse_id ? 'bg-cyan-950/20' : ''
                    }`}
                    onClick={() => setSelectedCseId(cse.cse_id)}
                  >
                    <td className="p-3 font-bold text-slate-400">#{idx + 1}</td>
                    <td className="p-3 font-semibold text-white">
                      <div className="flex items-center gap-2">
                        <span>{cse.name}</span>
                      </div>
                    </td>
                    <td className="p-3 text-slate-300">
                      <div>{cse.sector}</div>
                      <div className="text-[10px] text-slate-500">{cse.entity_type}</div>
                    </td>
                    <td className="p-3 text-center text-slate-300">{cse.asset_count}</td>
                    <td className="p-3 text-center">
                      <span className={`font-bold ${cse.finding_count > 0 ? 'text-amber-400' : 'text-slate-500'}`}>
                        {cse.finding_count}
                      </span>
                    </td>
                    <td className="p-3 text-right font-bold text-white">
                      <span className={`px-2 py-0.5 rounded ${
                        cse.score >= 75 ? 'bg-rose-950 text-rose-300 border border-rose-800' :
                        cse.score >= 50 ? 'bg-amber-950 text-amber-300 border border-amber-800' :
                        cse.score >= 25 ? 'bg-sky-950 text-sky-300 border border-sky-800' :
                        'bg-emerald-950 text-emerald-300 border border-emerald-800'
                      }`}>
                        {cse.score.toFixed(1)}
                      </span>
                    </td>
                    <td className="p-3 text-center">
                      <PriorityBandBadge band={cse.band} />
                    </td>
                    <td className="p-3 text-slate-300 max-w-xs truncate" title={cse.primaryDriver}>
                      {cse.primaryDriver}
                    </td>
                    <td className="p-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectCSE(cse);
                        }}
                        className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded text-[11px] font-semibold transition inline-flex items-center gap-1"
                      >
                        <span>Profile</span>
                        <ExternalLink className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
