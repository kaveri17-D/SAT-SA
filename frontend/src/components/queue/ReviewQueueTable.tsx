import React, { useState, useMemo } from 'react';
import { QueueItem } from '../../types/api';
import { PriorityBandBadge, StatusBadge, CompletenessGauge } from '../common/Badges';
import { ArrowUpDown, Search, Filter, ShieldAlert } from 'lucide-react';

interface QueueTableProps {
  items: QueueItem[];
  onSelectItem: (item: QueueItem) => void;
}

export const ReviewQueueTable: React.FC<QueueTableProps> = ({ items, onSelectItem }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [bandFilter, setBandFilter] = useState('ALL');
  const [sortField, setSortField] = useState<'rank' | 'priority_score' | 'status'>('rank');
  const [sortAsc, setSortAsc] = useState(true);

  const filteredItems = useMemo(() => {
    return items.filter(item => {
      const matchSearch =
        item.queue_item_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.cse_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.finding_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.rationale.toLowerCase().includes(searchTerm.toLowerCase());

      const matchStatus = statusFilter === 'ALL' || item.status === statusFilter;
      const matchBand = bandFilter === 'ALL' || item.priority_band === bandFilter;

      return matchSearch && matchStatus && matchBand;
    }).sort((a, b) => {
      let valA: any = a[sortField];
      let valB: any = b[sortField];

      if (typeof valA === 'string') valA = valA.toLowerCase();
      if (typeof valB === 'string') valB = valB.toLowerCase();

      if (valA < valB) return sortAsc ? -1 : 1;
      if (valA > valB) return sortAsc ? 1 : -1;
      return 0;
    });
  }, [items, searchTerm, statusFilter, bandFilter, sortField, sortAsc]);

  const toggleSort = (field: 'rank' | 'priority_score' | 'status') => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-4">
      {/* Header & Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h3 className="text-sm font-mono font-bold text-white flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-cyan-400" />
            Ranked Supervisory Review Queue ({filteredItems.length} Queue Items)
          </h3>
          <p className="text-xs text-slate-400">Two-pass diversity prioritized queue derived from decomposable risk scores</p>
        </div>

        {/* Filter Controls */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Search CSE, Finding, Rule..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded text-xs font-mono text-slate-200 pl-8 pr-3 py-1.5 focus:outline-none focus:border-cyan-500 w-48"
            />
          </div>

          <div className="flex items-center gap-1 bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-xs font-mono text-slate-300">
            <Filter className="w-3.5 h-3.5 text-slate-500" />
            <select
              value={bandFilter}
              onChange={e => setBandFilter(e.target.value)}
              className="bg-transparent focus:outline-none text-xs font-mono"
            >
              <option value="ALL" className="bg-slate-900">All Bands</option>
              <option value="CRITICAL" className="bg-slate-900">CRITICAL Band</option>
              <option value="HIGH" className="bg-slate-900">HIGH Band</option>
              <option value="MEDIUM" className="bg-slate-900">MEDIUM Band</option>
              <option value="LOW" className="bg-slate-900">LOW Band</option>
            </select>
          </div>

          <div className="flex items-center gap-1 bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-xs font-mono text-slate-300">
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="bg-transparent focus:outline-none text-xs font-mono"
            >
              <option value="ALL" className="bg-slate-900">All Statuses</option>
              <option value="NEW" className="bg-slate-900">NEW</option>
              <option value="IN_REVIEW" className="bg-slate-900">IN_REVIEW</option>
              <option value="ESCALATED" className="bg-slate-900">ESCALATED</option>
              <option value="RESOLVED" className="bg-slate-900">RESOLVED</option>
              <option value="DISMISSED" className="bg-slate-900">DISMISSED</option>
            </select>
          </div>
        </div>
      </div>

      {/* Table Content */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono">
          <thead>
            <tr className="border-b border-slate-800 text-slate-400 text-[11px] uppercase bg-slate-950">
              <th className="py-3 px-3 cursor-pointer hover:text-white" onClick={() => toggleSort('rank')}>
                <div className="flex items-center gap-1">RANK <ArrowUpDown className="w-3 h-3" /></div>
              </th>
              <th className="py-3 px-3">CSE IDENTIFIER</th>
              <th className="py-3 px-3 cursor-pointer hover:text-white" onClick={() => toggleSort('priority_score')}>
                <div className="flex items-center gap-1">PRIORITY BAND & SCORE <ArrowUpDown className="w-3 h-3" /></div>
              </th>
              <th className="py-3 px-3">EVIDENCE COMPLETENESS</th>
              <th className="py-3 px-3">SUPERVISORY RATIONALE</th>
              <th className="py-3 px-3 cursor-pointer hover:text-white" onClick={() => toggleSort('status')}>
                <div className="flex items-center gap-1">STATUS <ArrowUpDown className="w-3 h-3" /></div>
              </th>
              <th className="py-3 px-3 text-right">ACTION</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {filteredItems.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-500 font-mono">
                  No review queue items match the current filters.
                </td>
              </tr>
            ) : (
              filteredItems.map(item => (
                <tr
                  key={item.queue_item_id}
                  onClick={() => onSelectItem(item)}
                  className="hover:bg-slate-850/60 cursor-pointer transition"
                >
                  <td className="py-3.5 px-3 font-bold text-cyan-400">
                    #{item.rank}
                  </td>
                  <td className="py-3.5 px-3">
                    <span className="font-bold text-slate-200 block">{item.cse_id.slice(0, 16)}</span>
                    <span className="text-[10px] text-slate-500">Finding: {item.finding_id.slice(0, 12)}</span>
                  </td>
                  <td className="py-3.5 px-3">
                    <PriorityBandBadge band={item.priority_band} score={item.priority_score} />
                  </td>
                  <td className="py-3.5 px-3">
                    <CompletenessGauge score={item.explanation?.evidence_completeness ?? 85} />
                  </td>
                  <td className="py-3.5 px-3 text-slate-300 max-w-xs truncate" title={item.rationale}>
                    {item.rationale}
                  </td>
                  <td className="py-3.5 px-3">
                    <StatusBadge status={item.status} />
                  </td>
                  <td className="py-3.5 px-3 text-right">
                    <button
                      onClick={e => {
                        e.stopPropagation();
                        onSelectItem(item);
                      }}
                      className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-400 text-[11px] font-bold border border-slate-700"
                    >
                      Inspect Finding
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
