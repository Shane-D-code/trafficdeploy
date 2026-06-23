import React, { useEffect, useState } from 'react';

interface RiskData {
  plate: string;
  risk_score: number;
  risk_level: string;
  violation_count: number;
  recent_violations: number;
  last_violation: string;
}

export const RiskScoreCard: React.FC = () => {
  const [offenders, setOffenders] = useState<RiskData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('/api/analytics/violations?limit=100');
        if (response.ok) {
          const data = await response.json();
          const rows: any[] = data.data?.rows || [];

          const plateMap = new Map<string, { count: number; recent: number; last: string }>();
          const now = Date.now();
          const thirtyDays = 30 * 24 * 60 * 60 * 1000;

          for (const v of rows) {
            const plate = v.plate_text;
            if (!plate || plate === 'N/A') continue;

            const existing = plateMap.get(plate) || { count: 0, recent: 0, last: '' };
            existing.count += 1;

            const ts = new Date(v.timestamp).getTime();
            if (now - ts < thirtyDays) existing.recent += 1;
            if (ts > new Date(existing.last || 0).getTime()) existing.last = v.timestamp;

            plateMap.set(plate, existing);
          }

          const riskData: RiskData[] = Array.from(plateMap.entries())
            .filter(([_, d]) => d.count >= 3)
            .map(([plate, d]) => ({
              plate,
              violation_count: d.count,
              risk_score: Math.min(100, d.count * 8 + d.recent * 5),
              risk_level: d.count >= 8 ? 'F' : d.count >= 6 ? 'D' : d.count >= 4 ? 'C' : 'B',
              recent_violations: d.recent,
              last_violation: d.last,
            }))
            .sort((a, b) => b.risk_score - a.risk_score)
            .slice(0, 5);

          setOffenders(riskData);
        }
      } catch {
        console.error('Failed to load risk data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'F': return 'text-red-500';
      case 'D': return 'text-orange-500';
      case 'C': return 'text-yellow-500';
      case 'B': return 'text-blue-500';
      default: return 'text-green-500';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32 text-gray-500">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {offenders.length === 0 ? (
        <div className="text-center py-6 text-gray-500">
          <p className="text-sm font-mono">No repeat offenders detected</p>
        </div>
      ) : (
        offenders.map((item, idx) => (
          <div
            key={idx}
            className="flex items-center justify-between py-2 px-3 rounded-lg bg-gray-800/50 border border-gray-700"
          >
            <div className="flex items-center gap-3">
              <span className="text-xs text-gray-500 font-mono w-4">{idx + 1}</span>
              <div>
                <p className="text-sm font-medium text-gray-200">{item.plate}</p>
                <p className="text-xs text-gray-500">
                  {item.violation_count} violations ({item.recent_violations} recent)
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className={`text-lg font-bold font-mono ${getLevelColor(item.risk_level)}`}>
                {item.risk_level}
              </p>
              <p className="text-xs text-gray-500">Risk {item.risk_score.toFixed(0)}</p>
            </div>
          </div>
        ))
      )}
    </div>
  );
};
