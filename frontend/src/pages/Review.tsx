import React, { useState, useEffect, useCallback } from 'react';
import { HudCard } from '../components/common/HudCard';
import { HudButton } from '../components/common/HudButton';
import { reviewApi, Incident } from '../api/review';

type FilterStatus = 'pending' | 'approved' | 'rejected' | 'false_positive' | 'all';

const FINE_COLORS: Record<string, string> = {
  'NO HELMET': '#FF5D5D',
  'NO_HELMET': '#FF5D5D',
  'NO SEATBELT': '#FFD43B',
  'NO_SEATBELT': '#FFD43B',
  'TRIPLE RIDING': '#D455FF',
  'TRIPLE_RIDING': '#D455FF',
  'WRONG SIDE': '#FF6B9D',
  'WRONG_SIDE': '#FF6B9D',
  'STOP LINE': '#3CE0A3',
  'STOP_LINE': '#3CE0A3',
  'RED LIGHT': '#FF2222',
  'RED_LIGHT': '#FF2222',
  'ILLEGAL PARKING': '#FF9F43',
  'ILLEGAL_PARKING': '#FF9F43',
};

const SEVERITY_COLORS: Record<string, string> = {
  low: '#3CE0A3',
  medium: '#FFD43B',
  high: '#FF9F43',
  critical: '#FF5D5D',
};

const STATUS_BADGES: Record<string, { color: string; label: string }> = {
  pending: { color: '#FFD43B', label: 'Pending Review' },
  approved: { color: '#3CE0A3', label: 'Approved' },
  rejected: { color: '#FF5D5D', label: 'Rejected' },
  false_positive: { color: '#FF9F43', label: 'False Positive' },
};

