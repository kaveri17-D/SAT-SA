import React, { useEffect, useState } from 'react';
import { fetchHealth } from '../api/client';
import { HealthStatus as HealthStatusType } from '../types/api';
import { Shield, CheckCircle2, AlertTriangle, Cpu, Database, WifiOff } from 'lucide-react';

export const HealthStatusCard: React.FC = () => {
  const [health, setHealth] = useState<HealthStatusType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadHealth = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchHealth();
      setHealth(data);
    } catch (err: any) {
      setError(err.message || 'Unable to connect to supervisory backend service');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHealth();
  }, []);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-cyan-500/10 rounded-md text-cyan-400">
            <Shield className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-100">Supervisory System Health</h2>
            <p className="text-xs text-slate-400 font-mono">SAT-SA Air-Gapped Supervisory Node</p>
          </div>
        </div>
        <button
          onClick={loadHealth}
          className="px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 transition"
        >
          Re-check Node
        </button>
      </div>

      {loading && (
        <div className="py-8 text-center text-slate-400 text-sm animate-pulse">
          Querying supervisory backend node...
        </div>
      )}

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded text-rose-400 text-sm flex items-start space-x-2">
          <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold block">Backend Connection Error</span>
            <span>{error}</span>
          </div>
        </div>
      )}

      {health && !loading && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-2">
          <div className="bg-slate-950/60 p-3 rounded border border-slate-800">
            <div className="text-xs text-slate-400 flex items-center gap-1.5 mb-1">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> API Status
            </div>
            <div className="text-sm font-semibold text-emerald-400 font-mono capitalize">
              {health.status}
            </div>
          </div>

          <div className="bg-slate-950/60 p-3 rounded border border-slate-800">
            <div className="text-xs text-slate-400 flex items-center gap-1.5 mb-1">
              <Database className="w-3.5 h-3.5 text-cyan-400" /> Database
            </div>
            <div className={`text-sm font-semibold font-mono ${health.database === 'healthy' ? 'text-cyan-400' : 'text-amber-400'}`}>
              {health.database}
            </div>
          </div>

          <div className="bg-slate-950/60 p-3 rounded border border-slate-800">
            <div className="text-xs text-slate-400 flex items-center gap-1.5 mb-1">
              <WifiOff className="w-3.5 h-3.5 text-purple-400" /> Air-Gap Mode
            </div>
            <div className="text-sm font-semibold text-purple-400 font-mono">
              {health.airgap_mode ? 'ENFORCED (OFFLINE)' : 'ONLINE'}
            </div>
          </div>

          <div className="bg-slate-950/60 p-3 rounded border border-slate-800">
            <div className="text-xs text-slate-400 flex items-center gap-1.5 mb-1">
              <Cpu className="w-3.5 h-3.5 text-blue-400" /> Version
            </div>
            <div className="text-sm font-semibold text-slate-200 font-mono">
              v{health.version} ({health.environment})
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
