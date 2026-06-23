import React from 'react';

interface ViolationTimelineProps {
  violations?: any[];
  realtime?: boolean;
}

export const ViolationTimeline: React.FC<ViolationTimelineProps> = ({
  violations = [],
  realtime = false
}) => {
  if (violations.length === 0) {
    return (
      <div className="text-center py-8 text-[#6B7280]">
        <p className="text-4xl mb-2">⏱️</p>
        <p className="font-mono text-sm">No violations yet</p>
        <p className="text-xs mt-1">{realtime ? 'Monitoring...' : 'Check back later'}</p>
      </div>
    );
  }

  const getViolationColor = (type: string): string => {
    const colors: Record<string, string> = {
      'NO HELMET': '#FF5D5D',
      'NO SEATBELT': '#FFD43B',
      'TRIPLE RIDING': '#A3FF3C',
      'WRONG SIDE': '#FF5D5D',
      'STOP LINE': '#7BFF7B',
      'RED LIGHT': '#FF5D5D',
      'ILLEGAL PARKING': '#FFD43B'
    };
    return colors[type] || '#6B7280';
  };

  return (
    <div className="space-y-3 max-h-96 overflow-y-auto pr-2">
      {violations.slice(0, 20).map((violation, index) => {
        const vtype = violation.type || violation.violation_type || 'UNKNOWN';
        return (
          <div key={index} className="flex items-start gap-3 pb-3" style={{ borderBottom: '1px solid rgba(58,67,79,0.3)' }}>
            <div className="w-0.5 h-full min-h-[2.5rem] mt-0.5" style={{ background: getViolationColor(vtype) }} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-[#EAEAEA] truncate">{vtype}</span>
                <span className="text-xs font-mono" style={{ color: '#A3FF3C' }}>
                  {(violation.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-xs text-[#6B7280] font-mono">
                  {violation.timestamp ? new Date(violation.timestamp).toLocaleTimeString() : ''}
                </span>
                <span className="text-xs text-[#3A434F]">•</span>
                <span className="text-xs text-[#6B7280] font-mono">
                  {violation.plateText || violation.plate_text || 'NO PLATE'}
                </span>
                {realtime && (
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};