const Review: React.FC = () => {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selected, setSelected] = useState<Incident | null>(null);
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [filter, setFilter] = useState<FilterStatus>('pending');
  const [isLoading, setIsLoading] = useState(true);

  const fetchIncidents = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await reviewApi.getIncidents({ status: filter, limit: 100 });
      const data = res.data;
      const items = data.incidents || [];
      setIncidents(items);
      if (items.length > 0 && !selected) setSelected(items[0]);
      else if (items.length === 0) setSelected(null);
    } catch (err) {
      console.error('Failed to fetch incidents:', err);
      setIncidents([]);
    } finally {
      setIsLoading(false);
    }
  }, [filter, selected]);

  useEffect(() => { fetchIncidents(); }, [filter]);

  const handleApprove = async () => {
    if (!selected || isSubmitting) return;
    setIsSubmitting(true);
    try {
      await reviewApi.approveIncident(selected.incidentId, { officerId: 'officer-1', notes });
      setNotes('');
      fetchIncidents();
    } catch (err) {
      console.error('Failed to approve:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!selected || isSubmitting) return;
    if (!window.confirm('Are you sure you want to reject this incident?')) return;
    setIsSubmitting(true);
    try {
      await reviewApi.rejectIncident(selected.incidentId, { officerId: 'officer-1', reason: notes });
      setNotes('');
      fetchIncidents();
    } catch (err) {
      console.error('Failed to reject:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFalsePositive = async () => {
    if (!selected || isSubmitting) return;
    if (!window.confirm('Mark this incident as false positive?')) return;
    setIsSubmitting(true);
    try {
      await reviewApi.falsePositive(selected.incidentId, { officerId: 'officer-1', notes });
      setNotes('');
      fetchIncidents();
    } catch (err) {
      console.error('Failed to mark false positive:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const getSeverity = (inc: Incident): string => {
    if (!inc.totalFine) return 'medium';
    if (inc.totalFine >= 5000) return 'critical';
    if (inc.totalFine >= 2000) return 'high';
    if (inc.totalFine >= 1000) return 'medium';
    return 'low';
  };

  const pendingCount = incidents.filter(i => i.summary.status === 'pending').length;

  return (
    <>
      <div className="flex items-center justify-between mb-2">
        <div>
          <h1 className="text-lg font-heading text-[#EAEAEA] tracking-widest">REVIEW PANEL</h1>
          <p className="text-xs text-[#6B7280] font-mono mt-0.5 tracking-wider">
            {incidents.length} INCIDENTS
            {pendingCount > 0 && <span className="text-[#FFD43B] ml-2">({pendingCount} pending)</span>}
          </p>
        </div>
        <div className="flex gap-2">
          {(['pending', 'approved', 'rejected', 'false_positive', 'all'] as FilterStatus[]).map(f => (
            <button
              key={f}
              onClick={() => { setFilter(f); setSelected(null); }}
              className={`px-3 py-1 text-xs font-mono rounded transition-all ${
                filter === f ? 'bg-blue-600 text-white' : 'text-[#6B7280] hover:text-white'
              }`}
              style={{ background: filter === f ? undefined : '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}
            >
              {f.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5" style={{ minHeight: '500px' }}>
        <div className="lg:col-span-1">
          <HudCard title="Incidents" accent>
            {isLoading ? (
              <div className="flex items-center justify-center h-48">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#A3FF3C]" />
              </div>
            ) : (
              <div className="space-y-2 max-h-[600px] overflow-y-auto">
                {incidents.length === 0 ? (
                  <div className="text-center py-8" style={{ color: '#6B7280' }}>
                    <p className="text-sm">No incidents found</p>
                  </div>
                ) : (
                  incidents.map((inc) => {
                    const severity = getSeverity(inc);
                    const badge = STATUS_BADGES[inc.summary.status] || STATUS_BADGES.pending;
                    return (
                      <div
                        key={inc.incidentId}
                        className="p-3 rounded-lg cursor-pointer transition-all"
                        style={{
                          background: selected?.incidentId === inc.incidentId
                            ? 'rgba(59,130,246,0.1)'
                            : '#0B0F13',
                          border: selected?.incidentId === inc.incidentId
                            ? '1px solid rgba(59,130,246,0.3)'
                            : '1px solid rgba(58,67,79,0.2)',
                        }}
                        onClick={() => { setSelected(inc); setNotes(''); }}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-mono text-[#EAEAEA] truncate">
                                {inc.summary.license_plate || 'Unknown'}
                              </span>
                              <span className="text-[10px] font-mono shrink-0" style={{ color: SEVERITY_COLORS[severity] }}>
                                ● {inc.summary.total_violations} viol.
                              </span>
                            </div>
                            <div className="flex items-center gap-2 mt-1">
                              <span
                                className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                                style={{ background: `${badge.color}20`, color: badge.color }}
                              >
                                {badge.label}
                              </span>
                              <span className="text-[10px] text-[#6B7280] font-mono">
                                {inc.summary.timestamp ? new Date(inc.summary.timestamp).toLocaleDateString() : ''}
                              </span>
                            </div>
                            {inc.totalFine > 0 && (
                              <div className="text-xs font-mono mt-1" style={{ color: '#A3FF3C' }}>
                                ₹{inc.totalFine.toLocaleString()}
                              </div>
                            )}
                          </div>
                          <div className="w-12 h-12 rounded-lg overflow-hidden shrink-0 ml-2 bg-[#1a1a2e]">
                            {inc.summary.evidence_path ? (
                              <img
                                src={inc.summary.evidence_path}
                                alt="Evidence"
                                className="w-full h-full object-cover"
                                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                              />
                            ) : (
                              <div className="w-full h-full flex items-center justify-center text-[#6B7280] text-xs">N/A</div>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            )}
          </HudCard>
        </div>

        <div className="lg:col-span-2">
          <HudCard title={selected ? `Incident #${selected.incidentId.slice(0, 8)}` : 'Select Incident'} accent fullHeight>
            {selected ? (
              <div className="space-y-4 h-full flex flex-col">
                <div className="relative rounded-lg overflow-hidden shrink-0 bg-[#0B0F13] border border-[rgba(58,67,79,0.2)]">
                  {selected.summary.evidence_path ? (
                    <img
                      src={selected.summary.evidence_path}
                      alt="Annotated evidence"
                      className="w-full h-64 object-contain"
                    />
                  ) : (
                    <div className="w-full h-64 flex items-center justify-center text-[#6B7280]">
                      No evidence image available
                    </div>
                  )}
                  <div className="absolute top-2 left-2 flex items-center gap-2 bg-black/60 px-2 py-1 rounded">
                    <span
                      className="w-2 h-2 rounded-full inline-block"
                      style={{
                        background: selected.summary.status === 'approved' ? '#3CE0A3'
                          : selected.summary.status === 'rejected' ? '#FF5D5D'
                          : '#FFD43B',
                      }}
                    />
                    <span className="text-xs font-mono text-white/80">
                      {(STATUS_BADGES[selected.summary.status] || STATUS_BADGES.pending).label}
                    </span>
                  </div>
                  <div className="absolute bottom-2 right-2 bg-black/70 px-2 py-1 rounded">
                    <span className="text-xs font-mono" style={{ color: '#A3FF3C' }}>
                      {(selected.summary.max_confidence * 100).toFixed(1)}% confidence
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-3 shrink-0">
                  {[
                    ['Violations', String(selected.summary.total_violations)],
                    ['Fine', `₹${selected.totalFine.toLocaleString()}`],
                    ['Plate', selected.summary.license_plate || 'N/A'],
                    ['Severity', getSeverity(selected).toUpperCase()],
                  ].map(([label, value]) => (
                    <div key={label} className="p-3" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}>
                      <p className="text-[10px] font-mono" style={{ color: '#6B7280' }}>{label}</p>
                      <p className="text-sm font-bold mt-1" style={{
                        color: label === 'Severity' ? SEVERITY_COLORS[getSeverity(selected)]
                          : label === 'Fine' ? '#A3FF3C'
                          : '#EAEAEA',
                      }}>{value}</p>
                    </div>
                  ))}
                </div>

                {selected.violations.length > 0 && (
                  <div className="flex-1 min-h-0 overflow-y-auto">
                    <h3 className="text-xs font-mono mb-2" style={{ color: '#6B7280' }}>VIOLATIONS</h3>
                    <div className="space-y-1.5">
                      {selected.violations.map((v: any, i: number) => (
                        <div
                          key={i}
                          className="flex items-center justify-between p-2 rounded-lg"
                          style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <span className="text-xs font-semibold shrink-0" style={{
                              color: FINE_COLORS[v.violation_type] || '#EAEAEA',
                            }}>
                              ● {v.violation_type?.replace(/_/g, ' ')}
                            </span>
                            <span className="text-[10px] font-mono text-[#6B7280]">
                              {(v.confidence * 100).toFixed(1)}%
                            </span>
                            {v.plate_text && (
                              <span className="text-[10px] font-mono text-[#A3FF3C] truncate">
                                {v.plate_text}
                              </span>
                            )}
                          </div>
                          <span className="text-xs font-mono shrink-0 ml-2" style={{ color: '#A3FF3C' }}>
                            ₹{(FINE_COLORS[v.violation_type] ? 500 : 500)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {selected.fineBreakdown && selected.fineBreakdown.breakdown.length > 0 && (
                  <div className="shrink-0 p-4 rounded-lg" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}>
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-xs font-mono text-[#6B7280]">FINE BREAKDOWN</h4>
                      <span className="text-lg font-bold font-mono" style={{ color: '#A3FF3C' }}>
                        ₹{selected.totalFine.toLocaleString()}
                      </span>
                    </div>
                    <div className="space-y-1">
                      {selected.fineBreakdown.breakdown.map((b, i) => (
                        <div key={i} className="flex items-center justify-between text-xs font-mono">
                          <span style={{ color: FINE_COLORS[b.violation_type] || '#EAEAEA' }}>
                            {b.violation_type.replace(/_/g, ' ')}
                          </span>
                          <span style={{ color: '#A3FF3C' }}>₹{b.fine}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="shrink-0">
                  <label className="block text-xs font-mono mb-1" style={{ color: '#6B7280' }}>Officer Notes</label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    className="w-full p-2 text-white resize-none text-sm rounded-lg"
                    style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}
                    rows={2}
                    placeholder="Enter review notes..."
                  />
                </div>

                {selected.canApprove && (
                  <div className="flex gap-2 shrink-0">
                    <HudButton
                      size="sm"
                      className="flex-1 text-xs"
                      onClick={handleApprove}
                      disabled={isSubmitting}
                      style={{ background: 'rgba(60,224,163,0.15)', borderColor: '#3CE0A3' }}
                    >
                      {isSubmitting ? 'Processing...' : '✅ Approve & Issue Fine'}
                    </HudButton>
                    <HudButton
                      size="sm"
                      className="flex-1 text-xs"
                      onClick={handleFalsePositive}
                      disabled={isSubmitting}
                      style={{ background: 'rgba(255,159,67,0.15)', borderColor: '#FF9F43' }}
                    >
                      ⚠️ False Positive
                    </HudButton>
                    <HudButton
                      size="sm"
                      variant="danger"
                      className="flex-1 text-xs"
                      onClick={handleReject}
                      disabled={isSubmitting}
                    >
                      ❌ Reject
                    </HudButton>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center justify-center h-64" style={{ color: '#6B7280' }}>
                <div className="text-center">
                  <p className="text-3xl mb-2">!</p>
                  <p className="font-mono text-sm">No incident selected</p>
                  <p className="text-xs mt-1">Select an incident from the list to review violations and issue fines</p>
                </div>
              </div>
            )}
          </HudCard>
        </div>
      </div>
    </>
  );
};

export default Review;
