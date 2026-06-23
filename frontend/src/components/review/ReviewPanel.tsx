import React, { useState, useEffect } from 'react';

interface ReviewItem {
  id: string;
  violation_type: string;
  plate_text: string;
  confidence: number;
  image_url: string;
  timestamp: string;
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
        }));
        setItems(mapped);
        if (mapped.length > 0) setSelected(mapped[0]);
      }
    } catch (err) {
      console.error('Failed to fetch violations:', err);
    }
  };

  const handleApprove = async () => {
    if (!selected || isSubmitting) return;
    setIsSubmitting(true);
    try {
      const response = await fetch('/api/analytics/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: selected.id, status: 'approved', notes })
      });
      if (response.ok) {
        setReviewStatus('approved');
        fetchItems();
      }
    } catch (err) {
      console.error('Failed to approve:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!selected || isSubmitting) return;
    setIsSubmitting(true);
    try {
      const response = await fetch('/api/analytics/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: selected.id, status: 'rejected', notes })
      });
      if (response.ok) {
        setReviewStatus('rejected');
        fetchItems();
      }
    } catch (err) {
      console.error('Failed to reject:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex h-full" style={{ minHeight: '500px' }}>
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
              onClick={() => { setSelected(item); setReviewStatus('pending'); setNotes(''); }}
            >
              <div className="flex justify-between items-center">
                <span className={`font-mono text-xs ${
                  item.confidence > 0.85 ? 'text-green-400' : 'text-yellow-400'
                }`}>
                  {item.violation_type}
                </span>
                <span className="text-xs text-gray-400">{item.plate_text}</span>
              </div>
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

      <div className="flex-1 p-6">
        {selected ? (
          <div className="space-y-6">
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-lg font-bold text-gray-100">{selected.violation_type}</h2>
                <p className="text-gray-400 text-xs">
                  {new Date(selected.timestamp).toLocaleString()}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleApprove}
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 text-sm font-mono"
                >
                  Approve
                </button>
                <button
                  onClick={handleReject}
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 text-sm font-mono"
                >
                  Reject
                </button>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="bg-gray-800 p-3 rounded-lg">
                <p className="text-xs text-gray-400 font-mono">Confidence</p>
                <p className="text-lg font-bold text-gray-100">{(selected.confidence * 100).toFixed(1)}%</p>
              </div>
              <div className="bg-gray-800 p-3 rounded-lg">
                <p className="text-xs text-gray-400 font-mono">Plate</p>
                <p className="text-lg font-bold text-gray-100">{selected.plate_text}</p>
              </div>
              <div className="bg-gray-800 p-3 rounded-lg">
                <p className="text-xs text-gray-400 font-mono">Status</p>
                <p className={`text-lg font-bold capitalize ${
                  reviewStatus === 'approved' ? 'text-green-400' :
                  reviewStatus === 'rejected' ? 'text-red-400' : 'text-yellow-400'
                }`}>
                  {reviewStatus}
                </p>
              </div>
            </div>

            <div>
              <label className="block text-xs text-gray-400 font-mono mb-2">Officer Notes</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg p-3 text-white resize-none text-sm"
                rows={3}
                placeholder="Enter your review notes..."
              />
            </div>

            {reviewStatus !== 'pending' && (
              <div className={`p-3 rounded-lg text-sm ${
                reviewStatus === 'approved' ? 'bg-green-900/30 text-green-400 border border-green-700' :
                'bg-red-900/30 text-red-400 border border-red-700'
              }`}>
                {reviewStatus === 'approved'
                  ? 'Violation has been approved and marked as valid.'
                  : 'Violation has been rejected and flagged for review.'}
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
