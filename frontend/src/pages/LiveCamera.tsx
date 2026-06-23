import React, { useState, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { HudCard } from '../components/common/HudCard';
import { HudButton } from '../components/common/HudButton';
import { Camera, WifiOff, AlertTriangle } from 'lucide-react';
import { getWebSocketClient } from '../api/websocket';
import type { Camera as CameraType } from '../types';

const LiveCamera: React.FC = () => {
  const [selectedCamera, setSelectedCamera] = useState<CameraType | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [violations, setViolations] = useState<any[]>([]);
  const [lastFrame, setLastFrame] = useState<string | null>(null);

  const { data: camerasData, isLoading } = useQuery({
    queryKey: ['cameras'],
    queryFn: () => fetch('/api/live/cameras').then(r => r.json()),
    refetchInterval: 30000,
  });

  const cameras: CameraType[] = camerasData?.data || [];

  useEffect(() => {
    if (!selectedCamera || !isStreaming) return;
    const ws = getWebSocketClient();
    ws.connect();
    const unsub = ws.onMessage((msg: any) => {
      if (msg.type === 'NEW_VIOLATION' && msg.data) {
        setViolations(prev => [...prev, { ...msg.data, receivedAt: new Date().toISOString() }].slice(-50));
      }
    });
    fetch(`/api/live/camera/${selectedCamera.id}/start`, { method: 'POST' });
    return () => {
      unsub();
      ws.disconnect();
      fetch(`/api/live/camera/${selectedCamera.id}/stop`, { method: 'POST' });
    };
  }, [selectedCamera, isStreaming]);

  const startStream = useCallback(() => setIsStreaming(true), []);
  const stopStream = useCallback(() => { setIsStreaming(false); setViolations([]); }, []);

  const statusColor = (s: string) =>
    s === 'online' ? '#A3FF3C' : s === 'warning' ? '#FFD43B' : '#FF5D5D';

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
          <h1 className="text-lg font-heading text-[#EAEAEA] tracking-widest">LIVE CAMERA MONITORING</h1>
          <p className="text-xs text-[#6B7280] font-mono mt-0.5 tracking-wider">REAL-TIME TRAFFIC SURVEILLANCE</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}>
          <span className={`w-2 h-2 rounded-full ${isStreaming ? 'bg-red-500 animate-pulse' : 'bg-gray-500'}`} />
          <span className="text-xs font-mono" style={{ color: isStreaming ? '#FF5D5D' : '#6B7280' }}>
            {isStreaming ? 'LIVE' : 'STOPPED'}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <HudCard title="Camera Grid" accent>
            <div className="grid grid-cols-2 gap-4">
              {cameras.map((cam: CameraType) => (
                <div
                  key={cam.id}
                  className="hud-panel p-4 cursor-pointer transition-all hover:scale-[1.02]"
                  style={selectedCamera?.id === cam.id ? {
                    borderColor: 'rgba(163,255,60,0.4)',
                    boxShadow: '0 0 15px rgba(163,255,60,0.06)',
                  } : {}}
                  onClick={() => { setSelectedCamera(cam); setIsStreaming(false); setViolations([]); }}
                >
                  <span className="corner-bl" /><span className="corner-br" />
                  <div className="aspect-video rounded-lg flex items-center justify-center relative scan-overlay" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}>
                    {cam.status === 'online' ? (
                      <>
                        <div className="absolute top-2 left-2 flex items-center gap-1.5 px-1.5 py-0.5 z-10" style={{ background: 'rgba(0,0,0,0.6)' }}>
                          <span className="status-dot online" />
                          <span className="text-[10px] text-[#A3FF3C] font-mono font-medium tracking-wider">LIVE</span>
                        </div>
                        <Camera className="w-10 h-10" style={{ color: '#3A434F' }} strokeWidth={1} />
                        <div className="absolute bottom-2 left-2 text-[10px] text-[#3A434F] font-mono z-10">30 FPS</div>
                      </>
                    ) : cam.status === 'warning' ? (
                      <>
                        <div className="absolute top-2 left-2 flex items-center gap-1.5 px-1.5 py-0.5 z-10" style={{ background: 'rgba(0,0,0,0.6)' }}>
                          <span className="status-dot warning" />
                          <span className="text-[10px] text-[#FFD43B] font-mono font-medium">WARNING</span>
                        </div>
                        <AlertTriangle className="w-10 h-10" style={{ color: 'rgba(255,212,59,0.5)' }} strokeWidth={1} />
                      </>
                    ) : (
                      <>
                        <div className="absolute top-2 left-2 flex items-center gap-1.5 px-1.5 py-0.5 z-10" style={{ background: 'rgba(0,0,0,0.6)' }}>
                          <span className="status-dot offline" />
                          <span className="text-[10px] text-[#FF5D5D] font-mono font-medium">OFFLINE</span>
                        </div>
                        <WifiOff className="w-10 h-10" style={{ color: '#3A434F' }} strokeWidth={1} />
                      </>
                    )}
                    <div className="absolute bottom-2 right-2 text-[10px] text-[#3A434F] font-mono z-10">{cam.location}</div>
                  </div>
                  <div className="mt-2.5 flex items-center justify-between">
                    <span className="text-sm font-medium text-[#EAEAEA]">{cam.name}</span>
                    <span className="text-[10px] font-mono font-medium tracking-wider" style={{ color: statusColor(cam.status) }}>
                      {cam.status.toUpperCase()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </HudCard>
        </div>

        <div className="lg:col-span-1 space-y-4">
          <HudCard title={selectedCamera ? `CAM-${String(selectedCamera.id).padStart(3, '0')}` : 'Camera Details'} accent fullHeight>
            {selectedCamera ? (
              <div className="space-y-4">
                <div className="aspect-video rounded-lg flex items-center justify-center scan-overlay relative" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}>
                  {isStreaming ? (
                    lastFrame ? (
                      <img src={lastFrame} alt="Live feed" className="w-full h-full object-contain" />
                    ) : (
                      <div className="text-center">
                        <Camera className="w-12 h-12 mx-auto" style={{ color: '#3A434F' }} strokeWidth={1} />
                        <p className="text-sm text-[#6B7280] mt-2 font-mono">WAITING FOR FEED</p>
                      </div>
                    )
                  ) : selectedCamera.status === 'online' ? (
                    <div className="text-center">
                      <Camera className="w-12 h-12 mx-auto" style={{ color: '#3A434F' }} strokeWidth={1} />
                      <p className="text-sm text-[#6B7280] mt-2 font-mono">CLICK START</p>
                    </div>
                  ) : (
                    <div className="text-center">
                      <WifiOff className="w-12 h-12 mx-auto" style={{ color: '#3A434F' }} strokeWidth={1} />
                      <p className="text-sm text-[#6B7280] mt-2 font-mono">NO SIGNAL</p>
                    </div>
                  )}
                  {isStreaming && (
                    <div className="absolute top-2 left-2 flex items-center gap-1.5 px-1.5 py-0.5 z-10" style={{ background: 'rgba(0,0,0,0.6)' }}>
                      <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
                      <span className="text-[10px] text-red-400 font-mono">LIVE</span>
                    </div>
                  )}
                </div>
                <div className="space-y-2">
                  {[
                    ['Location', selectedCamera.location],
                    ['Status', selectedCamera.status.toUpperCase()],
                    ['Resolution', '1920x1080'],
                    ['Bitrate', '4.5 Mbps'],
                    ['Codec', 'H.264'],
                  ].map(([label, value]) => (
                    <div key={label} className="flex justify-between py-1.5 px-2" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}>
                      <span className="hud-label">{label}</span>
                      <span className="text-xs font-mono font-medium" style={{ color: label === 'Status' ? statusColor(selectedCamera.status) : '#EAEAEA' }}>{value}</span>
                    </div>
                  ))}
                </div>
                <div className="flex gap-2 pt-2">
                  {!isStreaming ? (
                    <HudButton className="flex-1 text-xs" size="sm" onClick={startStream}>Start Stream</HudButton>
                  ) : (
                    <HudButton className="flex-1 text-xs" variant="danger" size="sm" onClick={stopStream}>Stop Stream</HudButton>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-center py-10" style={{ color: '#6B7280' }}>
                <Camera className="w-10 h-10 mx-auto mb-3" style={{ color: '#3A434F' }} strokeWidth={1} />
                <p className="text-sm font-medium">Select a camera</p>
                <p className="text-xs mt-1 font-mono" style={{ color: '#3A434F' }}>Click on any camera to view details</p>
              </div>
            )}
          </HudCard>

          {isStreaming && (
            <HudCard title="Live Violations" accent>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {violations.length > 0 ? (
                  violations.slice().reverse().map((v, i) => (
                    <div key={i} className="p-2" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold" style={{ color: '#FF5D5D' }}>{v.type}</span>
                        <span className="text-[10px] font-mono" style={{ color: '#A3FF3C' }}>
                          {v.confidence ? `${(v.confidence * 100).toFixed(0)}%` : ''}
                        </span>
                      </div>
                      <p className="text-[10px] font-mono" style={{ color: '#6B7280' }}>
                        {v.plateText || ''} {v.receivedAt ? new Date(v.receivedAt).toLocaleTimeString() : ''}
                      </p>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-6" style={{ color: '#6B7280' }}>
                    <p className="text-xs font-mono">No violations detected</p>
                    <p className="text-[10px] mt-1 font-mono" style={{ color: '#3A434F' }}>Waiting for feed...</p>
                  </div>
                )}
              </div>
            </HudCard>
          )}
        </div>
      </div>
    </>
  );
};

export default LiveCamera;
