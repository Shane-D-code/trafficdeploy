import React, { useState, useMemo } from 'react';
import type { Violation } from '../../types';

interface DetectionCanvasProps {
  image: string | null;
  violations: Violation[];
  annotatedImageUrl?: string | null;
  onViolationClick?: (violation: Violation) => void;
  confidenceThreshold?: number;
}

const CLASS_COLORS: Record<string, string> = {
  'NO HELMET': '#FF5D5D',
  'NO_SEATBELT': '#FF00FF',
  'TRIPLE RIDING': '#00FFFF',
  'WRONG SIDE': '#FF5D5D',
  'RED LIGHT': '#FF5D5D',
  'STOP LINE': '#7BFF7B',
  'ILLEGAL PARKING': '#FFD43B',
};

function computeIoU(a: number[], b: number[]): number {
  const x1 = Math.max(a[0], b[0]);
  const y1 = Math.max(a[1], b[1]);
  const x2 = Math.min(a[2], b[2]);
  const y2 = Math.min(a[3], b[3]);
  const inter = Math.max(0, x2 - x1) * Math.max(0, y2 - y1);
  const areaA = (a[2] - a[0]) * (a[3] - a[1]);
  const areaB = (b[2] - b[0]) * (b[3] - b[1]);
  const union = areaA + areaB - inter;
  return union > 0 ? inter / union : 0;
}

function centerDist(a: number[], b: number[]): number {
  const cax = (a[0] + a[2]) / 2, cay = (a[1] + a[3]) / 2;
  const cbx = (b[0] + b[2]) / 2, cby = (b[1] + b[3]) / 2;
  return Math.sqrt((cax - cbx) ** 2 + (cay - cby) ** 2);
}

function nmsFilter(violations: Violation[]): Violation[] {
  const sorted = [...violations].sort((a, b) => b.confidence - a.confidence);
  const kept: Violation[] = [];
  for (const v of sorted) {
    if (kept.every(k => computeIoU(v.bbox, k.bbox) <= 0.5)) kept.push(v);
  }
  return kept;
}

function groupViolations(violations: Violation[]): Violation[][] {
  const groups: Violation[][] = [];
  for (const v of violations) {
    let added = false;
    for (const g of groups) {
      if (g.some(m => computeIoU(v.bbox, m.bbox) > 0.3 || centerDist(v.bbox, m.bbox) < 50)) {
        g.push(v);
        added = true;
        break;
      }
    }
    if (!added) groups.push([v]);
  }
  return groups;
}

const DetectionCanvas: React.FC<DetectionCanvasProps> = ({
  image, violations, annotatedImageUrl, onViolationClick, confidenceThreshold = 0
}) => {
  const [imgNatural, setImgNatural] = useState({ w: 1, h: 1 });
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const filtered = useMemo(() => {
    const above = violations.filter(v => v.confidence >= confidenceThreshold);
    return nmsFilter(above);
  }, [violations, confidenceThreshold]);

  const groups = useMemo(() => groupViolations(filtered), [filtered]);

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

  const displayImage = annotatedImageUrl || image;

  return (
    <div className="relative inline-block w-full rounded-lg overflow-hidden scan-overlay">
      <img
        src={displayImage}
        alt="Detection"
        className="w-full"
        onLoad={(e) => {
          const img = e.target as HTMLImageElement;
          if (img.naturalWidth && img.naturalHeight) {
            setImgNatural({ w: img.naturalWidth, h: img.naturalHeight });
          }
        }}
      />

      {!annotatedImageUrl && groups.map((group, gi) => {
        const primary = group.reduce((a, b) => a.confidence > b.confidence ? a : b);
        const [x1, y1, x2, y2] = primary.bbox;
        const color = CLASS_COLORS[primary.type] || '#A3FF3C';
        const isHovered = hoveredIdx === gi;
        const sx = imgNatural.w || 1;
        const sy = imgNatural.h || 1;

        return (
          <div key={`box-${gi}`}>
            <div
              className="absolute cursor-pointer"
              style={{
                left: `${(x1 / sx) * 100}%`,
                top: `${(y1 / sy) * 100}%`,
                width: `${((x2 - x1) / sx) * 100}%`,
                height: `${((y2 - y1) / sy) * 100}%`,
                zIndex: isHovered ? 20 : 10,
                pointerEvents: 'auto',
              }}
              onClick={() => onViolationClick?.(primary)}
              onMouseEnter={() => setHoveredIdx(gi)}
              onMouseLeave={() => setHoveredIdx(null)}
            >
              <div
                className="absolute inset-0"
                style={{
                  border: `${isHovered ? 3 : 2}px solid ${color}`,
                  backgroundColor: color + '14',
                }}
              />
              {isHovered && (
                <div
                  className="absolute z-30 px-2 py-1 text-[10px] font-mono whitespace-nowrap rounded"
                  style={{
                    background: 'rgba(0,0,0,0.85)',
                    color: '#00ff41',
                    top: '-32px',
                    left: '0',
                    pointerEvents: 'none',
                  }}
                >
                  {primary.type.replace('_', ' ')} · {(primary.confidence * 100).toFixed(1)}% · [{Math.round(x1)},{Math.round(y1)},{Math.round(x2)},{Math.round(y2)}]
                </div>
              )}
            </div>
          </div>
        );
      })}

      {!annotatedImageUrl && groups.map((group, gi) => {
        const primary = group.reduce((a, b) => a.confidence > b.confidence ? a : b);
        const [x1, y1, x2, _y2] = primary.bbox;
        const sx = imgNatural.w || 1;
        const sy = imgNatural.h || 1;
        const placeAbove = (y1 / sy) * 100 > 8;

        return (
          <div
            key={`label-${gi}`}
            className="absolute flex flex-col gap-0.5"
            style={{
              left: `${(x1 / sx) * 100}%`,
              top: placeAbove
                ? `${((y1 / sy) * 100) - 0.5}%`
                : `${((_y2 / sy) * 100) + 0.5}%`,
              transform: placeAbove ? 'translateY(-100%)' : 'translateY(0)',
              zIndex: 15,
              pointerEvents: 'none',
              maxWidth: '140px',
            }}
          >
            {group.map((v, vi) => (
              <span
                key={vi}
                className="truncate"
                style={{
                  padding: '4px 8px',
                  borderRadius: '4px',
                  fontSize: '11px',
                  fontWeight: 600,
                  background: CLASS_COLORS[v.type] || '#A3FF3C',
                  color: '#000',
                  textOverflow: 'ellipsis',
                  overflow: 'hidden',
                  whiteSpace: 'nowrap',
                }}
              >
                {v.type.replace('_', ' ')} {(v.confidence * 100).toFixed(0)}%
              </span>
            ))}
          </div>
        );
      })}

      {violations.length > 0 && (
        <div
          className="absolute top-2 left-2 rounded font-mono"
          style={{
            background: 'rgba(0,0,0,0.6)',
            color: '#00ff41',
            fontSize: '12px',
            padding: '6px 10px',
            zIndex: 25,
            pointerEvents: 'none',
          }}
        >
          ⚠ {violations.length} VIOLATION{violations.length !== 1 ? 'S' : ''} DETECTED
        </div>
      )}
    </div>
  );
};

export default DetectionCanvas;
