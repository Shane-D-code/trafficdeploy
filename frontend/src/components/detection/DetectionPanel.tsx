import React from 'react';
import { HudCard } from '../common/HudCard';
import { PlateDisplay } from './PlateDisplay';
import { getFineAmount } from '../../utils/formatters';
import type { Violation } from '../../types';

const parseMeta = (v: Violation) => {
  if (!v.detectionDetails) return null;
  try { return JSON.parse(v.detectionDetails); } catch { return null; }
};

interface DetectionPanelProps {
  violation: Violation | null;
  violations: Violation[];
  image?: string | null;
  annotatedImageUrl?: string | null;
}

export const DetectionPanel: React.FC<DetectionPanelProps> = ({ violation, image, annotatedImageUrl }) => {
  const displayImage = annotatedImageUrl || image;

  if (!violation) {
    return (
      <HudCard title="Detection Info" accent fullHeight>
        {displayImage && (
          <div className="mb-4 rounded-lg overflow-hidden" style={{ border: '1px solid rgba(58,67,79,0.3)' }}>
            <img src={displayImage} alt="Preview" className="w-full h-auto" />
          </div>
        )}
        <div className="text-center py-6" style={{ color: '#6B7280' }}>
          <svg className="w-10 h-10 mx-auto mb-3" style={{ color: '#3A434F' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
          <p className="text-sm font-medium">Select a detection</p>
          <p className="text-xs mt-1 font-mono" style={{ color: '#3A434F' }}>Click on a bounding box to inspect</p>
        </div>
      </HudCard>
    );
  }

  const confidenceColor = violation.confidence > 0.8 ? '#A3FF3C' : violation.confidence > 0.6 ? '#FFD43B' : '#FF5D5D';

  return (
    <HudCard title="Detection Details" accent>
      {displayImage && (
        <div className="mb-4 rounded-lg overflow-hidden" style={{ border: '1px solid rgba(58,67,79,0.3)' }}>
          <img src={displayImage} alt="Preview" className="w-full h-auto" />
        </div>
      )}
      <div className="space-y-3">
        <div className="flex justify-between items-center py-2.5 px-3" style={{ background: '#141A20', border: '1px solid rgba(58,67,79,0.3)' }}>
          <span className="hud-label">Vehicle</span>
          <span className="text-sm text-[#EAEAEA] font-medium">{violation.vehicleType || violation.source?.replace('_', ' ') || 'Unknown'}</span>
        </div>
        <div className="flex justify-between items-center py-2.5 px-3" style={{ background: '#141A20', border: '1px solid rgba(58,67,79,0.3)' }}>
          <span className="hud-label">Confidence</span>
          <span className="text-sm font-bold font-mono" style={{ color: confidenceColor }}>{(violation.confidence * 100).toFixed(0)}%</span>
        </div>
        <div className="flex justify-between items-center py-2.5 px-3" style={{ background: '#141A20', border: '1px solid rgba(58,67,79,0.3)' }}>
          <span className="hud-label">Helmet</span>
          <span className="text-sm font-medium" style={{ color: violation.type === 'NO HELMET' || violation.type === 'NO_HELMET' ? '#FF5D5D' : '#A3FF3C' }}>
            {violation.type === 'NO HELMET' || violation.type === 'NO_HELMET' ? 'Not Wearing' : 'Detected'}
          </span>
        </div>
        {violation.rider_count && violation.rider_count > 0 && (
          <div className="flex justify-between items-center py-2.5 px-3" style={{ background: '#141A20', border: '1px solid rgba(58,67,79,0.3)' }}>
            <span className="hud-label">Riders</span>
            <span className="text-sm font-bold font-mono" style={{ color: '#FFD43B' }}>{violation.rider_count}</span>
          </div>
        )}
        {violation.plateText && (
          <div className="py-2.5 px-3" style={{ background: '#141A20', border: '1px solid rgba(58,67,79,0.3)' }}>
            <span className="hud-label block mb-2">License Plate</span>
            <PlateDisplay plateText={violation.plateText} confidence={violation.plateConfidence || 0} valid={violation.plateValid || false} />
            <div className="flex gap-3 mt-1.5 text-[10px] font-mono" style={{ color: '#6B7280' }}>
              {violation.plateConfidence !== undefined && (
                <span>Plate: {(violation.plateConfidence * 100).toFixed(0)}%</span>
              )}
              {violation.plateValid !== undefined && (
                <span>Valid: {violation.plateValid ? 'Yes' : 'No'}</span>
              )}
            </div>
          </div>
        )}
        <div className="flex justify-between items-center py-2.5 px-3" style={{ background: 'rgba(255,93,93,0.05)', border: '1px solid rgba(255,93,93,0.2)' }}>
          <span className="hud-label">Violation</span>
          <span className="text-sm font-bold" style={{ color: '#FF5D5D' }}>{violation.type.replace('_', ' ')}</span>
        </div>
        {violation.explanation && (
          <div className="py-2.5 px-3" style={{ background: 'rgba(163,255,60,0.03)', border: '1px solid rgba(163,255,60,0.15)' }}>
            <span className="hud-label block mb-1">Details</span>
            <span className="text-xs text-[#9CA3AF] font-mono leading-relaxed">{violation.explanation}</span>
          </div>
        )}
        <div className="flex justify-between items-center py-2.5 px-3" style={{ background: 'rgba(255,212,59,0.05)', border: '1px solid rgba(255,212,59,0.2)' }}>
          <span className="hud-label">Penalty</span>
          <span className="text-sm font-bold font-mono" style={{ color: '#FFD43B' }}>{getFineAmount(violation.type)}</span>
        </div>
        <div className="flex justify-between items-center py-2.5 px-3" style={{ background: '#141A20', border: '1px solid rgba(58,67,79,0.3)' }}>
          <span className="hud-label">Timestamp</span>
          <span className="text-xs text-[#EAEAEA] font-mono">{new Date(violation.timestamp).toLocaleTimeString()}</span>
        </div>
        {(() => {
          const meta = parseMeta(violation);
          if (!meta) return null;
          const extras: [string, string][] = [];
          if (meta.detection_confidence) extras.push(['Detection Conf.', `${(meta.detection_confidence * 100).toFixed(0)}%`]);
          if (meta.ocr_confidence) extras.push(['OCR Conf.', `${(meta.ocr_confidence * 100).toFixed(0)}%`]);
          if (meta.inference_time_ms) extras.push(['Inference', `${meta.inference_time_ms}ms`]);
          if (meta.source) extras.push(['Source', meta.source]);
          if (extras.length === 0) return null;
          return extras.map(([label, value]) => (
            <div key={label} className="flex justify-between items-center py-2.5 px-3" style={{ background: '#141A20', border: '1px solid rgba(58,67,79,0.3)' }}>
              <span className="hud-label">{label}</span>
              <span className="text-xs text-[#EAEAEA] font-mono">{value}</span>
            </div>
          ));
        })()}
      </div>
    </HudCard>
  );
};
