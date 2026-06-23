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
        const response = await fetch('/api/insights/repeat-offenders');
        if (response.ok) {
          const body = await response.json();
          const items: any[] = body.data || [];
          setOffenders(
            items.slice(0, 5).map((o: any) => ({
              plate: o.plate,
              violation_count: o.count,
              risk_score: o.riskScore || 0,
              risk_level: o.riskLevel || 'low',
              recent_violations: o.count,
              last_violation: o.lastViolation || '',
            }))
          );
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
      case 'high': return 'text-red-500';
      case 'critical': return 'text-red-500';
      case 'medium': return 'text-yellow-500';
      case 'low': return 'text-green-500';
      default: return 'text-gray-500';
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
                {item.risk_level.toUpperCase()}
              </p>
              <p className="text-xs text-gray-500">Risk {item.risk_score.toFixed(0)}</p>
            </div>
          </div>
        ))
      )}
    </div>
  );
};
