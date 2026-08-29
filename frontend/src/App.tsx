import React, { useState, useEffect } from 'react';
import { Header } from './components/common/Header';
import { SupervisoryDashboard } from './components/dashboard/SupervisoryDashboard';
import { ReviewQueueTable } from './components/queue/ReviewQueueTable';
import { EvidenceGraphViewer } from './components/graph/EvidenceGraphViewer';
import { FindingDetailModal } from './components/findings/FindingDetailModal';
import { CSEDetailModal } from './components/cse/CSEDetailModal';
import {
  fetchDashboardMetrics,
  fetchCSEProfiles,
  fetchReviewQueue,
  fetchGraphSummary,
  fetchGraphAnomalies
} from './api/client';
import {
  DashboardMetrics,
  CSEProfile,
  QueueItem,
  GraphData,
  GraphAnomaly
} from './types/api';
import { LayoutDashboard, Layers, Network, AlertCircle } from 'lucide-react';

export const App: React.FC = () => {
  const [viewMode, setViewMode] = useState<'DASHBOARD' | 'QUEUE' | 'GRAPH'>('DASHBOARD');
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [cses, setCses] = useState<CSEProfile[]>([]);
  const [queueItems, setQueueItems] = useState<QueueItem[]>([]);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [anomalies, setAnomalies] = useState<GraphAnomaly[]>([]);
  const [selectedQueueItem, setSelectedQueueItem] = useState<QueueItem | null>(null);
  const [selectedCSE, setSelectedCSE] = useState<CSEProfile | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setIsRefreshing(true);
    setError(null);
    try {
      const [metRes, cseRes, queueRes, grpRes, anomRes] = await Promise.all([
        fetchDashboardMetrics(),
        fetchCSEProfiles(),
        fetchReviewQueue('latest'),
        fetchGraphSummary('latest'),
        fetchGraphAnomalies('latest')
      ]);

      setMetrics(metRes);
      setCses(cseRes);
      setQueueItems(queueRes.queue || []);
      setGraphData(grpRes);
      setAnomalies(anomRes);
    } catch (err: any) {
      setError(err.message || 'Failed to connect to SAT-SA backend API.');
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="min-h-screen bg-[#070a12] text-slate-100 flex flex-col font-sans">
      <Header onRefresh={loadData} isRefreshing={isRefreshing} />

      {/* Main Navigation Subheader */}
      <div className="border-b border-slate-800 bg-slate-900/60 px-6 flex items-center justify-between">
        <div className="flex items-center gap-6 text-xs font-mono">
          <button
            onClick={() => setViewMode('DASHBOARD')}
            className={`py-3 font-bold flex items-center gap-1.5 border-b-2 transition ${
              viewMode === 'DASHBOARD'
                ? 'border-cyan-400 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <LayoutDashboard className="w-4 h-4" />
            <span>SUPERVISORY DASHBOARD</span>
          </button>

          <button
            onClick={() => setViewMode('QUEUE')}
            className={`py-3 font-bold flex items-center gap-1.5 border-b-2 transition ${
              viewMode === 'QUEUE'
                ? 'border-cyan-400 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>REVIEW PRIORITY QUEUE ({queueItems.length})</span>
          </button>

          <button
            onClick={() => setViewMode('GRAPH')}
            className={`py-3 font-bold flex items-center gap-1.5 border-b-2 transition ${
              viewMode === 'GRAPH'
                ? 'border-cyan-400 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Network className="w-4 h-4" />
            <span>SUPERVISORY EVIDENCE GRAPH</span>
          </button>
        </div>

        <div className="text-[11px] font-mono text-slate-400">
          Air-Gap Protocol: <span className="text-emerald-400 font-bold">STRICT_LOCAL_ONLY</span>
        </div>
      </div>

      {/* Main App Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
        {error && (
          <div className="bg-rose-950/80 border border-rose-800 text-rose-200 p-4 rounded text-xs font-mono flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{error}</span>
            </div>
            <button onClick={loadData} className="px-3 py-1 bg-rose-900 hover:bg-rose-800 rounded text-white font-bold">
              Retry Connection
            </button>
          </div>
        )}

        {viewMode === 'DASHBOARD' && (
          <SupervisoryDashboard
            metrics={metrics}
            cses={cses}
            onSelectCSE={cse => setSelectedCSE(cse)}
            onNavigateToQueue={() => setViewMode('QUEUE')}
          />
        )}

        {viewMode === 'QUEUE' && (
          <ReviewQueueTable
            items={queueItems}
            onSelectItem={item => setSelectedQueueItem(item)}
          />
        )}

        {viewMode === 'GRAPH' && (
          <EvidenceGraphViewer
            graphData={graphData}
            anomalies={anomalies}
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
      <footer className="border-t border-slate-800 bg-slate-950 px-6 py-4 text-xs font-mono text-slate-500 flex justify-between items-center">
        <div>SAT-SA Smart Assessment Tool — Offline Supervisory Intelligence Platform</div>
        <div>NCIIPC Supervisory Framework Compliant</div>
      </footer>
    </div>
  );
};

export default App;
