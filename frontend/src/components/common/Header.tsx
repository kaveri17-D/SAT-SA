import React from 'react';
import { ShieldCheck, Lock, Activity, RefreshCw, Sun, Moon } from 'lucide-react';

interface HeaderProps {
  onRefresh?: () => void;
  isRefreshing?: boolean;
  theme?: 'dark' | 'light';
  onToggleTheme?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onRefresh, isRefreshing, theme = 'dark', onToggleTheme }) => {
  return (
    <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-40 px-6 py-3.5 flex items-center justify-between shadow-md">
      <div className="flex items-center space-x-3.5">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white shadow-lg shadow-cyan-500/20 font-bold">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold tracking-tight text-white">
              SAT-SA
            </h1>
            <span className="text-[10px] font-mono tracking-wider font-bold text-cyan-400 bg-cyan-950/80 border border-cyan-800/80 px-2 py-0.5 rounded">
              SUPERVISORY CONSOLE
            </span>
          </div>
          <p className="text-xs text-slate-400">Smart Assessment Tool for Security Analytics — NCIIPC Supervisory Intelligence</p>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition disabled:opacity-50"
            title="Reload data from backend"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-cyan-400' : ''}`} />
            <span>Refresh Data</span>
          </button>
        )}

        {onToggleTheme && (
          <button
            onClick={onToggleTheme}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
            title={theme === 'dark' ? 'Switch to Daylight / Presentation Mode' : 'Switch to Dark Mode'}
          >
            {theme === 'dark' ? (
              <>
                <Sun className="w-3.5 h-3.5 text-amber-400" />
                <span>Daylight</span>
              </>
            ) : (
              <>
                <Moon className="w-3.5 h-3.5 text-sky-400" />
                <span>Dark</span>
              </>
            )}
          </button>
        )}

        <div className="flex items-center gap-2 text-xs font-mono text-slate-300 bg-slate-950 px-3 py-1.5 rounded border border-slate-800">
          <Lock className="w-3.5 h-3.5 text-emerald-400" />
          <span>Air-Gapped Offline</span>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-slate-300 bg-slate-950 px-3 py-1.5 rounded border border-slate-800">
          <Activity className="w-3.5 h-3.5 text-cyan-400" />
          <span>Examiner Tier-1</span>
        </div>
      </div>
    </header>
  );
};
