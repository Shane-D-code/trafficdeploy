import React, { useState, useEffect } from 'react';

interface ReviewItem {
  id: string;
  violation_type: string;
  plate_text: string;
  confidence: number;
  image_url: string;
  timestamp: string;
  status?: string;
}

export const ReviewPanel: React.FC = () => {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [selected, setSelected] = useState<ReviewItem | null>(null);
  const [notes, setNotes] = useState('');
  const [reviewStatus, setReviewStatus] = useState<string>('pending');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    fetchItems();
  }, []);

  const fetchItems = async () => {
    try {
      const response = await fetch('/api/analytics/violations?limit=50');
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
        if (mapped.length > 0) setSelected(mapped[0]);
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
      console.error(`Failed to submit ${status}:`, err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const statusColor = (s: string) =>
    s === 'approved'
      ? '#A3FF3C'
      : s === 'rejected'
      ? '#FF5D5D'
      : s === 'false_positive'
      ? '#FFD43B'
      : '#6B7280';

  return (
    <div className="flex h-full" style={{ minHeight: '500px' }}>
      {/* List panel */}
      <div className="w-1/3 border-r border-gray-700 overflow-y-auto p-4">
        <h3 className="font-mono text-xs text-gray-400 mb-4 tracking-wider uppercase">Pending Review</h3>
        {items.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p className="text-sm">No violations found</p>
          </div>
        ) : (
          items.map((item) => (
            <div
              key={item.id}
              className={`p-3 rounded-lg cursor-pointer transition-colors mb-2 ${
                selected?.id === item.id
                  ? 'bg-blue-900/30 border border-blue-500'
                  : 'hover:bg-gray-800 border border-transparent'
              }`}
              onClick={() => { setSelected(item); setReviewStatus(item.status || 'pending'); setNotes(''); }}
            >
              <div className="flex justify-between items-center">
                <span className={`font-mono text-xs ${
                  item.confidence > 0.85 ? 'text-green-400' : 'text-yellow-400'
                }`}>
                  {item.violation_type}
                </span>
                <span className="text-[10px] font-mono" style={{ color: statusColor(item.status || 'pending') }}>
                  {(item.status || 'pending').toUpperCase()}
                </span>
              </div>
              <div className="text-xs text-gray-400 mt-0.5 font-mono">{item.plate_text}</div>
              <div className="text-xs text-gray-500 mt-1">
                {item.timestamp ? new Date(item.timestamp).toLocaleString() : ''}
              </div>
              <div className="text-xs text-gray-600 mt-1">
                {(item.confidence * 100).toFixed(1)}% confidence
              </div>
            </div>
          ))
        )}
      </div>

      {/* Detail panel */}
      <div className="flex-1 p-6 overflow-y-auto">
        {selected ? (
          <div className="space-y-5">
            <div className="flex justify-between items-start flex-wrap gap-3">
              <div>
                <h2 className="text-lg font-bold text-gray-100">{selected.violation_type}</h2>
                <p className="text-gray-400 text-xs">
                  {selected.timestamp ? new Date(selected.timestamp).toLocaleString() : ''}
                </p>
              </div>
              {/* THREE action buttons */}
              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={() => submitReview('approved')}
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-lg text-sm font-mono transition-colors disabled:opacity-50"
                  style={{ background: 'rgba(163,255,60,0.15)', color: '#A3FF3C', border: '1px solid rgba(163,255,60,0.4)' }}
                >
                  ✅ Approve
                </button>
                <button
                  onClick={() => submitReview('false_positive')}
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-lg text-sm font-mono transition-colors disabled:opacity-50"
                  style={{ background: 'rgba(255,212,59,0.15)', color: '#FFD43B', border: '1px solid rgba(255,212,59,0.4)' }}
                >
                  ⚠️ False Positive
                </button>
                <button
                  onClick={() => submitReview('rejected')}
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-lg text-sm font-mono transition-colors disabled:opacity-50"
                  style={{ background: 'rgba(255,93,93,0.15)', color: '#FF5D5D', border: '1px solid rgba(255,93,93,0.4)' }}
                >
                  ❌ Reject
                </button>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              {[
                ['Confidence', `${(selected.confidence * 100).toFixed(1)}%`],
                ['Plate', selected.plate_text],
                ['Status', (reviewStatus || 'pending').toUpperCase()],
              ].map(([label, value]) => (
                <div key={label} className="p-3 rounded-lg" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}>
                  <p className="text-xs font-mono" style={{ color: '#6B7280' }}>{label}</p>
                  <p className="text-sm font-bold mt-1" style={{
                    color: label === 'Status'
                      ? statusColor(reviewStatus)
                      : label === 'Confidence'
                      ? '#A3FF3C'
                      : '#EAEAEA',
                  }}>
                    {value}
                  </p>
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
                className="w-full rounded-lg p-3 text-white resize-none text-sm"
                style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}
                rows={3}
                placeholder="Enter your review notes..."
              />
            </div>

            {reviewStatus !== 'pending' && (
              <div
                className="p-3 rounded-lg text-sm"
                style={{
                  background: reviewStatus === 'approved'
                    ? 'rgba(163,255,60,0.05)'
                    : reviewStatus === 'false_positive'
                    ? 'rgba(255,212,59,0.05)'
                    : 'rgba(255,93,93,0.05)',
                  border: `1px solid ${statusColor(reviewStatus)}40`,
                  color: statusColor(reviewStatus),
                }}
              >
                {reviewStatus === 'approved'
                  ? 'Violation approved and marked as valid.'
                  : reviewStatus === 'false_positive'
                  ? 'Marked as false positive — will be excluded from metrics.'
                  : 'Violation rejected.'}
              </div>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <p className="text-3xl mb-2">📋</p>
              <p className="font-mono text-sm">No violation selected</p>
              <p className="text-xs mt-1">Select a violation from the list to review</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
