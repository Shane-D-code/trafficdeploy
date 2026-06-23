import React from 'react';
import type { Violation } from '../../types';
import { formatConfidence, formatTime } from '../../utils/formatters';

interface ViolationListProps {
  violations: Violation[];
  onViolationSelect: (v: Violation) => void;
}

export const ViolationList: React.FC<ViolationListProps> = ({ violations, onViolationSelect }) => {
  return (
    <div className="space-y-2">
      {violations.map((v, i) => (
        <div
          key={i}
          className="cursor-pointer hover:opacity-80 transition-opacity p-3"
          style={{ borderLeft: '3px solid #A3FF3C', background: 'rgba(163,255,60,0.02)' }}
          onClick={() => onViolationSelect(v)}
        >
          <div className="flex items-center justify-between">
            <div className="min-w-0 flex-1">
              <span className="hud-tag hud-tag-green mb-1">{v.type.replace('_', ' ')}</span>
              <p className="text-xs text-[#6B7280] font-mono mt-0.5 truncate">
                {v.plateText || 'No plate'} · {formatTime(v.timestamp)}
              </p>
            </div>
            <div className="text-right ml-3 shrink-0">
              <p className="text-sm font-mono text-[#A3FF3C] font-bold">{formatConfidence(v.confidence)}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
