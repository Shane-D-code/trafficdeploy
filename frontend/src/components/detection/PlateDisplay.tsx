import React from 'react';

interface PlateDisplayProps {
  plateText: string;
  confidence: number;
  valid: boolean;
}

export const PlateDisplay: React.FC<PlateDisplayProps> = ({ plateText, confidence, valid }) => {
  const borderColor = valid ? 'rgba(163,255,60,0.3)' : confidence > 0.5 ? 'rgba(255,212,59,0.3)' : 'rgba(255,93,93,0.3)';
  const bgColor = valid ? 'rgba(163,255,60,0.05)' : confidence > 0.5 ? 'rgba(255,212,59,0.05)' : 'rgba(255,93,93,0.05)';

  return (
    <div className="p-3" style={{ border: '1px solid ' + borderColor, background: bgColor }}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-lg font-bold tracking-widest text-[#EAEAEA] font-mono">{plateText}</span>
        <span className={`hud-tag ${valid ? 'hud-tag-green' : confidence > 0.5 ? 'hud-tag-yellow' : 'hud-tag-red'}`}>
          {valid ? 'Valid' : 'Low'}
        </span>
      </div>
      <div className="mt-2 flex items-center gap-2">
        <div className="hud-progress flex-1">
          <div className="hud-progress-fill" style={{ width: `${confidence * 100}%` }} />
        </div>
        <span className="text-xs text-[#6B7280] font-mono">{(confidence * 100).toFixed(0)}%</span>
      </div>
    </div>
  );
};
