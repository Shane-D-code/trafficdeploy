import React, { useEffect, useState } from 'react';

interface SummaryData {
  total: number;
  by_type: Record<string, number>;
  unique_plates: number;
  avg_confidence: number;
  insights: string[];
}

export const AISummary: React.FC = () => {
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [timeframe, setTimeframe] = useState<'daily' | 'weekly'>('daily');

  useEffect(() => {
    const fetchSummary = async () => {
      setLoading(true);
      try {
        const response = await fetch('/api/analytics/stats');
        if (response.ok) {
          const data = await response.json();
          const stats = data.data || {};

          const byType = stats.byType || {};
          const total = Object.values(byType).reduce((a: number, b: any) => a + (typeof b === 'number' ? b : 0), 0);

          setSummary({
            total,
            by_type: byType as Record<string, number>,
            unique_plates: stats.uniquePlates || 0,
            avg_confidence: stats.avgConfidence || 0,
            insights: generateInsights(byType as Record<string, number>),
          });
        }
      } catch {
        console.error('Failed to fetch summary');
      } finally {
        setLoading(false);
      }
    };

    fetchSummary();
  }, [timeframe]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32 text-gray-500">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!summary || summary.total === 0) {
    return (
      <div className="text-center py-6 text-gray-500">
        <p className="text-sm font-mono">No data available for summary</p>
      </div>
    );
  }

  const topViolation = Object.entries(summary.by_type)
    .sort(([, a], [, b]) => b - a)[0];

  return (
    <div className="space-y-4">
      <div className="flex gap-2 mb-3">
        <button
          onClick={() => setTimeframe('daily')}
          className={`px-3 py-1 text-xs rounded font-mono ${
            timeframe === 'daily' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-400'
          }`}
        >
          Daily
        </button>
        <button
          onClick={() => setTimeframe('weekly')}
          className={`px-3 py-1 text-xs rounded font-mono ${
            timeframe === 'weekly' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-400'
          }`}
        >
          Weekly
        </button>
      </div>

      <p className="text-sm text-gray-300 leading-relaxed">
        {timeframe === 'daily' ? 'Today' : 'This week'}, {summary.total} violations were detected.{' '}
        {topViolation && (
          <>{topViolation[0].replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())} violations were most common ({topViolation[1]}).{' '}
        </>
        )}
        Average confidence: {(summary.avg_confidence * 100).toFixed(1)}%.{' '}
        {summary.unique_plates} unique plates identified.
      </p>

      {summary.insights.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs text-gray-500 font-mono uppercase tracking-wider">Insights</p>
          {summary.insights.map((insight, idx) => (
            <p key={idx} className="text-xs text-gray-400 flex items-start gap-2">
              <span className="text-blue-400 mt-0.5">&#9656;</span>
              {insight}
            </p>
          ))}
        </div>
      )}
    </div>
  );
};

function generateInsights(byType: Record<string, number>): string[] {
  const insights: string[] = [];
  if (byType['NO HELMET'] > 10) insights.push('Increased helmet enforcement needed at high-risk areas');
  if (byType['NO SEATBELT'] > 5) insights.push('Seatbelt awareness campaign recommended');
  if (byType['RED LIGHT'] > 5) insights.push('Additional signal monitoring at peak hours');
  if (byType['TRIPLE RIDING'] > 5) insights.push('Targeted enforcement against triple riding');
  if (byType['WRONG SIDE'] > 3) insights.push('One-way street sign visibility should be reviewed');
  return insights.slice(0, 4);
}
