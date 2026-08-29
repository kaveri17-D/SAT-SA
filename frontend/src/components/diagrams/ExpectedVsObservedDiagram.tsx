import React from 'react';
import { ArrowRight, CheckCircle2, XCircle, AlertTriangle, FileText } from 'lucide-react';
import { GraphPathInfo } from '../../types/api';

interface DiagramProps {
  pathInfo?: GraphPathInfo | null;
  expectedBehaviour?: string;
  observedBehaviour?: string;
  deviation?: string;
}

export const ExpectedVsObservedDiagram: React.FC<DiagramProps> = ({
  pathInfo,
  expectedBehaviour,
  observedBehaviour,
  deviation
}) => {
  const expectedSteps = pathInfo?.expected_path || ['ALERT', 'INVESTIGATION', 'ESCALATION', 'CASE', 'CLOSURE'];
  const observedSteps = pathInfo?.observed_sequence || ['ALERT', 'INVESTIGATION', 'CASE', 'CLOSURE'];
  const missingTransitions = pathInfo?.missing_transitions || [];
  const isAnomalous = pathInfo?.is_anomalous || missingTransitions.length > 0;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <h3 className="text-xs font-mono font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-2">
          <FileText className="w-4 h-4 text-cyan-400" />
          Supervisory Workflow Transition Analysis
        </h3>
        {isAnomalous ? (
          <span className="inline-flex items-center gap-1 text-xs font-mono font-bold text-rose-400 bg-rose-950 border border-rose-800 px-2.5 py-0.5 rounded">
            <XCircle className="w-3.5 h-3.5" /> Workflow Path Anomaly
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-xs font-mono font-bold text-emerald-400 bg-emerald-950 border border-emerald-800 px-2.5 py-0.5 rounded">
            <CheckCircle2 className="w-3.5 h-3.5" /> Canonical Workflow Valid
          </span>
        )}
      </div>

      {/* Expected Path Sequence */}
      <div className="space-y-1.5">
        <div className="text-[11px] font-mono text-slate-400 font-semibold uppercase">Canonical Expected Workflow Path</div>
        <div className="flex items-center gap-2 overflow-x-auto py-2">
          {expectedSteps.map((step, idx) => (
            <React.Fragment key={idx}>
              <div className="flex items-center gap-1.5 bg-slate-950 border border-emerald-800/80 px-3 py-1.5 rounded text-xs font-mono font-bold text-emerald-300">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>{step}</span>
              </div>
              {idx < expectedSteps.length - 1 && <ArrowRight className="w-4 h-4 text-slate-600 shrink-0" />}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Observed Path Sequence */}
      <div className="space-y-1.5">
        <div className="text-[11px] font-mono text-slate-400 font-semibold uppercase">Actual Observed Workflow Path</div>
        <div className="flex items-center gap-2 overflow-x-auto py-2">
          {observedSteps.map((step, idx) => {
            const isMissingStep = missingTransitions.some(m => m.to === step || m.from === step);
            return (
              <React.Fragment key={idx}>
                <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono font-bold border ${isMissingStep ? 'bg-slate-950 border-rose-800 text-rose-300' : 'bg-slate-950 border-slate-700 text-slate-200'}`}>
                  <span>{step}</span>
                </div>
                {idx < observedSteps.length - 1 && <ArrowRight className="w-4 h-4 text-slate-600 shrink-0" />}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Missing Transitions Callout */}
      {missingTransitions.length > 0 && (
        <div className="bg-rose-950/40 border border-rose-800/80 rounded-md p-3.5 space-y-1">
          <div className="text-xs font-mono font-bold text-rose-300 flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4 text-rose-400" />
            Detected Missing Workflow Transition
          </div>
          {missingTransitions.map((mt, i) => (
            <div key={i} className="text-xs text-rose-200 font-mono">
              ❌ Missing Transition: <span className="font-bold text-white">{mt.from} ➔ {mt.to}</span> ({mt.reason})
            </div>
          ))}
        </div>
      )}

      {/* Behaviour Description Details */}
      {(expectedBehaviour || observedBehaviour || deviation) && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 border-t border-slate-800/80 text-xs">
          {expectedBehaviour && (
            <div className="bg-slate-950 border border-slate-800 p-2.5 rounded">
              <div className="text-[10px] font-mono text-slate-400 uppercase font-semibold">Expected Behaviour</div>
              <p className="text-slate-200 mt-1">{expectedBehaviour}</p>
            </div>
          )}
          {observedBehaviour && (
            <div className="bg-slate-950 border border-slate-800 p-2.5 rounded">
              <div className="text-[10px] font-mono text-slate-400 uppercase font-semibold">Observed Behaviour</div>
              <p className="text-slate-200 mt-1">{observedBehaviour}</p>
            </div>
          )}
          {deviation && (
            <div className="bg-rose-950/20 border border-rose-900/60 p-2.5 rounded">
              <div className="text-[10px] font-mono text-rose-400 uppercase font-semibold">Supervisory Deviation</div>
              <p className="text-rose-200 mt-1">{deviation}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
