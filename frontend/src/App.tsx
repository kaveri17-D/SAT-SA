import React, { useState, useEffect } from "react";
import { Header } from "./components/common/Header";
import { SupervisoryDashboard } from "./components/dashboard/SupervisoryDashboard";
import { ReviewQueueTable } from "./components/queue/ReviewQueueTable";
import { EvidenceGraphViewer } from "./components/graph/EvidenceGraphViewer";
import { RiskAnalytics } from "./components/risk/RiskAnalytics";
import { ReportsDashboard } from "./components/reporting/ReportsDashboard";
import { FindingDetailModal } from "./components/findings/FindingDetailModal";
import { CSEDetailModal } from "./components/cse/CSEDetailModal";
import {
  fetchDashboardMetrics,
  fetchCSEProfiles,
  fetchReviewQueue,
  fetchGraphSummary,
  fetchGraphAnomalies,
} from "./api/client";
import {
  DashboardMetrics,
  CSEProfile,
  QueueItem,
  GraphData,
  GraphAnomaly,
} from "./types/api";
import {
  LayoutDashboard,
  Layers,
  Network,
  AlertCircle,
  FileText,
  BarChart3,
  RefreshCw,
} from "lucide-react";

export const App: React.FC = () => {
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    const saved = localStorage.getItem("satsa_theme");
    return saved === "light" ? "light" : "dark";
  });

  const [viewMode, setViewMode] = useState<
    "DASHBOARD" | "QUEUE" | "GRAPH" | "RISK" | "REPORTS"
  >("DASHBOARD");
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [cses, setCses] = useState<CSEProfile[]>([]);
  const [queueItems, setQueueItems] = useState<QueueItem[]>([]);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [anomalies, setAnomalies] = useState<GraphAnomaly[]>([]);
  const [selectedQueueItem, setSelectedQueueItem] = useState<QueueItem | null>(
    null,
  );
  const [selectedCSE, setSelectedCSE] = useState<CSEProfile | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [activeRunId, setActiveRunId] = useState<string>("");
  const [apiError, setApiError] = useState<{
    endpoint: string;
    message: string;
  } | null>(null);

  const toggleTheme = () => {
    setTheme((prev) => {
      const next = prev === "dark" ? "light" : "dark";
      localStorage.setItem("satsa_theme", next);
      return next;
    });
  };

  useEffect(() => {
    if (theme === "light") {
      document.body.classList.add("theme-light");
      document.body.classList.remove("theme-dark");
    } else {
      document.body.classList.add("theme-dark");
      document.body.classList.remove("theme-light");
    }
  }, [theme]);

  const loadData = async () => {
    setIsRefreshing(true);
    setApiError(null);
    try {
      // Step 1: Fetch latest completed analysis run metrics
      const metRes = await fetchDashboardMetrics();
      setMetrics(metRes);
      const resolvedRunId = metRes.analysis_run_id || "";
      setActiveRunId(resolvedRunId);

      // Step 2: Fetch run-dependent resources using THAT EXACT ID
      const [cseRes, queueRes] = await Promise.all([
        fetchCSEProfiles(resolvedRunId),
        fetchReviewQueue(resolvedRunId || "latest"),
      ]);

      setCses(cseRes);
      setQueueItems(queueRes.queue || []);

      // Step 3: Fetch evidence graph with the EXACT same run ID
      try {
        const [grpRes, anomRes] = await Promise.all([
          fetchGraphSummary(resolvedRunId || "latest"),
          fetchGraphAnomalies(resolvedRunId || "latest"),
        ]);
        setGraphData(grpRes);
        setAnomalies(anomRes);
      } catch (grpErr) {
        console.warn("Evidence graph load warning:", grpErr);
      }
    } catch (err: any) {
      console.error("Failed to load core supervisory data:", err);
      setApiError({
        endpoint: "Core Supervisory APIs (/metrics, /cses, /queue)",
        message: err.message || "Unable to load supervisory data.",
      });
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div
      className={`min-h-screen flex flex-col font-sans transition-colors duration-200 ${
        theme === "light"
          ? "theme-light bg-slate-50 text-slate-900"
          : "bg-[#070a12] text-slate-100"
      }`}
    >
      <Header
        onRefresh={loadData}
        isRefreshing={isRefreshing}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      {/* Main Navigation Subheader & Compact Navigation */}
      <div className="border-b border-slate-800 bg-slate-900/60 px-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 md:gap-6 text-xs font-mono overflow-x-auto">
          <button
            onClick={() => setViewMode("DASHBOARD")}
            className={`py-3 font-bold flex items-center gap-1.5 border-b-2 transition shrink-0 ${
              viewMode === "DASHBOARD"
                ? "border-cyan-400 text-cyan-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <LayoutDashboard className="w-4 h-4" />
            <span>SUPERVISORY DASHBOARD</span>
          </button>

          <button
            onClick={() => setViewMode("QUEUE")}
            className={`py-3 font-bold flex items-center gap-1.5 border-b-2 transition shrink-0 ${
              viewMode === "QUEUE"
                ? "border-cyan-400 text-cyan-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>REVIEW PRIORITY QUEUE ({queueItems.length})</span>
          </button>

          <button
            onClick={() => setViewMode("GRAPH")}
            className={`py-3 font-bold flex items-center gap-1.5 border-b-2 transition shrink-0 ${
              viewMode === "GRAPH"
                ? "border-cyan-400 text-cyan-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Network className="w-4 h-4" />
            <span>SUPERVISORY EVIDENCE GRAPH</span>
          </button>

          <button
            onClick={() => setViewMode("RISK")}
            className={`py-3 font-bold flex items-center gap-1.5 border-b-2 transition shrink-0 ${
              viewMode === "RISK"
                ? "border-cyan-400 text-cyan-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            <span>RISK ANALYTICS</span>
          </button>

          <button
            onClick={() => setViewMode("REPORTS")}
            className={`py-3 font-bold flex items-center gap-1.5 border-b-2 transition shrink-0 ${
              viewMode === "REPORTS"
                ? "border-cyan-400 text-cyan-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <FileText className="w-4 h-4" />
            <span>REPORTS & AUDIT TRAIL</span>
          </button>
        </div>

        <div className="flex items-center gap-3 text-[11px] font-mono text-slate-400 py-2">
          <span>
            Air-Gap Protocol:{" "}
            <strong className="text-emerald-400 font-bold">
              STRICT_LOCAL_ONLY
            </strong>
          </span>
        </div>
      </div>

      {/* Main App Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
        {/* Explicit API Error Banner */}
        {apiError && (
          <div className="bg-rose-950/90 border border-rose-800 text-rose-200 p-5 rounded-xl text-xs font-mono shadow-lg flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <div className="font-bold text-sm text-white uppercase tracking-wider">
                  Unable to load supervisory data
                </div>
                <div className="text-rose-300 mt-1">
                  Failed Endpoint:{" "}
                  <span className="text-white font-semibold">
                    {apiError.endpoint}
                  </span>
                </div>
                <div className="text-rose-400 text-[11px] mt-0.5">
                  {apiError.message}
                </div>
              </div>
            </div>
            <button
              onClick={loadData}
              disabled={isRefreshing}
              className="px-4 py-2 bg-rose-900 hover:bg-rose-800 text-white font-bold rounded-lg transition inline-flex items-center gap-2 shrink-0 disabled:opacity-50"
            >
              <RefreshCw
                className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin" : ""}`}
              />
              <span>Retry Connection</span>
            </button>
          </div>
        )}

        {/* Views */}
        {viewMode === "DASHBOARD" &&
          (metrics === null && apiError ? (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-12 text-center space-y-3 font-mono">
              <AlertCircle className="w-8 h-8 text-rose-400 mx-auto" />
              <div className="text-sm font-bold text-white">
                Dashboard Offline / Connection Error
              </div>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Could not retrieve active assessment run metrics from the
                backend. Please ensure the SAT-SA server is running.
              </p>
              <button
                onClick={loadData}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded text-xs font-bold transition"
              >
                Retry Loading
              </button>
            </div>
          ) : (
            <SupervisoryDashboard
              metrics={metrics}
              cses={cses}
              onSelectCSE={(cse) => setSelectedCSE(cse)}
              onNavigateToQueue={() => setViewMode("QUEUE")}
            />
          ))}

        {viewMode === "QUEUE" && (
          <ReviewQueueTable
            items={queueItems}
            onSelectItem={(item) => setSelectedQueueItem(item)}
          />
        )}

        {viewMode === "GRAPH" && (
          <EvidenceGraphViewer
            graphData={graphData}
            anomalies={anomalies}
            analysisRunId={activeRunId || metrics?.analysis_run_id}
          />
        )}

        {viewMode === "RISK" && (
          <RiskAnalytics
            cses={cses}
            analysisRunId={activeRunId || metrics?.analysis_run_id}
            onSelectCSE={(cse) => setSelectedCSE(cse)}
          />
        )}

        {viewMode === "REPORTS" && (
          <ReportsDashboard
            cses={cses}
            analysisRunId={activeRunId || metrics?.analysis_run_id}
          />
        )}
      </main>

      {/* Modals */}
      <FindingDetailModal
        queueItem={selectedQueueItem}
        isOpen={!!selectedQueueItem}
        onClose={() => setSelectedQueueItem(null)}
        onRefreshQueue={loadData}
      />

      <CSEDetailModal
        cse={selectedCSE}
        isOpen={!!selectedCSE}
        onClose={() => setSelectedCSE(null)}
      />

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-slate-950 px-6 py-4 text-xs font-mono text-slate-500 flex flex-wrap justify-between items-center gap-2">
        <div>
          SAT-SA Smart Assessment Tool — Offline Supervisory Intelligence
          Platform
        </div>
        <div>
          NCIIPC Supervisory Framework Compliant | Strict Air-Gap Validated
        </div>
      </footer>
    </div>
  );
};

export default App;
