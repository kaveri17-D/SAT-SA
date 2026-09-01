import React, { useState, useEffect } from 'react';
import {
  FileText,
  ShieldCheck,
  Download,
  Eye,
  AlertTriangle,
  CheckCircle2,
  Lock,
  RefreshCw,
  PlusCircle,
  X
} from 'lucide-react';
import {
  fetchReports,
  fetchReportDetail,
  generateReport,
  getReportExportUrl,
  fetchAuditLogs,
  verifyAuditTrail
} from '../../api/client';
import { ReportSummary, ReportDetail, AuditLogItem, AuditVerificationResult, CSEProfile } from '../../types/api';

interface ReportsDashboardProps {
  cses: CSEProfile[];
  analysisRunId?: string;
}

export const ReportsDashboard: React.FC<ReportsDashboardProps> = ({ cses, analysisRunId }) => {
  const [activeTab, setActiveTab] = useState<'REPORTS' | 'AUDIT'>('REPORTS');
  
  // Reports State
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [totalReports, setTotalReports] = useState(0);
  const [selectedReport, setSelectedReport] = useState<ReportDetail | null>(null);
  const [isLoadingReports, setIsLoadingReports] = useState(false);
  const [reportFilterType, setReportFilterType] = useState<string>('ALL');
  
  // Report Gen Modal
  const [showGenModal, setShowGenModal] = useState(false);
  const [genType, setGenType] = useState<string>('EXECUTIVE');
  const [genCseId, setGenCseId] = useState<string>('');
  const [genTitle, setGenTitle] = useState<string>('');
  const [genDesc, setGenDesc] = useState<string>('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);

  // Audit State
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [totalAuditLogs, setTotalAuditLogs] = useState(0);
  const [isLoadingAudit, setIsLoadingAudit] = useState(false);
  const [auditUserFilter, setAuditUserFilter] = useState('');
  const [auditActionFilter, setAuditActionFilter] = useState('');
  const [auditVerifyResult, setAuditVerifyResult] = useState<AuditVerificationResult | null>(null);
  const [isVerifyingAudit, setIsVerifyingAudit] = useState(false);
  const [selectedAuditLog, setSelectedAuditLog] = useState<AuditLogItem | null>(null);

  // Active Report Detail Tabs
  const [detailTab, setDetailTab] = useState<'OVERVIEW' | 'FINDINGS' | 'RISK' | 'EVIDENCE'>('OVERVIEW');

  const loadReports = async () => {
    setIsLoadingReports(true);
    try {
      const typeFilter = reportFilterType === 'ALL' ? undefined : reportFilterType;
      const res = await fetchReports({ report_type: typeFilter, limit: 50 });
      setReports(res.reports || []);
      setTotalReports(res.total_count || 0);
    } catch (err) {
      console.error('Failed to load reports:', err);
    } finally {
      setIsLoadingReports(false);
    }
  };

  const loadAuditLogs = async () => {
    setIsLoadingAudit(true);
    try {
      const res = await fetchAuditLogs({
        user_id: auditUserFilter || undefined,
        action: auditActionFilter || undefined,
        limit: 50
      });
      setAuditLogs(res.logs || []);
      setTotalAuditLogs(res.total_count || 0);
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    } finally {
      setIsLoadingAudit(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'REPORTS') {
      loadReports();
    } else {
      loadAuditLogs();
    }
  }, [activeTab, reportFilterType]);

  const handleOpenReport = async (id: string) => {
    try {
      const detail = await fetchReportDetail(id);
      setSelectedReport(detail);
      setDetailTab('OVERVIEW');
    } catch (err) {
      console.error('Failed to load report detail:', err);
    }
  };

  const handleGenerateReport = async (e?: React.FormEvent | React.MouseEvent) => {
    if (e) e.preventDefault();
    setIsGenerating(true);
    setGenError(null);
    try {
      console.log('Generating report with type:', genType, 'title:', genTitle);
      await generateReport({
        assessment_id: analysisRunId || 'latest',
        report_type: genType,
        cse_id: genCseId || undefined,
        title: genTitle || undefined,
        description: genDesc || undefined,
        generated_by: 'EXAMINER_NCIIPC'
      });
      setShowGenModal(false);
      setGenTitle('');
      setGenDesc('');
      await loadReports();
    } catch (err: any) {
      console.error('Report generation error in frontend:', err);
      setGenError(err.message || 'Failed to generate report.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleVerifyAudit = async () => {
    setIsVerifyingAudit(true);
    try {
      const res = await verifyAuditTrail();
      setAuditVerifyResult(res);
    } catch (err) {
      console.error('Failed to verify audit trail:', err);
    } finally {
      setIsVerifyingAudit(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header & Sub-Nav */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-slate-900/60 p-4 rounded-xl border border-slate-800 backdrop-blur">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <FileText className="w-6 h-6 text-sky-400" />
            Supervisory Reporting & Cryptographic Audit Ledger
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Immutable official assessment reports, SHA-256 evidence linking, and append-only cryptographic audit trail.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex bg-slate-950 p-1 rounded-lg border border-slate-800">
            <button
              onClick={() => setActiveTab('REPORTS')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                activeTab === 'REPORTS'
                  ? 'bg-sky-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Reports & Snapshots ({totalReports})
            </button>
            <button
              onClick={() => setActiveTab('AUDIT')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                activeTab === 'AUDIT'
                  ? 'bg-sky-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Audit Trail ({totalAuditLogs})
            </button>
          </div>

          {activeTab === 'REPORTS' ? (
            <button
              onClick={() => setShowGenModal(true)}
              className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white px-3.5 py-1.5 rounded-lg text-xs font-bold transition shadow-sm"
            >
              <PlusCircle className="w-4 h-4" />
              Generate Report
            </button>
          ) : (
            <button
              onClick={handleVerifyAudit}
              disabled={isVerifyingAudit}
              className="flex items-center gap-1.5 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white px-3.5 py-1.5 rounded-lg text-xs font-bold transition shadow-sm"
            >
              <ShieldCheck className="w-4 h-4" />
              {isVerifyingAudit ? 'Verifying Chain...' : 'Verify Audit Integrity'}
            </button>
          )}
        </div>
      </div>

      {/* KPI Cards Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-xl">
          <div className="text-[11px] font-mono uppercase text-slate-400">Total Snapshots</div>
          <div className="text-2xl font-bold text-slate-100 mt-1">{totalReports}</div>
          <div className="text-[10px] text-sky-400 mt-1 font-mono">Immutable SHA-256</div>
        </div>
        <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-xl">
          <div className="text-[11px] font-mono uppercase text-slate-400">Report Categories</div>
          <div className="text-2xl font-bold text-sky-400 mt-1">5 Types</div>
          <div className="text-[10px] text-slate-400 mt-1">Executive, Tech, Risk, Asset, Intel</div>
        </div>
        <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-xl">
          <div className="text-[11px] font-mono uppercase text-slate-400">Audit Events Chained</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">{totalAuditLogs}</div>
          <div className="text-[10px] text-emerald-500 mt-1 font-mono">Append-Only Cryptographic</div>
        </div>
        <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-xl">
          <div className="text-[11px] font-mono uppercase text-slate-400">Air-Gap Integrity</div>
          <div className="text-2xl font-bold text-purple-400 mt-1">STRICT_LOCAL</div>
          <div className="text-[10px] text-purple-300 mt-1 font-mono">Zero External Callouts</div>
        </div>
      </div>

      {/* TAB 1: REPORTS VIEW */}
      {activeTab === 'REPORTS' && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/40 p-3 rounded-lg border border-slate-800">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-slate-400 uppercase">Filter Type:</span>
              {['ALL', 'EXECUTIVE', 'TECHNICAL', 'RISK', 'ASSET', 'VULNERABILITY_THREAT_INTEL'].map((type) => (
                <button
                  key={type}
                  onClick={() => setReportFilterType(type)}
                  className={`px-2.5 py-1 text-[11px] font-mono rounded transition ${
                    reportFilterType === type
                      ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 font-bold'
                      : 'text-slate-400 hover:text-slate-200 border border-transparent'
                  }`}
                >
                  {type.replace(/_/g, ' ')}
                </button>
              ))}
            </div>

            <button
              onClick={loadReports}
              disabled={isLoadingReports}
              className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200 transition font-mono"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoadingReports ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>

          {/* Reports Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/80 border-b border-slate-800 text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                  <tr>
                    <th className="p-3.5">Report Number</th>
                    <th className="p-3.5">Type</th>
                    <th className="p-3.5">Title & Scope</th>
                    <th className="p-3.5">Posture / Score</th>
                    <th className="p-3.5">SHA-256 Checksum</th>
                    <th className="p-3.5">Generated At</th>
                    <th className="p-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {reports.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="p-8 text-center text-slate-500 font-mono">
                        {isLoadingReports ? 'Loading reports...' : 'No reports generated yet. Click "Generate Report" to create one.'}
                      </td>
                    </tr>
                  ) : (
                    reports.map((rep) => (
                      <tr key={rep.id} className="hover:bg-slate-800/40 transition">
                        <td className="p-3.5 font-mono text-sky-400 font-bold">
                          {rep.report_number}
                        </td>
                        <td className="p-3.5">
                          <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                            rep.report_type === 'EXECUTIVE' ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30' :
                            rep.report_type === 'TECHNICAL' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' :
                            rep.report_type === 'RISK' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' :
                            rep.report_type === 'ASSET' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' :
                            'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                          }`}>
                            {rep.report_type}
                          </span>
                        </td>
                        <td className="p-3.5">
                          <div className="font-semibold text-slate-200">{rep.title}</div>
                          <div className="text-[11px] text-slate-400">{rep.cse_name || 'Enterprise Portfolio'}</div>
                        </td>
                        <td className="p-3.5">
                          <div className="font-mono font-bold text-slate-200">
                            {rep.summary?.overall_risk_score !== undefined ? `${rep.summary.overall_risk_score}/100` : '—'}
                          </div>
                          <div className="text-[10px] font-mono text-slate-400">
                            {rep.summary?.overall_security_posture || rep.summary?.risk_band || 'VALIDATED'}
                          </div>
                        </td>
                        <td className="p-3.5 font-mono text-[10px] text-slate-400">
                          <span title={rep.sha256_checksum}>
                            {rep.sha256_checksum.substring(0, 12)}...
                          </span>
                        </td>
                        <td className="p-3.5 font-mono text-slate-400 text-[11px]">
                          {new Date(rep.generated_at).toLocaleString()}
                        </td>
                        <td className="p-3.5 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              onClick={() => handleOpenReport(rep.id)}
                              className="flex items-center gap-1 bg-slate-800 hover:bg-slate-700 text-sky-400 px-2.5 py-1 rounded text-xs font-semibold transition"
                            >
                              <Eye className="w-3.5 h-3.5" />
                              View
                            </button>
                            <a
                              href={getReportExportUrl(rep.id, 'html')}
                              target="_blank"
                              rel="noreferrer"
                              className="flex items-center gap-1 bg-slate-800 hover:bg-slate-700 text-emerald-400 px-2.5 py-1 rounded text-xs font-semibold transition"
                            >
                              <Download className="w-3.5 h-3.5" />
                              HTML
                            </a>
                            <a
                              href={getReportExportUrl(rep.id, 'json')}
                              download={`${rep.report_number}.json`}
                              className="flex items-center gap-1 bg-slate-800 hover:bg-slate-700 text-purple-400 px-2.5 py-1 rounded text-xs font-semibold transition"
                            >
                              <Download className="w-3.5 h-3.5" />
                              JSON
                            </a>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: AUDIT TRAIL VIEW */}
      {activeTab === 'AUDIT' && (
        <div className="space-y-4">
          {/* Verification Status Banner */}
          {auditVerifyResult && (
            <div className={`p-4 rounded-xl border flex items-center justify-between ${
              auditVerifyResult.is_valid
                ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
                : 'bg-rose-950/40 border-rose-500/40 text-rose-300'
            }`}>
              <div className="flex items-center gap-3">
                {auditVerifyResult.is_valid ? (
                  <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0" />
                ) : (
                  <AlertTriangle className="w-6 h-6 text-rose-400 shrink-0" />
                )}
                <div>
                  <div className="font-bold text-sm">
                    {auditVerifyResult.is_valid
                      ? 'ALL AUDIT TRAIL RECORDS CRYPTOGRAPHICALLY VERIFIED'
                      : 'AUDIT CHAIN TAMPER DETECTED'}
                  </div>
                  <div className="text-xs opacity-80 mt-0.5 font-mono">
                    {auditVerifyResult.details} (Verified {auditVerifyResult.verified_events} of {auditVerifyResult.total_events} events)
                  </div>
                </div>
              </div>
              <button
                onClick={() => setAuditVerifyResult(null)}
                className="text-xs opacity-60 hover:opacity-100 font-mono"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Audit Filters */}
          <div className="flex flex-wrap items-center gap-3 bg-slate-900/40 p-3 rounded-lg border border-slate-800">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-slate-400 uppercase">User:</span>
              <input
                type="text"
                placeholder="Filter user..."
                value={auditUserFilter}
                onChange={(e) => setAuditUserFilter(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-xs text-slate-200 font-mono"
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-slate-400 uppercase">Action:</span>
              <input
                type="text"
                placeholder="Filter action..."
                value={auditActionFilter}
                onChange={(e) => setAuditActionFilter(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-xs text-slate-200 font-mono"
              />
            </div>
            <button
              onClick={loadAuditLogs}
              className="bg-sky-600 hover:bg-sky-500 text-white px-3 py-1 rounded text-xs font-bold font-mono transition"
            >
              Filter
            </button>
          </div>

          {/* Audit Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/80 border-b border-slate-800 text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                  <tr>
                    <th className="p-3.5">Timestamp</th>
                    <th className="p-3.5">User / Role</th>
                    <th className="p-3.5">Action</th>
                    <th className="p-3.5">Entity</th>
                    <th className="p-3.5">Status</th>
                    <th className="p-3.5">Integrity Hash</th>
                    <th className="p-3.5 text-right">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {auditLogs.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="p-8 text-center text-slate-500">
                        {isLoadingAudit ? 'Loading audit logs...' : 'No audit records found.'}
                      </td>
                    </tr>
                  ) : (
                    auditLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-slate-800/40 transition">
                        <td className="p-3.5 text-slate-400 text-[11px]">
                          {new Date(log.timestamp).toLocaleString()}
                        </td>
                        <td className="p-3.5">
                          <div className="font-bold text-slate-200">{log.user_id}</div>
                          <div className="text-[10px] text-slate-500">{log.actor_role}</div>
                        </td>
                        <td className="p-3.5 text-sky-300 font-bold">
                          {log.action}
                        </td>
                        <td className="p-3.5 text-slate-300">
                          <span className="text-slate-500">{log.entity_type}:</span> {log.entity_id.substring(0, 16)}
                        </td>
                        <td className="p-3.5">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            log.status === 'SUCCESS' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                            'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                          }`}>
                            {log.status}
                          </span>
                        </td>
                        <td className="p-3.5 text-[10px] text-slate-400">
                          {log.integrity_hash ? `${log.integrity_hash.substring(0, 10)}...` : 'LEGACY'}
                        </td>
                        <td className="p-3.5 text-right">
                          <button
                            onClick={() => setSelectedAuditLog(log)}
                            className="text-xs text-sky-400 hover:text-sky-300 font-semibold"
                          >
                            Inspect
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
      )}

      {/* GENERATE REPORT MODAL */}
      {showGenModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-lg text-slate-100 flex items-center gap-2">
                <FileText className="w-5 h-5 text-sky-400" />
                Generate Assessment Report Snapshot
              </h3>
              <button onClick={() => setShowGenModal(false)} className="text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>

            {genError && (
              <div className="p-3 bg-rose-950/50 border border-rose-500/40 rounded-lg text-rose-300 text-xs">
                {genError}
              </div>
            )}

            <form onSubmit={handleGenerateReport} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-mono uppercase mb-1">Report Category</label>
                <select
                  value={genType}
                  onChange={(e) => setGenType(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-slate-200 font-mono focus:outline-none focus:border-sky-500"
                >
                  <option value="EXECUTIVE">Executive Summary Report</option>
                  <option value="TECHNICAL">Technical Findings Report</option>
                  <option value="RISK">Supervisory Risk Decomposition Report</option>
                  <option value="ASSET">Asset-Level Vulnerability Assessment</option>
                  <option value="VULNERABILITY_THREAT_INTEL">Threat Intelligence & KEV Report</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-mono uppercase mb-1">Target Entity Scope</label>
                <select
                  value={genCseId}
                  onChange={(e) => setGenCseId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-slate-200 font-mono focus:outline-none focus:border-sky-500"
                >
                  <option value="">All Monitored Critical Entities (Portfolio)</option>
                  {cses.map((c) => (
                    <option key={c.cse_id} value={c.cse_id}>
                      {c.name} ({c.sector})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-mono uppercase mb-1">Custom Title (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. Q3 Official Cyber Security Assessment"
                  value={genTitle}
                  onChange={(e) => setGenTitle(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-mono uppercase mb-1">Description / Notes</label>
                <textarea
                  rows={2}
                  placeholder="Assessment scope rationale or examiner notes..."
                  value={genDesc}
                  onChange={(e) => setGenDesc(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowGenModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  onClick={handleGenerateReport}
                  disabled={isGenerating}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg font-bold transition flex items-center gap-1.5"
                >
                  {isGenerating ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Generating & Signing...
                    </>
                  ) : (
                    'Generate & Sign Snapshot'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* REPORT DETAIL DRAWER / MODAL */}
      {selectedReport && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-4xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/80">
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 bg-sky-500/20 text-sky-300 border border-sky-500/40 rounded text-[10px] font-mono font-bold">
                    {selectedReport.report_type}
                  </span>
                  <span className="font-mono text-xs text-slate-400">
                    No: <strong className="text-slate-200">{selectedReport.report_number}</strong>
                  </span>
                </div>
                <h2 className="text-lg font-bold text-slate-100 mt-1">{selectedReport.title}</h2>
              </div>

              <div className="flex items-center gap-2">
                <a
                  href={getReportExportUrl(selectedReport.id, 'html')}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1 bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1.5 rounded-lg text-xs font-bold transition"
                >
                  <Download className="w-4 h-4" />
                  HTML Export
                </a>
                <button
                  onClick={() => setSelectedReport(null)}
                  className="p-1.5 text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-800 transition"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Cryptographic Integrity Bar */}
            <div className="px-5 py-2.5 bg-slate-950 border-b border-slate-800 flex items-center justify-between text-xs font-mono">
              <div className="flex items-center gap-2 text-emerald-400">
                <Lock className="w-3.5 h-3.5" />
                <span>SHA-256 Checksum: {selectedReport.sha256_checksum}</span>
              </div>
              <div className="flex items-center gap-1.5">
                {selectedReport.tamper_verified ? (
                  <span className="text-emerald-400 font-bold flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Verified
                  </span>
                ) : (
                  <span className="text-rose-400 font-bold flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5" /> Tampered
                  </span>
                )}
              </div>
            </div>

            {/* Detail Tabs */}
            <div className="flex border-b border-slate-800 bg-slate-950/40 px-5 text-xs font-mono">
              <button
                onClick={() => setDetailTab('OVERVIEW')}
                className={`py-3 px-4 border-b-2 font-bold transition ${
                  detailTab === 'OVERVIEW'
                    ? 'border-sky-500 text-sky-400'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                Executive Overview
              </button>
              <button
                onClick={() => setDetailTab('FINDINGS')}
                className={`py-3 px-4 border-b-2 font-bold transition ${
                  detailTab === 'FINDINGS'
                    ? 'border-sky-500 text-sky-400'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                Findings ({selectedReport.content?.detailed_findings?.length || selectedReport.content?.top_security_gaps?.length || 0})
              </button>
              <button
                onClick={() => setDetailTab('EVIDENCE')}
                className={`py-3 px-4 border-b-2 font-bold transition ${
                  detailTab === 'EVIDENCE'
                    ? 'border-sky-500 text-sky-400'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                Evidence References ({selectedReport.evidence_references?.length || 0})
              </button>
            </div>

            {/* Content Body */}
            <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs">
              {detailTab === 'OVERVIEW' && (
                <div className="space-y-6">
                  {/* Summary Grid */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                      <div className="text-[10px] font-mono text-slate-400 uppercase">Posture</div>
                      <div className="text-xl font-bold text-emerald-400 mt-1">
                        {selectedReport.summary?.overall_security_posture || 'VALIDATED'}
                      </div>
                    </div>
                    <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                      <div className="text-[10px] font-mono text-slate-400 uppercase">Risk Score</div>
                      <div className="text-xl font-bold text-rose-400 mt-1">
                        {selectedReport.summary?.overall_risk_score !== undefined ? `${selectedReport.summary.overall_risk_score}/100` : '—'}
                      </div>
                    </div>
                    <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                      <div className="text-[10px] font-mono text-slate-400 uppercase">Findings Count</div>
                      <div className="text-xl font-bold text-slate-100 mt-1">
                        {selectedReport.summary?.total_findings ?? selectedReport.summary?.total_assets ?? 0}
                      </div>
                    </div>
                    <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                      <div className="text-[10px] font-mono text-slate-400 uppercase">Active KEVs</div>
                      <div className="text-xl font-bold text-amber-400 mt-1">
                        {selectedReport.summary?.kev_exposures_count ?? selectedReport.summary?.kev_exposed_assets ?? 0}
                      </div>
                    </div>
                  </div>

                  {/* Executive Narrative */}
                  {selectedReport.content?.executive_summary?.narrative && (
                    <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800 space-y-2">
                      <div className="font-mono text-[11px] uppercase text-sky-400 font-bold">Executive Assessment Narrative</div>
                      <p className="text-slate-300 leading-relaxed text-sm">
                        {selectedReport.content.executive_summary.narrative}
                      </p>
                    </div>
                  )}

                  {/* Top Security Gaps */}
                  {selectedReport.content?.top_security_gaps && (
                    <div className="space-y-3">
                      <div className="font-mono text-[11px] uppercase text-sky-400 font-bold">Priority Supervisory Gaps</div>
                      <div className="space-y-2">
                        {selectedReport.content.top_security_gaps.map((gap: any, i: number) => (
                          <div key={i} className="bg-slate-950 p-3.5 rounded-lg border border-slate-800 space-y-1.5">
                            <div className="flex items-center justify-between">
                              <span className="font-mono font-bold text-sky-400">{gap.rule_id}</span>
                              <span className="px-2 py-0.5 bg-rose-500/20 text-rose-300 border border-rose-500/30 rounded text-[10px] font-bold font-mono">
                                Priority {gap.supervisory_priority}
                              </span>
                            </div>
                            <div className="text-slate-300">{gap.reason}</div>
                            <div className="text-slate-400 text-[11px]">
                              <strong className="text-slate-300">Recommendation:</strong> {gap.recommendation}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {detailTab === 'FINDINGS' && (
                <div className="space-y-3">
                  {(selectedReport.content?.detailed_findings || []).map((f: any, i: number) => (
                    <div key={i} className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-sky-400">{f.rule_id}</span>
                          <span className="px-2 py-0.5 bg-slate-800 text-slate-300 rounded font-mono text-[10px]">
                            {f.severity}
                          </span>
                        </div>
                        <div className="text-slate-400 font-mono text-[11px]">
                          Priority: <strong className="text-slate-200">{f.supervisory_priority}</strong>
                        </div>
                      </div>
                      <div className="text-slate-200">{f.reason}</div>
                      <div className="grid grid-cols-2 gap-2 text-[11px] bg-slate-900 p-2 rounded">
                        <div>
                          <span className="text-slate-500">Expected:</span> {f.expected_behaviour}
                        </div>
                        <div>
                          <span className="text-slate-500">Observed:</span> {f.observed_behaviour}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {detailTab === 'EVIDENCE' && (
                <div className="space-y-3">
                  {(selectedReport.evidence_references || []).map((ev: any, i: number) => (
                    <div key={i} className="bg-slate-950 p-3.5 rounded-lg border border-slate-800 space-y-1">
                      <div className="flex items-center justify-between font-mono text-[11px]">
                        <span className="text-sky-400 font-bold">{ev.evidence_type}</span>
                        <span className="text-slate-400">{ev.source_table} [{ev.source_record_id}]</span>
                      </div>
                      <div className="text-slate-300">{ev.description}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* AUDIT LOG DETAIL MODAL */}
      {selectedAuditLog && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-lg text-slate-100 font-mono flex items-center gap-2">
                <Lock className="w-5 h-5 text-emerald-400" />
                Audit Trail Event Inspection
              </h3>
              <button onClick={() => setSelectedAuditLog(null)} className="text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs font-mono">
              <div>
                <span className="text-slate-500">Event ID:</span>
                <div className="text-slate-200">{selectedAuditLog.id}</div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="text-slate-500">User:</span>
                  <div className="text-slate-200">{selectedAuditLog.user_id}</div>
                </div>
                <div>
                  <span className="text-slate-500">Role:</span>
                  <div className="text-slate-200">{selectedAuditLog.actor_role}</div>
                </div>
              </div>
              <div>
                <span className="text-slate-500">Action:</span>
                <div className="text-sky-400 font-bold">{selectedAuditLog.action}</div>
              </div>
              <div>
                <span className="text-slate-500">Resource:</span>
                <div className="text-slate-200">{selectedAuditLog.entity_type} ({selectedAuditLog.entity_id})</div>
              </div>
              <div>
                <span className="text-slate-500">Integrity Hash:</span>
                <div className="text-emerald-400 break-all text-[11px]">{selectedAuditLog.integrity_hash || 'N/A'}</div>
              </div>
              <div>
                <span className="text-slate-500">Previous Hash:</span>
                <div className="text-slate-400 break-all text-[11px]">{selectedAuditLog.previous_hash || 'N/A'}</div>
              </div>
              {selectedAuditLog.before_after && (
                <div>
                  <span className="text-slate-500">State Transition Diff:</span>
                  <pre className="bg-slate-950 p-2 rounded text-[10px] text-slate-300 overflow-x-auto">
                    {JSON.stringify(selectedAuditLog.before_after, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="flex justify-end pt-2 border-t border-slate-800">
              <button
                onClick={() => setSelectedAuditLog(null)}
                className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
