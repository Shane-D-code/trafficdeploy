import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { analyticsApi } from '../api/analytics';
import { HudCard } from '../components/common/HudCard';
import { HudButton } from '../components/common/HudButton';
import { HudSpinner } from '../components/common/HudSpinner';
import { Search, ChevronLeft, ChevronRight, RotateCcw } from 'lucide-react';
import type { ViolationRecord } from '../types';

const ViolationLogs: React.FC = () => {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState({ type: '', plate: '', page: '1', limit: '50', status: '' });
  const [toast, setToast] = useState<{ message: string; id?: string } | null>(null);
  const [undoTimers, setUndoTimers] = useState<Record<string, ReturnType<typeof setTimeout>>>({});

  const { data, isLoading } = useQuery({
    queryKey: ['violations', filters],
    queryFn: () => analyticsApi.getViolations(filters),
  });

  const fpMutation = useMutation({
    mutationFn: (id: string) => analyticsApi.markFalsePositive(id),
    onSuccess: (_, id) => {
      setToast({ message: 'Marked as false positive', id });
      setUndoTimers(prev => {
        const timer = setTimeout(() => {
          setUndoTimers(p => { const n = { ...p }; delete n[id]; return n; });
          setToast(null);
          queryClient.invalidateQueries({ queryKey: ['violations'] });
        }, 5000);
        return { ...prev, [id]: timer };
      });
      queryClient.invalidateQueries({ queryKey: ['violations'] });
    },
  });

  const undoMutation = useMutation({
    mutationFn: (id: string) => analyticsApi.undoFalsePositive(id),
    onSuccess: () => {
      const tid = toast?.id;
      setToast(null);
      if (tid && undoTimers[tid]) {
        clearTimeout(undoTimers[tid]);
        setUndoTimers(prev => { const n = { ...prev }; delete n[tid]; return n; });
      }
      queryClient.invalidateQueries({ queryKey: ['violations'] });
    },
  });

  const violations = data?.data?.data?.rows || [];
  const total = data?.data?.data?.total || 0;
  const page = parseInt(filters.page);

  const statusTabs = [
    { label: 'Active', value: '' },
    { label: 'False Positives', value: 'false_positive' },
    { label: 'All', value: 'all' },
  ];

  return (
    <>
      <div>
        <h1 className="text-lg font-heading text-[#EAEAEA] tracking-widest">VIOLATION LOGS</h1>
        <p className="text-xs text-[#6B7280] font-mono mt-0.5 tracking-wider">SEARCH AND REVIEW ALL RECORDED VIOLATIONS ({total} TOTAL)</p>
      </div>

      <HudCard title="Filters" accent>
        <div className="flex flex-wrap gap-3 items-center">
          <div className="relative flex-1 min-w-[200px] max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: '#6B7280' }} />
            <input type="text" placeholder="Violation type..."
              value={filters.type} onChange={(e) => setFilters(p => ({ ...p, type: e.target.value, page: '1' }))}
              className="hud-input w-full pl-9" />
          </div>
          <input type="text" placeholder="Plate number..."
            value={filters.plate} onChange={(e) => setFilters(p => ({ ...p, plate: e.target.value, page: '1' }))}
            className="hud-input w-48" />
          <div className="flex gap-1 ml-auto">
            {statusTabs.map(tab => (
              <button
                key={tab.value}
                onClick={() => setFilters(p => ({ ...p, status: tab.value, page: '1' }))}
                className={`px-3 py-1 text-xs font-mono rounded transition-all ${
                  filters.status === tab.value ? 'bg-blue-600 text-white' : 'text-[#6B7280] hover:text-white'
                }`}
                style={{ background: filters.status === tab.value ? undefined : '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </HudCard>

      {isLoading ? (
        <HudSpinner size="lg" text="Loading violations" />
      ) : (
        <>
          <HudCard title="Violations" accent>
            <div className="overflow-x-auto">
              <table className="hud-table w-full">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Plate</th>
                    <th>Confidence</th>
                    <th>Status</th>
                    <th>Timestamp</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {violations.length === 0 ? (
                    <tr><td colSpan={6} className="py-12 text-center text-sm" style={{ color: '#6B7280' }}>No violations found</td></tr>
                  ) : (
                    violations.map((v: ViolationRecord) => {
                      const isFP = v.status === 'false_positive';
                      const isUndoing = undoMutation.isPending && toast?.id === String(v.id);
                      return (
                        <tr key={v.id} className="transition-colors" style={{ cursor: 'default', opacity: isFP ? 0.6 : 1 }}>
                          <td>
                            <span className={`hud-tag ${isFP ? 'hud-tag-yellow' : 'hud-tag-red'}`}>{v.violation_type.replace('_', ' ')}</span>
                          </td>
                          <td className="text-sm font-mono" style={{ color: '#EAEAEA' }}>{v.plate_text || '-'}</td>
                          <td className="text-sm font-mono" style={{ color: '#A3FF3C' }}>{(v.confidence * 100).toFixed(0)}%</td>
                          <td>
                            <span className="text-xs font-mono px-2 py-0.5 rounded" style={{
                              background: isFP ? 'rgba(255,212,59,0.1)' : 'rgba(107,114,128,0.1)',
                              color: isFP ? '#FFD43B' : '#6B7280',
                              border: `1px solid ${isFP ? 'rgba(255,212,59,0.3)' : 'rgba(107,114,128,0.2)'}`,
                            }}>
                              {(v.status || 'pending').toUpperCase()}
                            </span>
                          </td>
                          <td className="text-sm font-mono" style={{ color: '#6B7280' }}>{new Date(v.timestamp).toLocaleString()}</td>
                          <td>
                            {!isFP ? (
                              <HudButton
                                size="sm"
                                className="text-xs"
                                onClick={() => fpMutation.mutate(String(v.id))}
                                disabled={fpMutation.isPending}
                              >
                                {fpMutation.isPending ? (
                                  <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white" />
                                ) : 'FP'}
                              </HudButton>
                            ) : (
                              <span className="text-xs font-mono" style={{ color: '#6B7280' }}>—</span>
                            )}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between mt-4 pt-4" style={{ borderTop: '1px solid rgba(58,67,79,0.3)' }}>
              <span className="text-xs font-mono" style={{ color: '#6B7280' }}>Page {page}</span>
              <div className="flex items-center gap-2">
                <HudButton size="sm" onClick={() => setFilters(p => ({ ...p, page: String(page - 1) }))} disabled={page <= 1}>
                  <ChevronLeft className="w-4 h-4" />
                </HudButton>
                <HudButton size="sm" onClick={() => setFilters(p => ({ ...p, page: String(page + 1) }))} disabled={violations.length < 50}>
                  <ChevronRight className="w-4 h-4" />
                </HudButton>
              </div>
            </div>
          </HudCard>

          {toast && (
            <div className="fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg" style={{
              background: '#1B232C',
              border: '1px solid rgba(255,212,59,0.3)',
              color: '#FFD43B',
            }}>
              <span className="text-sm font-mono">{toast.message}</span>
              {toast.id && undoTimers[toast.id] && (
                <HudButton
                  size="sm"
                  className="text-xs flex items-center gap-1"
                  onClick={() => undoMutation.mutate(toast.id!)}
                  disabled={undoMutation.isPending}
                >
                  <RotateCcw className="w-3 h-3" />
                  Undo
                </HudButton>
              )}
            </div>
          )}
        </>
      )}
    </>
  );
};

export default ViolationLogs;