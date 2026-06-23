import React from 'react';

interface ConfidenceDisplayProps {
  confidence: number;
  label: string;
  size?: 'sm' | 'md' | 'lg';
}

export const ConfidenceDisplay: React.FC<ConfidenceDisplayProps> = ({
  confidence,
  label,
  size = 'md'
}) => {
  const percentage = (confidence * 100).toFixed(1);
  const color = confidence > 0.85 ? 'text-green-500' :
                confidence > 0.65 ? 'text-yellow-500' : 'text-red-500';
  const barColor = confidence > 0.85 ? 'bg-green-500' :
                   confidence > 0.65 ? 'bg-yellow-500' : 'bg-red-500';
  const barWidth = confidence > 0.85 ? 'w-3/4' :
                   confidence > 0.65 ? 'w-1/2' : 'w-1/4';

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-gray-400">{label}</span>
        <span className={`font-mono ${color}`}>{percentage}%</span>
      </div>
      <div className="w-full bg-gray-700 rounded-full h-2">
        <div
          className={`${barColor} h-2 rounded-full transition-all duration-500`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};
