import React, { useState, useEffect, useMemo } from "react";
import {
  GraphData,
  GraphNode,
  GraphEdge,
  GraphAnomaly,
  SimpleWorkflowData,
  SimpleWorkflowStage,
} from "../../types/api";
import { fetchSimpleWorkflow, fetchFullGraph } from "../../api/client";
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  AlertTriangle,
  Layers,
  Info,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Network,
  GitCommit,
  ArrowRight,
  ShieldAlert,
} from "lucide-react";

interface GraphViewerProps {
  graphData?: GraphData | null;
  anomalies?: GraphAnomaly[];
  analysisRunId?: string;
  selectedCseId?: string;
  selectedFindingId?: string;
  onSelectNode?: (node: any) => void;
}

type DisplayView = "SIMPLE" | "FULL";

export const EvidenceGraphViewer: React.FC<GraphViewerProps> = ({
  graphData: initialGraphData,
  anomalies = [],
  analysisRunId = "latest",
  selectedCseId,
  selectedFindingId,
  onSelectNode,
}) => {
  const [displayView, setDisplayView] = useState<DisplayView>("SIMPLE");
  const [zoom, setZoom] = useState(1);
  const [simpleWorkflow, setSimpleWorkflow] = useState<SimpleWorkflowData | null>(null);
  const [isLoadingSimple, setIsLoadingSimple] = useState(true);
  const [simpleError, setSimpleError] = useState<string | null>(null);

  // Selected stage for inspection in Simple View
  const [selectedStage, setSelectedStage] = useState<SimpleWorkflowStage | null>(null);

  // Full Graph state (loaded on-demand when user opts in)
  const [fullGraphData, setFullGraphData] = useState<GraphData | null>(initialGraphData || null);
  const [isLoadingFull, setIsLoadingFull] = useState(false);
  const [fullGraphLoaded, setFullGraphLoaded] = useState(!!initialGraphData);
  const [selectedFullNode, setSelectedFullNode] = useState<GraphNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<GraphEdge | null>(null);
  const [filterType, setFilterType] = useState<string>("ALL");

  // Load Simple Workflow (Scoped 7-stage path)
  useEffect(() => {
    let isMounted = true;
    setIsLoadingSimple(true);
    setSimpleError(null);

    fetchSimpleWorkflow(analysisRunId, {
      cseId: selectedCseId,
      findingId: selectedFindingId,
    })
      .then((data) => {
        if (isMounted) {
          setSimpleWorkflow(data);
          setIsLoadingSimple(false);
          if (data.stages && data.stages.length > 0) {
            const anomalous = data.stages.find((s) => s.status === "ANOMALOUS" || s.status === "MISSING");
            const alertStage = data.stages.find((s) => s.stage === "ALERT");
            setSelectedStage(anomalous || alertStage || data.stages[0]);
          }
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error("Failed to load simple workflow:", err);
          setSimpleError(err.message || "Failed to load workflow path");
          setIsLoadingSimple(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [analysisRunId, selectedCseId, selectedFindingId]);

  // Load Full Graph on conscious examiner opt-in
  const handleOptInFullGraph = () => {
    setDisplayView("FULL");
    if (!fullGraphLoaded && !isLoadingFull) {
      setIsLoadingFull(true);
      fetchFullGraph(analysisRunId, 250)
        .then((data) => {
          setFullGraphData(data);
          setFullGraphLoaded(true);
          setIsLoadingFull(false);
        })
        .catch((err) => {
          console.error("Failed to load full evidence graph:", err);
          setIsLoadingFull(false);
        });
    }
  };

  const nodeColorMap: Record<
    string,
    { bg: string; stroke: string; text: string; fill: string }
  > = {
    CSE: { bg: "#0f172a", stroke: "#38bdf8", text: "#38bdf8", fill: "#0369a1" },
    ASSET: { bg: "#0f172a", stroke: "#818cf8", text: "#818cf8", fill: "#4338ca" },
    ALERT: { bg: "#0f172a", stroke: "#f87171", text: "#f87171", fill: "#b91c1c" },
    INVESTIGATION: { bg: "#0f172a", stroke: "#fbbf24", text: "#fbbf24", fill: "#b45309" },
    ANALYST: { bg: "#0f172a", stroke: "#34d399", text: "#34d399", fill: "#047857" },
    ESCALATION: { bg: "#0f172a", stroke: "#c084fc", text: "#c084fc", fill: "#6b21a8" },
    CASE: { bg: "#0f172a", stroke: "#38bdf8", text: "#38bdf8", fill: "#1e40af" },
    CLOSURE: { bg: "#0f172a", stroke: "#94a3b8", text: "#94a3b8", fill: "#334155" },
    MISSING_EXPECTED: { bg: "#450a0a", stroke: "#ef4444", text: "#fca5a5", fill: "#991b1b" },
  };

  // Full Graph Nodes & Layout (Capped to 40 nodes to maintain maximum performance)
  const filteredNodes = useMemo(() => {
    if (!fullGraphData) return [];
    if (filterType === "ALL") return fullGraphData.nodes.slice(0, 40);
    return fullGraphData.nodes.filter((n) => n.entity_type === filterType).slice(0, 40);
  }, [fullGraphData, filterType]);

  const filteredEdges = useMemo(() => {
    if (!fullGraphData) return [];
    const nodeIds = new Set(filteredNodes.map((n) => n.id));
    return fullGraphData.edges.filter(
      (e) => nodeIds.has(e.source) && nodeIds.has(e.target)
    );
  }, [fullGraphData, filteredNodes]);

  const nodePositions = useMemo(() => {
    const posMap: Record<string, { x: number; y: number }> = {};
    const typeGroups: Record<string, GraphNode[]> = {};

    filteredNodes.forEach((n) => {
      if (!typeGroups[n.entity_type]) typeGroups[n.entity_type] = [];
      typeGroups[n.entity_type].push(n);
    });

    const columns: Record<string, number> = {
      CSE: 80,
      ASSET: 220,
      ALERT: 380,
      INVESTIGATION: 540,
      ANALYST: 700,
      ESCALATION: 860,
      CASE: 1020,
      CLOSURE: 1180,
      MISSING_EXPECTED: 380,
    };

    Object.entries(typeGroups).forEach(([type, nodes]) => {
      const colX = columns[type] || 500;
      const startY = 80;
      const spacingY = Math.min(60, 500 / Math.max(1, nodes.length));

      nodes.forEach((n, idx) => {
        posMap[n.id] = {
          x: colX,
          y: startY + idx * spacingY,
        };
      });
    });

    return posMap;
  }, [filteredNodes]);

  const globalNodeCount = displayView === "SIMPLE"
    ? (simpleWorkflow ? simpleWorkflow.metrics.node_count : "—")
    : (fullGraphData ? fullGraphData.metrics.node_count : "—");

  const globalEdgeCount = displayView === "SIMPLE"
    ? (simpleWorkflow ? simpleWorkflow.metrics.edge_count : "—")
    : (fullGraphData ? fullGraphData.metrics.edge_count : "—");

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-5 font-mono shadow-xl">
      {/* Top Header & Summary Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Layers className="w-5 h-5 text-sky-400" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Supervisory Evidence Graph (NetworkX Provenance)
            </h3>
          </div>
          <div className="text-xs text-slate-400 mt-1 flex flex-wrap items-center gap-4">
            <span>
              View Mode:{" "}
              <strong className={displayView === "SIMPLE" ? "text-sky-400" : "text-purple-400"}>
                {displayView === "SIMPLE" ? "Canonical Linear Workflow (Scoped)" : "Full NetworkX Topology"}
              </strong>
            </span>
            <span>
              Nodes in View: <strong className="text-white">{globalNodeCount}</strong>
            </span>
            <span>
              Edges in View: <strong className="text-white">{globalEdgeCount}</strong>
            </span>
            {simpleWorkflow && (
              <>
                <span>
                  Completed Stages:{" "}
                  <strong className="text-emerald-400">{simpleWorkflow.metrics.completed_stages}</strong>
                </span>
                <span>
                  Anomalies / Missing:{" "}
                  <strong className="text-rose-400">
                    {simpleWorkflow.metrics.anomalous_stages + simpleWorkflow.metrics.missing_stages}
                  </strong>
                </span>
                {anomalies.length > 0 && (
                  <span>
                    Detected Anomalies: <strong className="text-amber-400">{anomalies.length}</strong>
                  </span>
                )}
              </>
            )}
          </div>
        </div>

        {/* View Toggle: Simple View vs Full Evidence Graph */}
        <div className="flex items-center gap-2 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
          <button
            onClick={() => setDisplayView("SIMPLE")}
            className={`px-3 py-1.5 rounded-md font-bold transition flex items-center gap-1.5 ${
              displayView === "SIMPLE"
                ? "bg-sky-950 text-sky-300 border border-sky-700 shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <GitCommit className="w-3.5 h-3.5" />
            <span>Simple View (Default)</span>
          </button>
          <button
            onClick={handleOptInFullGraph}
            className={`px-3 py-1.5 rounded-md font-bold transition flex items-center gap-1.5 ${
              displayView === "FULL"
                ? "bg-purple-950 text-purple-300 border border-purple-700 shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Network className="w-3.5 h-3.5" />
            <span>Show Full Evidence Graph</span>
          </button>
        </div>
      </div>

      {/* VIEW 1: SIMPLE VIEW (DEFAULT SCOPED 7-STAGE PATH) */}
      {displayView === "SIMPLE" && (
        <div className="space-y-5">
          {/* Workflow Scope Banner */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-slate-400 font-semibold uppercase text-[11px]">Inspecting Incident Workflow:</span>
              <span className="text-sky-300 font-bold">
                {simpleWorkflow?.target_scope.cse_name || "Enterprise Portfolio Scope"}
              </span>
              {simpleWorkflow?.target_scope.finding_rule_id && (
                <span className="text-xs bg-slate-800 text-slate-300 px-2 py-0.5 rounded">
                  Rule: {simpleWorkflow.target_scope.finding_rule_id} ({simpleWorkflow.target_scope.finding_severity})
                </span>
              )}
            </div>

            <div className="flex items-center gap-3 text-[11px] text-slate-400">
              <span className="flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Completed
              </span>
              <span className="flex items-center gap-1">
                <AlertTriangle className="w-3 h-3 text-amber-400" /> Anomalous
              </span>
              <span className="flex items-center gap-1">
                <XCircle className="w-3 h-3 text-rose-400" /> Missing
              </span>
              <span className="flex items-center gap-1">
                <HelpCircle className="w-3 h-3 text-slate-500" /> Not Applicable
              </span>
            </div>
          </div>

          {isLoadingSimple && (
            <div className="p-8 text-center text-slate-400 text-xs">
              Resolving canonical supervisory workflow path...
            </div>
          )}

          {simpleError && (
            <div className="p-4 bg-rose-950/40 border border-rose-800 rounded-lg text-rose-300 text-xs flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{simpleError}</span>
            </div>
          )}

          {/* Sequential Lifecycle Visualizer (Strictly 7 Stages) */}
          {simpleWorkflow && !isLoadingSimple && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-7 gap-2.5 pt-2">
                {simpleWorkflow.stages.map((stage, idx) => {
                  const isSelected = selectedStage?.stage === stage.stage;
                  let statusBg = "bg-slate-950/80 border-slate-800";
                  let statusText = "text-slate-400";
                  let StatusIcon = HelpCircle;

                  if (stage.status === "COMPLETED") {
                    statusBg = "bg-emerald-950/30 border-emerald-700/60";
                    statusText = "text-emerald-400";
                    StatusIcon = CheckCircle2;
                  } else if (stage.status === "ANOMALOUS") {
                    statusBg = "bg-amber-950/30 border-amber-600/60";
                    statusText = "text-amber-400";
                    StatusIcon = AlertTriangle;
                  } else if (stage.status === "MISSING") {
                    statusBg = "bg-rose-950/40 border-rose-600/80";
                    statusText = "text-rose-400";
                    StatusIcon = XCircle;
                  }

                  return (
                    <div
                      key={stage.stage}
                      onClick={() => {
                        setSelectedStage(stage);
                        if (onSelectNode) onSelectNode(stage);
                      }}
                      className={`p-3 rounded-lg border flex flex-col justify-between transition cursor-pointer relative ${statusBg} ${
                        isSelected ? "ring-2 ring-sky-400 scale-[1.02] shadow-lg" : "hover:border-sky-500/60"
                      }`}
                    >
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] text-slate-500 font-bold uppercase">
                            Step {idx + 1}
                          </span>
                          <StatusIcon className={`w-3.5 h-3.5 ${statusText}`} />
                        </div>
                        <div className="text-xs font-bold text-white uppercase">
                          {stage.stage}
                        </div>
                        <div className="text-[11px] text-slate-300 font-semibold truncate" title={stage.label}>
                          {stage.label}
                        </div>
                      </div>

                      <div className="mt-3 pt-2 border-t border-slate-800/80">
                        <span
                          className={`text-[9px] uppercase font-bold px-1.5 py-0.5 rounded inline-block ${
                            stage.status === "COMPLETED"
                              ? "bg-emerald-500/20 text-emerald-400"
                              : stage.status === "ANOMALOUS"
                              ? "bg-amber-500/20 text-amber-400"
                              : stage.status === "MISSING"
                              ? "bg-rose-500/20 text-rose-400 font-black"
                              : "bg-slate-800 text-slate-400"
                          }`}
                        >
                          {stage.status}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Sequential Path Arrows Indicator */}
              <div className="hidden md:flex items-center justify-between px-6 text-slate-600 text-xs">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-1 text-slate-600">
                    <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
                    <span className="text-[9px] uppercase font-mono text-slate-500">
                      {simpleWorkflow.stages[i].stage} → {simpleWorkflow.stages[i + 1].stage}
                    </span>
                  </div>
                ))}
              </div>

              {/* Node Inspector Panel (Displays REAL Canonical Database Fields) */}
              {selectedStage && (
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <div className="flex items-center gap-2">
                      <Info className="w-4 h-4 text-sky-400" />
                      <span className="text-xs font-bold text-slate-200 uppercase">
                        Stage Inspector: {selectedStage.stage} — {selectedStage.label}
                      </span>
                    </div>
                    <span
                      className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                        selectedStage.status === "COMPLETED"
                          ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                          : selectedStage.status === "ANOMALOUS"
                          ? "bg-amber-500/20 text-amber-400 border border-amber-500/40"
                          : selectedStage.status === "MISSING"
                          ? "bg-rose-500/20 text-rose-400 border border-rose-500/40"
                          : "bg-slate-800 text-slate-400"
                      }`}
                    >
                      Status: {selectedStage.status}
                    </span>
                  </div>

                  {selectedStage.status === "MISSING" && (
                    <div className="p-3 bg-rose-950/40 border border-rose-700/60 rounded-lg text-xs text-rose-300">
                      <strong>EVIDENCE GAP DETECTED:</strong> This mandatory supervisory workflow stage has no corresponding record in the database. Anomaly and execution gap scores reflect this absence.
                    </div>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                    <div>
                      <span className="text-slate-500 text-[10px] uppercase block">Record Reference</span>
                      <span className="text-sky-300 font-mono font-bold">
                        {selectedStage.canonical_record_id || "NOT_APPLICABLE"}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 text-[10px] uppercase block">Display Descriptor</span>
                      <span className="text-slate-200 font-semibold">{selectedStage.name}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 text-[10px] uppercase block">Workflow Context</span>
                      <span className="text-slate-400">{selectedStage.details}</span>
                    </div>
                  </div>

                  {/* Real Canonical Entity Data Attributes */}
                  {selectedStage.entity_data && Object.keys(selectedStage.entity_data).length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-900">
                      <div className="text-[10px] text-slate-400 uppercase font-bold mb-2">
                        Canonical Database Attributes
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs bg-slate-900/60 p-3 rounded-lg border border-slate-800/80">
                        {Object.entries(selectedStage.entity_data).map(([key, val]) => (
                          <div key={key} className="overflow-hidden">
                            <span className="text-[9px] text-slate-500 uppercase block font-mono">
                              {key.replace(/_/g, " ")}
                            </span>
                            <span className="text-slate-200 font-mono text-[11px] truncate block" title={String(val)}>
                              {val !== null && val !== undefined ? String(val) : "—"}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* VIEW 2: FULL EVIDENCE GRAPH (OPTIONAL ADVANCED VIEW WITH EXAMINER OPT-IN) */}
      {displayView === "FULL" && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-slate-400">Filter Nodes:</span>
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="bg-slate-950 border border-slate-800 text-slate-200 text-xs font-mono rounded px-2.5 py-1.5 focus:outline-none focus:border-sky-400"
              >
                <option value="ALL">Show All Entity Types (Top 40 Capped)</option>
                <option value="CSE">CSE Nodes</option>
                <option value="ASSET">Asset Nodes</option>
                <option value="ALERT">Alert Nodes</option>
                <option value="INVESTIGATION">Investigation Nodes</option>
                <option value="ESCALATION">Escalation Nodes</option>
                <option value="MISSING_EXPECTED">Missing Expected Nodes</option>
              </select>
            </div>

            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setZoom((z) => Math.min(2, z + 0.15))}
                className="p-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700"
                title="Zoom In"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
              <button
                onClick={() => setZoom((z) => Math.max(0.5, z - 0.15))}
                className="p-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700"
                title="Zoom Out"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
              <button
                onClick={() => setZoom(1)}
                className="p-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700"
                title="Reset Zoom"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            </div>
          </div>

          {isLoadingFull && (
            <div className="p-8 text-center text-slate-400 text-xs">
              Loading full NetworkX graph representation...
            </div>
          )}

          {fullGraphData && !isLoadingFull && (
            <div className="relative border border-slate-950 bg-[#050811] rounded-lg overflow-hidden h-[420px] cursor-grab">
              <svg
                className="w-full h-full"
                viewBox="0 0 1300 650"
                style={{
                  transform: `scale(${zoom})`,
                  transformOrigin: "top left",
                  transition: "transform 0.2s ease-out",
                }}
              >
                <defs>
                  <marker
                    id="arrow"
                    viewBox="0 0 10 10"
                    refX="22"
                    refY="5"
                    markerWidth="6"
                    markerHeight="6"
                    orient="auto-start-reverse"
                  >
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b" />
                  </marker>
                  <marker
                    id="arrow-missing"
                    viewBox="0 0 10 10"
                    refX="22"
                    refY="5"
                    markerWidth="6"
                    markerHeight="6"
                    orient="auto-start-reverse"
                  >
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#ef4444" />
                  </marker>
                </defs>

                {/* Render Edges */}
                {filteredEdges.map((edge, idx) => {
                  const p1 = nodePositions[edge.source];
                  const p2 = nodePositions[edge.target];
                  if (!p1 || !p2) return null;

                  const isMissing = edge.relationship === "MISSING_EXPECTED";
                  const isSelected = selectedEdge === edge;

                  return (
                    <g
                      key={idx}
                      onClick={() => setSelectedEdge(edge)}
                      className="cursor-pointer"
                    >
                      <line
                        x1={p1.x}
                        y1={p1.y}
                        x2={p2.x}
                        y2={p2.y}
                        stroke={
                          isSelected
                            ? "#38bdf8"
                            : isMissing
                            ? "#ef4444"
                            : "#475569"
                        }
                        strokeWidth={isSelected ? 3 : isMissing ? 2 : 1.5}
                        strokeDasharray={isMissing ? "4,4" : "none"}
                        markerEnd={
                          isMissing ? "url(#arrow-missing)" : "url(#arrow)"
                        }
                      />
                    </g>
                  );
                })}

                {/* Render Nodes */}
                {filteredNodes.map((node) => {
                  const pos = nodePositions[node.id];
                  if (!pos) return null;

                  const style =
                    nodeColorMap[node.entity_type] || nodeColorMap.CLOSURE;
                  const isSelected = selectedFullNode?.id === node.id;
                  const isMissingNode = node.entity_type === "MISSING_EXPECTED";

                  return (
                    <g
                      key={node.id}
                      transform={`translate(${pos.x}, ${pos.y})`}
                      onClick={() => {
                        setSelectedFullNode(node);
                        if (onSelectNode) onSelectNode(node);
                      }}
                      className="cursor-pointer"
                    >
                      <circle
                        r={isSelected ? 18 : 14}
                        fill={style.fill}
                        stroke={style.stroke}
                        strokeWidth={isSelected ? 3.5 : isMissingNode ? 2.5 : 2}
                        strokeDasharray={isMissingNode ? "3,3" : "none"}
                      />
                      <text
                        y={26}
                        textAnchor="middle"
                        fill={style.text}
                        fontSize="10"
                        fontFamily="monospace"
                        fontWeight="bold"
                      >
                        {node.entity_type}
                      </text>
                      <text
                        y={37}
                        textAnchor="middle"
                        fill="#94a3b8"
                        fontSize="8"
                        fontFamily="monospace"
                      >
                        {node.canonical_record_id.slice(0, 8)}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
