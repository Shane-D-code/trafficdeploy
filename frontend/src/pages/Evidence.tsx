import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { HudCard } from '../components/common/HudCard';
import { HudButton } from '../components/common/HudButton';
import { ImageIcon } from 'lucide-react';
import type { EvidenceItem } from '../types';

const Evidence: React.FC = () => {
  const [selected, setSelected] = useState<EvidenceItem | null>(null);
  const [showAnnotated, setShowAnnotated] = useState(false);

  const { data: evidenceData, isLoading } = useQuery({
    queryKey: ['evidence'],
    queryFn: () => fetch('/api/evidence').then(r => r.json()),
    refetchInterval: 15000,
  });

  const items: EvidenceItem[] = evidenceData?.data || [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
      </div>
    );
  }

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-heading text-[#EAEAEA] tracking-widest">EVIDENCE GALLERY</h1>
          <p className="text-xs text-[#6B7280] font-mono mt-0.5 tracking-wider">{items.length} EVIDENCE ITEMS</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <HudCard title="Evidence" accent>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {items.length > 0 ? items.map((item) => {
                const displayUrl = showAnnotated && item.annotatedImageUrl ? item.annotatedImageUrl : item.imageUrl;
                return (
                <div
                  key={item.id}
                  className="hud-panel p-3 cursor-pointer transition-all hover:scale-[1.02]"
                  style={selected?.id === item.id ? {
                    borderColor: 'rgba(163,255,60,0.4)',
                    boxShadow: '0 0 15px rgba(163,255,60,0.06)',
                  } : {}}
                  onClick={() => { setSelected(item); setShowAnnotated(false); }}
                >
                  <span className="corner-bl" /><span className="corner-br" />
                  <div className="aspect-video rounded-lg flex items-center justify-center mb-2.5 target-lock overflow-hidden" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}>
                    {displayUrl ? (
                      <img src={displayUrl} alt="Evidence" className="w-full h-full object-contain rounded-lg" />
                    ) : (
                      <ImageIcon className="w-8 h-8" style={{ color: '#3A434F' }} />
                    )}
                  </div>
                  <p className="text-xs font-semibold" style={{ color: '#FF5D5D' }}>{item.violationType?.replace('_', ' ') || 'UNKNOWN'}</p>
                  <p className="text-xs text-[#6B7280] font-mono mt-0.5">{item.plateText || 'N/A'}</p>
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-xs font-mono" style={{ color: '#A3FF3C' }}>
                      {item.confidence ? `${(item.confidence * 100).toFixed(0)}%` : 'N/A'}
                    </span>
                    <span className="text-[10px] font-mono" style={{ color: '#3A434F' }}>
                      {item.timestamp ? new Date(item.timestamp).toLocaleDateString() : ''}
                    </span>
                  </div>
                </div>
                );
              }) : (
                <div className="col-span-full text-center py-10" style={{ color: '#6B7280' }}>
                  <ImageIcon className="w-10 h-10 mx-auto mb-3" style={{ color: '#3A434F' }} />
                  <p className="text-sm">No evidence found</p>
                  <p className="text-xs mt-1 font-mono" style={{ color: '#3A434F' }}>Upload and process images to generate evidence</p>
                </div>
              )}
            </div>
          </HudCard>
        </div>

        <div className="lg:col-span-1">
          <HudCard title={selected ? 'Evidence Details' : 'Evidence'} accent fullHeight>
            {selected ? (
              <div className="space-y-4">
                <div className="relative">
                  <div className="aspect-video rounded-lg flex items-center justify-center target-lock overflow-hidden" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}>
                    {selected.annotatedImageUrl ? (
                      <img
                        src={showAnnotated ? selected.annotatedImageUrl : selected.imageUrl}
                        alt="Evidence"
                        className="w-full h-full object-contain transition-all"
                        style={showAnnotated ? { transform: 'scale(1.15)', cursor: 'zoom-in' } : {}}
                      />
                    ) : selected.imageUrl ? (
                      <img src={selected.imageUrl} alt="Evidence" className="w-full h-full object-contain" />
                    ) : (
                      <ImageIcon className="w-12 h-12" style={{ color: '#3A434F' }} />
                    )}
                  </div>
                  {selected.annotatedImageUrl && (
                    <div className="absolute top-2 right-2">
                      <HudButton
                        size="sm"
                        className="text-xs"
                        onClick={() => setShowAnnotated(!showAnnotated)}
                      >
                        {showAnnotated ? 'Original' : 'Annotated'}
                      </HudButton>
                    </div>
                  )}
                </div>
                <div className="space-y-2">
                  {[
                    ['Type', selected.violationType?.replace('_', ' ') || 'UNKNOWN'],
                    ['Plate', selected.plateText || 'N/A'],
                    ['Confidence', selected.confidence ? `${(selected.confidence * 100).toFixed(0)}%` : 'N/A'],
                    ['Date', selected.timestamp ? new Date(selected.timestamp).toLocaleString() : ''],
                  ].map(([label, value]) => (
                    <div key={label} className="flex justify-between py-2 px-3" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}>
                      <span className="hud-label">{label}</span>
                      <span className="text-xs text-[#EAEAEA] font-medium">{value}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center py-10" style={{ color: '#6B7280' }}>
                <ImageIcon className="w-10 h-10 mx-auto mb-3" style={{ color: '#3A434F' }} />
                <p className="text-sm font-medium">Select evidence</p>
                <p className="text-xs mt-1 font-mono" style={{ color: '#3A434F' }}>Click on any item to view details</p>
              </div>
            )}
          </HudCard>
        </div>
      </div>
    </>
  );
};

export default Evidence;
