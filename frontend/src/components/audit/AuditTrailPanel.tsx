import React from 'react';
import { AuditLogEntry } from '../../types/api';
import { History, User, Clock, MessageSquare } from 'lucide-react';
import { StatusBadge } from '../common/Badges';

interface AuditPanelProps {
  logs: AuditLogEntry[];
}

export const AuditTrailPanel: React.FC<AuditPanelProps> = ({ logs }) => {
  if (!logs || logs.length === 0) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 text-xs font-mono text-slate-400">
        No examiner status transition logs recorded for this item.
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-3">
      <h4 className="text-xs font-mono font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-2">
        <History className="w-4 h-4 text-cyan-400" />
        Examiner Action & Status Audit History
      </h4>

      <div className="space-y-2.5">
        {logs.map((log) => {
          const details = log.details || {};
          return (
            <div key={log.audit_id} className="bg-slate-950 border border-slate-800 rounded p-3 text-xs font-mono space-y-1.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="flex items-center gap-1 text-slate-300 font-bold">
                    <User className="w-3.5 h-3.5 text-cyan-400" />
                    {log.user_id}
                  </span>
                  <span className="text-slate-500">|</span>
                  <span className="text-slate-400">{log.action}</span>
                </div>
                <div className="flex items-center gap-1 text-slate-400 text-[11px]">
                  <Clock className="w-3 h-3 text-slate-500" />
                  {new Date(log.timestamp).toLocaleString()}
                </div>
              </div>

              {details.old_status && details.new_status && (
                <div className="flex items-center gap-2 pt-1">
                  <span className="text-slate-400">Status Change:</span>
                  <StatusBadge status={details.old_status} />
                  <span className="text-slate-500">➔</span>
                  <StatusBadge status={details.new_status} />
                </div>
              )}

              {details.notes && (
                <div className="flex items-start gap-1.5 text-slate-300 bg-slate-900 border border-slate-800/80 p-2 rounded text-[11px] mt-1">
                  <MessageSquare className="w-3.5 h-3.5 text-cyan-400 shrink-0 mt-0.5" />
                  <span>{details.notes}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
