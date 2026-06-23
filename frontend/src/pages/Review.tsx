import React, { useState, useEffect } from 'react';
import { HudCard } from '../components/common/HudCard';
import { HudButton } from '../components/common/HudButton';

interface ReviewItem {
  id: string;
  violation_type: string;
  plate_text: string;
  confidence: number;
  image_url: string;
  timestamp: string;
  status?: string;
}

const Review: React.FC = () => {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [selected, setSelected] = useState<ReviewItem | null>(null);
  const [notes, setNotes] = useState('');
  const [reviewStatus, setReviewStatus] = useState<string>('pending');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [filter, setFilter] = useState<string>('pending');

  useEffect(() => { fetchItems(); }, [filter]);

  const fetchItems = async () => {
    try {
      const response = await fetch(`/api/analytics/violations?limit=50${filter !== 'all' ? `&status=${filter}` : ''}`);
      if (response.ok) {
        const data = await response.json();
        const violations = data.data?.rows || [];
        const mapped = violations.map((v: any) => ({
          id: String(v.id),
          violation_type: v.violation_type || 'UNKNOWN',
          plate_text: v.plate_text || 'N/A',
          confidence: v.confidence || 0,
          image_url: v.evidence_path || v.image_path || '',
          timestamp: v.timestamp || '',
          status: v.status || 'pending',
        }));
        setItems(mapped);
        if (mapped.length > 0 && !selected) setSelected(mapped[0]);
      }
    } catch (err) {
      console.error('Failed to fetch violations:', err);
    }
  };

  const submitReview = async (status: string) => {
    if (!selected || isSubmitting) return;
    setIsSubmitting(true);
    try {
      const response = await fetch('/api/analytics/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: selected.id, status, notes }),
      });
      if (response.ok) {
        setReviewStatus(status);
        setNotes('');
        setTimeout(() => fetchItems(), 300);
      }
    } catch (err) {
      console.error(`Failed to ${status}:`, err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const statusColor = (s: string) =>
    s === 'approved' ? '#A3FF3C' : s === 'rejected' ? '#FF5D5D' : s === 'false_positive' ? '#FFD43B' : '#6B7280';

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-heading text-[#EAEAEA] tracking-widest">REVIEW PANEL</h1>
          <p className="text-xs text-[#6B7280] font-mono mt-0.5 tracking-wider">{items.length} VIOLATIONS</p>
        </div>
        <div className="flex gap-2">
          {['pending', 'approved', 'rejected', 'all'].map(f => (
            <button
              key={f}
              onClick={() => { setFilter(f); setSelected(null); setReviewStatus('pending'); }}
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
          <HudCard title="Violations" accent>
            <div className="space-y-2 max-h-[600px] overflow-y-auto">
              {items.length === 0 ? (
                <div className="text-center py-8" style={{ color: '#6B7280' }}>
                  <p className="text-sm">No violations found</p>
                </div>
              ) : (
                items.map((item) => (
                  <div
                    key={item.id}
                    className="p-3 rounded-lg cursor-pointer transition-all"
                    style={{
                      background: selected?.id === item.id ? 'rgba(59,130,246,0.1)' : '#0B0F13',
                      border: selected?.id === item.id ? '1px solid rgba(59,130,246,0.3)' : '1px solid rgba(58,67,79,0.2)',
                    }}
                    onClick={() => { setSelected(item); setReviewStatus(item.status || 'pending'); setNotes(''); }}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold" style={{ color: '#FF5D5D' }}>{item.violation_type}</span>
                      <span className="text-[10px] font-mono" style={{ color: statusColor(item.status || 'pending') }}>
                        {(item.status || 'pending').toUpperCase()}
                      </span>
                    </div>
                    <p className="text-xs font-mono mt-1" style={{ color: '#6B7280' }}>{item.plate_text}</p>
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-[10px] font-mono" style={{ color: '#A3FF3C' }}>
                        {(item.confidence * 100).toFixed(1)}%
                      </span>
                      <span className="text-[10px] font-mono" style={{ color: '#3A434F' }}>
                        {item.timestamp ? new Date(item.timestamp).toLocaleDateString() : ''}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </HudCard>
        </div>

        <div className="lg:col-span-2">
          <HudCard title={selected ? selected.violation_type : 'Select Violation'} accent fullHeight>
            {selected ? (
              <div className="space-y-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-xs font-mono" style={{ color: '#6B7280' }}>
                      {selected.timestamp ? new Date(selected.timestamp).toLocaleString() : ''}
                    </p>
                    <p className="text-xs font-mono mt-1" style={{ color: '#6B7280' }}>
                      Plate: {selected.plate_text}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <HudButton
                      size="sm"
                      className="text-xs"
                      onClick={() => submitReview('approved')}
                      disabled={isSubmitting}
                    >
                      Approve
                    </HudButton>
                    <HudButton
                      size="sm"
                      className="text-xs"
                      onClick={() => submitReview('false_positive')}
                      disabled={isSubmitting}
                    >
                      False Positive
                    </HudButton>
                    <HudButton
                      size="sm"
                      variant="danger"
                      className="text-xs"
                      onClick={() => submitReview('rejected')}
                      disabled={isSubmitting}
                    >
                      Reject
                    </HudButton>
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-3">
                  {[
                    ['Confidence', `${(selected.confidence * 100).toFixed(1)}%`],
                    ['Plate', selected.plate_text],
                    ['Status', (reviewStatus || 'pending').toUpperCase()],
                    ['Type', selected.violation_type],
                  ].map(([label, value]) => (
                    <div key={label} className="p-3" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}>
                      <p className="text-[10px] font-mono" style={{ color: '#6B7280' }}>{label}</p>
                      <p className="text-sm font-bold mt-1" style={{
                        color: label === 'Status'
                          ? statusColor(reviewStatus)
                          : label === 'Confidence'
                            ? '#A3FF3C' : '#EAEAEA',
                      }}>{value}</p>
                    </div>
                  ))}
                </div>

                {selected.image_url && (
                  <div className="rounded-lg overflow-hidden" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}>
                    <img src={selected.image_url} alt="Violation" className="w-full h-auto max-h-64 object-contain" />
                  </div>
                )}

                <div>
                  <label className="block text-xs font-mono mb-2" style={{ color: '#6B7280' }}>Officer Notes</label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    className="w-full p-3 text-white resize-none text-sm rounded-lg"
                    style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}
                    rows={3}
                    placeholder="Enter review notes..."
                  />
                </div>

                {reviewStatus !== 'pending' && (
                  <div className="p-3 rounded-lg text-sm" style={{
                    background: reviewStatus === 'approved' ? 'rgba(163,255,60,0.05)' : reviewStatus === 'false_positive' ? 'rgba(255,212,59,0.05)' : 'rgba(255,93,93,0.05)',
                    border: `1px solid ${reviewStatus === 'approved' ? 'rgba(163,255,60,0.3)' : reviewStatus === 'false_positive' ? 'rgba(255,212,59,0.3)' : 'rgba(255,93,93,0.3)'}`,
                    color: reviewStatus === 'approved' ? '#A3FF3C' : reviewStatus === 'false_positive' ? '#FFD43B' : '#FF5D5D',
                  }}>
                    {reviewStatus === 'approved' ? 'Violation approved and marked as valid.'
                      : reviewStatus === 'false_positive' ? 'Marked as false positive — will be excluded from metrics.'
                      : 'Violation rejected.'}
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center justify-center h-64" style={{ color: '#6B7280' }}>
                <div className="text-center">
                  <p className="text-3xl mb-2">!</p>
                  <p className="font-mono text-sm">No violation selected</p>
                  <p className="text-xs mt-1">Select a violation to review</p>
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
