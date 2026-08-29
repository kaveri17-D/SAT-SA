import React, { useState } from 'react';
import { updateQueueItemStatus } from '../../api/client';
import { ShieldCheck, Eye, ShieldAlert, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

interface ModalProps {
  queueItemId: string;
  currentStatus: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (updatedStatus: string) => void;
}

export const ExaminerActionModal: React.FC<ModalProps> = ({
  queueItemId,
  currentStatus,
  isOpen,
  onClose,
  onSuccess
}) => {
  const [status, setStatus] = useState<string>(currentStatus);
  const [notes, setNotes] = useState<string>('');
  const [userId, setUserId] = useState<string>('EXAMINER_NCIIPC_01');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const res = await updateQueueItemStatus(queueItemId, status, notes, userId);
      onSuccess(res.status);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to update examiner status.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const statusOptions = [
    { value: 'IN_REVIEW', label: 'In Review', icon: <Eye className="w-4 h-4 text-blue-400" />, desc: 'Assign for active supervisory examination' },
    { value: 'ESCALATED', label: 'Escalated', icon: <ShieldAlert className="w-4 h-4 text-purple-400" />, desc: 'Escalate finding for senior tribunal review' },
    { value: 'RESOLVED', label: 'Resolved', icon: <CheckCircle className="w-4 h-4 text-emerald-400" />, desc: 'Confirmed anomaly and logged corrective action' },
    { value: 'DISMISSED', label: 'Dismissed', icon: <XCircle className="w-4 h-4 text-slate-400" />, desc: 'Dismiss finding after verified exception audit' }
  ];

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-lg max-w-lg w-full p-6 shadow-2xl space-y-5">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded bg-cyan-950 border border-cyan-800 flex items-center justify-center text-cyan-400 font-bold">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-mono font-bold text-white uppercase tracking-wider">
              Record Examiner Supervisory Action
            </h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white font-bold text-sm">✕</button>
        </div>

        {error && (
          <div className="bg-rose-950/80 border border-rose-800 text-rose-200 p-3 rounded text-xs font-mono flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-xs font-mono">
          <div className="space-y-1.5">
            <label className="text-slate-300 font-semibold uppercase">Examiner Handle / ID</label>
            <input
              type="text"
              value={userId}
              onChange={e => setUserId(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              required
            />
          </div>

          <div className="space-y-2">
            <label className="text-slate-300 font-semibold uppercase">Target Disposition Status</label>
            <div className="grid grid-cols-2 gap-2">
              {statusOptions.map(opt => (
                <button
                  type="button"
                  key={opt.value}
                  onClick={() => setStatus(opt.value)}
                  className={`p-3 rounded border text-left flex flex-col justify-between transition ${
                    status === opt.value
                      ? 'bg-cyan-950/60 border-cyan-600 text-white shadow-md'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:bg-slate-800'
                  }`}
                >
                  <div className="flex items-center gap-2 font-bold text-xs">
                    {opt.icon}
                    <span>{opt.label}</span>
                  </div>
                  <p className="text-[10px] text-slate-400 mt-1 leading-tight">{opt.desc}</p>
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-slate-300 font-semibold uppercase">Examiner Audit Notes & Justification</label>
            <textarea
              value={notes}
              onChange={e => setNotes(e.target.value)}
              rows={3}
              placeholder="Record mandatory rationale for status update (recorded in immutable AuditLog)..."
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              required
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-bold shadow-lg shadow-cyan-600/20 disabled:opacity-50"
            >
              {isSubmitting ? 'Recording Audit...' : 'Commit Status Action'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
