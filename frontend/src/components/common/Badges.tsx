import React from 'react';
import { AlertTriangle, CheckCircle, ShieldAlert, Clock, Eye, XCircle } from 'lucide-react';

export const PriorityBandBadge: React.FC<{ band: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'; score?: number }> = ({ band, score }) => {
  const styles = {
    CRITICAL: 'bg-rose-950/80 text-rose-300 border-rose-800/80 shadow-rose-900/20',
    HIGH: 'bg-amber-950/80 text-amber-300 border-amber-800/80 shadow-amber-900/20',
    MEDIUM: 'bg-yellow-950/80 text-yellow-300 border-yellow-800/80 shadow-yellow-900/20',
    LOW: 'bg-slate-800/80 text-slate-300 border-slate-700/80 shadow-slate-900/20'
  };

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono font-bold border shadow-sm ${styles[band] || styles.LOW}`}>
      <ShieldAlert className="w-3.5 h-3.5" />
      <span>{band}</span>
      {score !== undefined && <span className="opacity-80">({score.toFixed(1)})</span>}
    </span>
  );
};

export const SeverityBadge: React.FC<{ severity: string }> = ({ severity }) => {
  const sev = severity.toUpperCase();
  const styles: Record<string, string> = {
    CRITICAL: 'bg-red-950 text-red-300 border-red-800',
    HIGH: 'bg-orange-950 text-orange-300 border-orange-800',
    MEDIUM: 'bg-amber-950 text-amber-300 border-amber-800',
    LOW: 'bg-slate-800 text-slate-300 border-slate-700'
  };

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-semibold border ${styles[sev] || styles.LOW}`}>
      <AlertTriangle className="w-3 h-3" />
      <span>{sev}</span>
    </span>
  );
};

export const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const st = status.toUpperCase();
  const config: Record<string, { style: string; icon: React.ReactNode }> = {
    NEW: { style: 'bg-cyan-950 text-cyan-300 border-cyan-800', icon: <Clock className="w-3 h-3 text-cyan-400" /> },
    IN_REVIEW: { style: 'bg-blue-950 text-blue-300 border-blue-800', icon: <Eye className="w-3 h-3 text-blue-400" /> },
    ESCALATED: { style: 'bg-purple-950 text-purple-300 border-purple-800', icon: <ShieldAlert className="w-3 h-3 text-purple-400" /> },
    RESOLVED: { style: 'bg-emerald-950 text-emerald-300 border-emerald-800', icon: <CheckCircle className="w-3 h-3 text-emerald-400" /> },
    DISMISSED: { style: 'bg-slate-800 text-slate-400 border-slate-700', icon: <XCircle className="w-3 h-3 text-slate-400" /> }
  };

  const item = config[st] || config.NEW;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-semibold border ${item.style}`}>
      {item.icon}
      <span>{st}</span>
    </span>
  );
};

export const CompletenessGauge: React.FC<{ score: number }> = ({ score }) => {
  const isHigh = score >= 80;
  const isMed = score >= 50 && score < 80;
  const color = isHigh ? 'text-emerald-400 bg-emerald-950 border-emerald-800' : isMed ? 'text-amber-400 bg-amber-950 border-amber-800' : 'text-rose-400 bg-rose-950 border-rose-800';

  return (
    <div className="flex items-center gap-2">
      <div className="w-16 bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
        <div className={`h-full ${isHigh ? 'bg-emerald-500' : isMed ? 'bg-amber-500' : 'bg-rose-500'}`} style={{ width: `${Math.min(100, Math.max(0, score))}%` }} />
      </div>
      <span className={`text-[11px] font-mono font-bold px-1.5 py-0.2 rounded border ${color}`}>
        {score.toFixed(0)}%
      </span>
    </div>
  );
};
