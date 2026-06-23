import React from 'react';
import type { Violation } from '../../types';

interface DetectionCanvasProps {
  image: string | null;
  violations: Violation[];
  onViolationClick?: (violation: Violation) => void;
}

const CLASS_COLORS: Record<string, string> = {
  NO_HELMET: '#FF5D5D',
  NO_SEATBELT: '#FFD43B',
  TRIPLE_RIDING: '#A3FF3C',
  WRONG_SIDE: '#FF5D5D',
  RED_LIGHT: '#FF5D5D',
  STOP_LINE: '#7BFF7B',
  ILLEGAL_PARKING: '#FFD43B',
};

const DetectionCanvas: React.FC<DetectionCanvasProps> = ({ image, violations, onViolationClick }) => {
  if (!image) {
    return (
      <div className="aspect-video rounded-lg flex items-center justify-center" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.3)' }}>
        <div className="text-center">
          <svg className="w-16 h-16 mx-auto" style={{ color: '#3A434F' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <p className="text-sm text-[#6B7280] mt-3 font-mono">Upload an image to begin</p>
          <p className="text-xs text-[#3A434F] mt-1 font-mono">Supported formats: JPG, PNG</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative inline-block w-full rounded-lg overflow-hidden scan-overlay">
      <img src={image} alt="Detection" className="w-full" />
      {violations.map((v, i) => {
        const [x1, y1, x2, y2] = v.bbox;
        const color = CLASS_COLORS[v.type] || '#A3FF3C';
        return (
          <div
            key={i}
            className="absolute cursor-pointer group hover:z-10"
            style={{
              left: `${x1 * 100}%`,
              top: `${y1 * 100}%`,
              width: `${(x2 - x1) * 100}%`,
              height: `${(y2 - y1) * 100}%`,
            }}
            onClick={() => onViolationClick?.(v)}
          >
            <div className="w-full h-full absolute" style={{ border: '2px solid ' + color }} />
            <div
              className="absolute -top-7 left-0 px-2 py-0.5 text-[11px] font-medium font-mono whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity text-black"
              style={{ background: color }}
            >
              {v.type.replace('_', ' ')} ({(v.confidence * 100).toFixed(0)}%)
            </div>
          </div>
        );
      })}
      {violations.length > 0 && (
        <div className="absolute bottom-3 left-3 flex flex-wrap gap-1.5">
          {Array.from(new Set(violations.map(v => v.type))).map(type => (
            <span key={type} className="px-2 py-0.5 text-[10px] font-mono font-medium text-black"
              style={{ background: CLASS_COLORS[type] || '#A3FF3C' }}>
              {type.replace('_', ' ')}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

export default DetectionCanvas;
