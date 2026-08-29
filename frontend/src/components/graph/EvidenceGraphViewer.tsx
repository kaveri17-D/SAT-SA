import React, { useState, useMemo } from 'react';
import { GraphData, GraphNode, GraphEdge, GraphAnomaly } from '../../types/api';
import { ZoomIn, ZoomOut, RotateCcw, AlertTriangle, Layers, Info } from 'lucide-react';

interface GraphViewerProps {
  graphData: GraphData | null;
  anomalies?: GraphAnomaly[];
  onSelectNode?: (node: GraphNode) => void;
}

export const EvidenceGraphViewer: React.FC<GraphViewerProps> = ({ graphData, anomalies = [], onSelectNode }) => {
  const [zoom, setZoom] = useState(1);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<GraphEdge | null>(null);
  const [filterType, setFilterType] = useState<string>('ALL');

  const nodeColorMap: Record<string, { bg: string; stroke: string; text: string; fill: string }> = {
    CSE: { bg: '#0f172a', stroke: '#38bdf8', text: '#38bdf8', fill: '#0369a1' },
    ASSET: { bg: '#0f172a', stroke: '#818cf8', text: '#818cf8', fill: '#4338ca' },
    ALERT: { bg: '#0f172a', stroke: '#f87171', text: '#f87171', fill: '#b91c1c' },
    INVESTIGATION: { bg: '#0f172a', stroke: '#fbbf24', text: '#fbbf24', fill: '#b45309' },
    ANALYST: { bg: '#0f172a', stroke: '#34d399', text: '#34d399', fill: '#047857' },
    ESCALATION: { bg: '#0f172a', stroke: '#c084fc', text: '#c084fc', fill: '#6b21a8' },
    CASE: { bg: '#0f172a', stroke: '#38bdf8', text: '#38bdf8', fill: '#1e40af' },
    CLOSURE: { bg: '#0f172a', stroke: '#94a3b8', text: '#94a3b8', fill: '#334155' },
    MISSING_EXPECTED: { bg: '#450a0a', stroke: '#ef4444', text: '#fca5a5', fill: '#991b1b' }
  };

  const filteredNodes = useMemo(() => {
    if (!graphData) return [];
    if (filterType === 'ALL') return graphData.nodes.slice(0, 40); // cap display to keep fast & clean
    return graphData.nodes.filter(n => n.entity_type === filterType).slice(0, 40);
  }, [graphData, filterType]);

  const filteredEdges = useMemo(() => {
    if (!graphData) return [];
    const nodeIds = new Set(filteredNodes.map(n => n.id));
    return graphData.edges.filter(e => nodeIds.has(e.source) && nodeIds.has(e.target));
  }, [graphData, filteredNodes]);

  // Layout positioning using deterministic grid/circle layout
  const nodePositions = useMemo(() => {
    const posMap: Record<string, { x: number; y: number }> = {};
    const typeGroups: Record<string, GraphNode[]> = {};

    filteredNodes.forEach(n => {
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
      MISSING_EXPECTED: 380
    };

    Object.entries(typeGroups).forEach(([type, nodes]) => {
      const colX = columns[type] || 500;
      const startY = 80;
      const spacingY = Math.min(60, 500 / Math.max(1, nodes.length));

      nodes.forEach((n, idx) => {
        posMap[n.id] = {
          x: colX,
          y: startY + idx * spacingY
        };
      });
    });

    return posMap;
  }, [filteredNodes]);

  if (!graphData) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-8 text-center text-slate-400 font-mono text-xs">
        Loading Supervisory Evidence Graph...
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-4">
      {/* Top Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div>
          <h3 className="text-xs font-mono font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            Supervisory Evidence Graph (NetworkX Provenance)
          </h3>
          <p className="text-[11px] text-slate-400">
            Nodes: <span className="text-white font-mono">{graphData.metrics.node_count}</span> | Edges: <span className="text-white font-mono">{graphData.metrics.edge_count}</span> | Missing Expected: <span className="text-rose-400 font-mono font-bold">{graphData.metrics.missing_expected_count}</span>
          </p>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={filterType}
            onChange={e => setFilterType(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-slate-200 text-xs font-mono rounded px-2.5 py-1.5"
          >
            <option value="ALL">Show All Entity Types</option>
            <option value="CSE">CSE Nodes</option>
            <option value="ASSET">Asset Nodes</option>
            <option value="ALERT">Alert Nodes</option>
            <option value="INVESTIGATION">Investigation Nodes</option>
            <option value="ESCALATION">Escalation Nodes</option>
            <option value="MISSING_EXPECTED">Missing Expected Nodes</option>
          </select>

          <button onClick={() => setZoom(z => Math.min(2, z + 0.15))} className="p-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700">
            <ZoomIn className="w-4 h-4" />
          </button>
          <button onClick={() => setZoom(z => Math.max(0.5, z - 0.15))} className="p-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700">
            <ZoomOut className="w-4 h-4" />
          </button>
          <button onClick={() => setZoom(1)} className="p-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700">
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* SVG Analytical Graph Canvas */}
      <div className="relative border border-slate-950 bg-[#050811] rounded-lg overflow-hidden h-[420px] cursor-grab">
        <svg
          className="w-full h-full"
          viewBox="0 0 1300 650"
          style={{ transform: `scale(${zoom})`, transformOrigin: 'top left', transition: 'transform 0.2s ease-out' }}
        >
          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b" />
            </marker>
            <marker id="arrow-missing" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#ef4444" />
            </marker>
          </defs>

          {/* Render Edges */}
          {filteredEdges.map((edge, idx) => {
            const p1 = nodePositions[edge.source];
            const p2 = nodePositions[edge.target];
            if (!p1 || !p2) return null;

            const isMissing = edge.relationship === 'MISSING_EXPECTED';
            const isSelected = selectedEdge === edge;

            return (
              <g key={idx} onClick={() => setSelectedEdge(edge)} className="cursor-pointer">
                <line
                  x1={p1.x}
                  y1={p1.y}
                  x2={p2.x}
                  y2={p2.y}
                  stroke={isSelected ? '#38bdf8' : isMissing ? '#ef4444' : '#475569'}
                  strokeWidth={isSelected ? 3 : isMissing ? 2 : 1.5}
                  strokeDasharray={isMissing ? '4,4' : 'none'}
                  markerEnd={isMissing ? 'url(#arrow-missing)' : 'url(#arrow)'}
                />
              </g>
            );
          })}

          {/* Render Nodes */}
          {filteredNodes.map(node => {
            const pos = nodePositions[node.id];
            if (!pos) return null;

            const style = nodeColorMap[node.entity_type] || nodeColorMap.CLOSURE;
            const isSelected = selectedNode?.id === node.id;
            const isMissingNode = node.entity_type === 'MISSING_EXPECTED';

            return (
              <g
                key={node.id}
                transform={`translate(${pos.x}, ${pos.y})`}
                onClick={() => {
                  setSelectedNode(node);
                  if (onSelectNode) onSelectNode(node);
                }}
                className="cursor-pointer"
              >
                <circle
                  r={isSelected ? 18 : 14}
                  fill={style.fill}
                  stroke={style.stroke}
                  strokeWidth={isSelected ? 3.5 : isMissingNode ? 2.5 : 2}
                  strokeDasharray={isMissingNode ? '3,3' : 'none'}
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

      {/* Selected Node / Edge Details Drawer */}
      {(selectedNode || selectedEdge) && (
        <div className="bg-slate-950 border border-slate-800 rounded-md p-3.5 flex items-start justify-between gap-4 text-xs font-mono">
          {selectedNode && (
            <div className="space-y-1">
              <div className="text-cyan-400 font-bold flex items-center gap-1.5">
                <Info className="w-3.5 h-3.5" /> Selected Entity Node
              </div>
              <p className="text-slate-200">ID: <span className="text-white">{selectedNode.id}</span></p>
              <p className="text-slate-400">Type: <span className="text-cyan-300 font-bold">{selectedNode.entity_type}</span> | Record: <span className="text-slate-300">{selectedNode.canonical_record_id}</span></p>
            </div>
          )}
          {selectedEdge && (
            <div className="space-y-1">
              <div className="text-amber-400 font-bold flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5" /> Selected Edge Relationship
              </div>
              <p className="text-slate-200">Relationship: <span className="text-amber-300 font-bold">{selectedEdge.relationship}</span></p>
              <p className="text-slate-400">From: <span className="text-slate-300">{selectedEdge.source.slice(0, 16)}</span> ➔ To: <span className="text-slate-300">{selectedEdge.target.slice(0, 16)}</span></p>
            </div>
          )}
          <button
            onClick={() => { setSelectedNode(null); setSelectedEdge(null); }}
            className="text-slate-500 hover:text-slate-300 font-bold"
          >
            ✕
          </button>
        </div>
      )}

      {/* Detected Graph Anomalies summary */}
      {anomalies.length > 0 && (
        <div className="space-y-2 pt-2 border-t border-slate-800">
          <div className="text-xs font-mono font-bold text-rose-400 flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4 text-rose-500" />
            Detected Graph Structural Anomalies ({anomalies.length})
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {anomalies.map((anom, idx) => (
              <div key={idx} className="bg-rose-950/30 border border-rose-900/60 rounded p-2.5 text-xs font-mono">
                <div className="text-rose-300 font-bold flex justify-between">
                  <span>{anom.anomaly_type}</span>
                  <span className="text-[10px] text-rose-400 bg-rose-950 px-1.5 rounded">{anom.severity}</span>
                </div>
                <p className="text-slate-300 text-[11px] mt-1">{anom.description}</p>
                <div className="text-[10px] text-slate-400 mt-1">
                  Observed: <span className="text-rose-200">{anom.observed_state}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
