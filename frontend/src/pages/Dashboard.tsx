import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { analyticsApi } from '../api/analytics';
import { detectionApi } from '../api/detection';
import { getWebSocketClient, WebSocketClient } from '../api/websocket';
import { useNotifications } from '../context/NotificationContext';
import { StatsCards } from '../components/dashboard/StatsCards';
import { ViolationTimeline } from '../components/dashboard/ViolationTimeline';
import { HudCard } from '../components/common/HudCard';
import { HudButton } from '../components/common/HudButton';
import { Heatmap } from '../components/maps/Heatmap';
import { ViolationHeatmap } from '../components/maps/ViolationHeatmap';
import { RiskScoreCard } from '../components/dashboard/RiskScoreCard';
import { AISummary } from '../components/dashboard/AISummary';
import { Upload, Image as ImageIcon, AlertCircle } from 'lucide-react';
import type { Violation } from '../types';

const Dashboard: React.FC = () => {
  const [realtimeStats, setRealtimeStats] = useState<any>(null);
  const [recentViolations, setRecentViolations] = useState<any[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const { addNotification } = useNotifications();

  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [violations, setViolations] = useState<Violation[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollingAttempts = useRef(0);
  const jobCompleted = useRef(false);

  const queryClient = useQueryClient();

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  useEffect(() => {
    const ws = new WebSocketClient();
    ws.connect();

    ws.onMessage((message) => {
      switch (message.type) {
        case 'NEW_VIOLATION': {
          const v = message.data;
          setRealtimeStats((prev: any) => {
            const base = prev || { total: 0, byType: {} };
            return {
              total: base.total + 1,
              byType: { ...base.byType, [v.type]: (base.byType[v.type] || 0) + 1 }
            };
          });
          setRecentViolations((prev: any[]) => [
            { ...v, timestamp: message.timestamp },
            ...prev
          ].slice(0, 20));
          addNotification('warning', `${v.type} detected${v.plateText ? ` - ${v.plateText}` : ''}`);
          queryClient.invalidateQueries({ queryKey: ['dashboardStats'] });
          break;
        }
        case 'JOB_PROGRESS':
          console.log(`Job ${message.jobId}: ${message.progress}%`);
          break;
        case 'CONNECTED':
          setIsConnected(true);
          break;
        case 'PONG':
          break;
        default:
          break;
      }
    });

    return () => { ws.disconnect(); stopPolling(); };
  }, [stopPolling]);

  const detectMutation = useMutation({
    mutationFn: async (f: File) => {
      setUploadError(null);
      setProgress(0);
      setViolations([]);
      pollingAttempts.current = 0;
      jobCompleted.current = false;

      const resp = await detectionApi.detectImage(f, 0.25, true, false);
      const { jobId } = resp.data;

      const ws2 = getWebSocketClient();
      ws2.connect();

      return new Promise<Violation[]>((resolve, reject) => {
        let done = false;
        const finish = (err?: string, violations?: Violation[]) => {
          if (done) return;
          done = true;
          jobCompleted.current = true;
          stopPolling();
          unsub();
          if (err) reject(new Error(err));
          else resolve(violations || []);
        };

        const unsub = ws2.onMessage((message: any) => {
          if (message.jobId !== jobId) return;
          if (message.type === 'JOB_PROGRESS') setProgress(message.progress);
          if (message.type === 'JOB_COMPLETE') {
            if (message.results?.error) { finish(message.results.error); return; }
            setViolations(message.results?.violations || []);
            setProgress(100);
            finish(undefined, message.results?.violations || []);
          }
          if (message.type === 'JOB_ERROR') finish(message.error || 'Job failed');
        });

        pollingRef.current = setInterval(async () => {
          if (done) return;
          pollingAttempts.current++;
          if (pollingAttempts.current > 300) { finish('Processing timeout'); return; }
          try {
            const status = await detectionApi.getStatus(jobId);
            if (status.data.status === 'complete') {
              if (status.data.result?.error) { finish(status.data.result.error); return; }
              setViolations(status.data.result?.violations || []);
              finish(undefined, status.data.result?.violations || []);
            } else if (status.data.status === 'error') {
              finish(status.data.message || 'Processing failed');
            } else {
              setProgress(status.data.progress || 0);
            }
          } catch {}
        }, 2000);
      });
    },
    onSuccess: (data) => {
      if (data) setViolations(data);
      addNotification('success', `Detection complete: ${data?.length || 0} violations found`);
    },
    onError: (e: any) => {
      setUploadError(e.message || 'Detection failed');
    },
  });

  const handleFile = useCallback((f: File) => {
    if (!f.type.startsWith('image/')) { setUploadError('Please select a valid image file'); return; }
    setFile(f);
    setViolations([]);
    setUploadError(null);
    setProgress(0);
    const reader = new FileReader();
    reader.onload = () => setPreview(reader.result as string);
    reader.readAsDataURL(f);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, [handleFile]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
  }, [handleFile]);

  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboardStats'],
    queryFn: () => analyticsApi.getStats().then(r => r.data.data),
    refetchInterval: 15000,
    staleTime: 5000,
  });

  const displayStats = useMemo(() => {
    if (!stats) return realtimeStats || null;
    if (!realtimeStats) return stats;
    const mergedByType = { ...(stats.byType || {}) };
    if (realtimeStats.byType) {
      for (const [type, count] of Object.entries(realtimeStats.byType)) {
        mergedByType[type] = Math.max(mergedByType[type] || 0, count as number);
      }
    }
    return {
      ...stats,
      total: Math.max(stats.total, realtimeStats.total || 0),
      byType: mergedByType,
    };
  }, [realtimeStats, stats]);

  const todayStats = {
    total: displayStats?.total || 0,
    helmet: displayStats?.byType?.['NO HELMET'] || 0,
    seatbelt: displayStats?.byType?.['NO SEATBELT'] || 0,
    triple: displayStats?.byType?.['TRIPLE RIDING'] || 0,
    wrongSide: displayStats?.byType?.['WRONG SIDE'] || 0,
    redLight: displayStats?.byType?.['RED LIGHT'] || 0,
    totalVehicles: displayStats?.totalVehicles ?? 0,
    helmetCompliance: displayStats?.compliance?.helmetCompliance ?? 0,
    seatbeltCompliance: displayStats?.compliance?.seatbeltCompliance ?? 0,
  };

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-heading text-[#EAEAEA] tracking-widest">DASHBOARD</h1>
          <p className="text-xs text-[#6B7280] font-mono mt-0.5 tracking-wider">AI TRAFFIC VIOLATION MONITORING SYSTEM</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className={`status-dot ${isConnected ? 'online' : ''}`} style={{ background: isConnected ? '#A3FF3C' : '#FF5D5D' }} />
            <span className="text-xs font-mono" style={{ color: isConnected ? '#A3FF3C' : '#FF5D5D' }}>
              {isConnected ? 'REAL-TIME' : 'OFFLINE'}
            </span>
          </div>
          <div className="live-indicator">{isConnected ? 'Live Monitoring' : 'Disconnected'}</div>
        </div>
      </div>

      {!isLoading && <StatsCards stats={todayStats} />}

      {!isLoading && stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="hud-panel p-4 text-center">
            <p className="text-2xl font-bold font-mono" style={{ color: '#60A5FA' }}>{todayStats.totalVehicles}</p>
            <p className="hud-label mt-1">Total Vehicles</p>
          </div>
          <div className="hud-panel p-4 text-center">
            <p className="text-2xl font-bold font-mono" style={{ color: '#7BFF7B' }}>{todayStats.helmetCompliance.toFixed(0)}%</p>
            <p className="hud-label mt-1">Helmet Compliance</p>
          </div>
          <div className="hud-panel p-4 text-center">
            <p className="text-2xl font-bold font-mono" style={{ color: '#FFD43B' }}>{todayStats.seatbeltCompliance.toFixed(0)}%</p>
            <p className="hud-label mt-1">Seatbelt Compliance</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <HudCard title="Quick Upload" accent scan>
            <div
              onDrop={handleDrop}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onClick={() => inputRef.current?.click()}
              className="p-6 text-center cursor-pointer transition-all rounded-lg"
              style={{
                border: `2px dashed ${dragOver ? '#A3FF3C' : '#3A434F'}`,
                background: dragOver ? 'rgba(163,255,60,0.03)' : 'transparent',
              }}
            >
              <input ref={inputRef} type="file" accept="image/jpeg,image/png" className="hidden" onChange={handleChange} />
              {file ? (
                <div className="space-y-3">
                  {preview && (
                    <img src={preview} alt="Preview" className="mx-auto max-h-48 rounded object-contain"
                      style={{ border: '1px solid rgba(58,67,79,0.3)' }} />
                  )}
                  <p className="text-sm font-mono" style={{ color: '#A3FF3C' }}>{file.name}</p>
                  <p className="text-xs text-[#6B7280] font-mono">Click or drop to change</p>
                </div>
              ) : (
                <div className="space-y-2">
                  <Upload className="w-10 h-10 mx-auto" style={{ color: '#3A434F' }} />
                  <p className="text-sm text-[#6B7280] font-mono">Drop image or click to upload</p>
                  <p className="text-xs" style={{ color: '#3A434F' }}>JPG, PNG · Max 50 MB</p>
                </div>
              )}
            </div>

            {file && (
              <div className="mt-4 space-y-3">
                {detectMutation.isPending && (
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs text-[#6B7280] font-mono">
                      <span>Detecting violations...</span>
                      <span>{progress}%</span>
                    </div>
                    <div className="w-full h-1.5" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.3)' }}>
                      <div className="h-full transition-all duration-300" style={{ width: `${progress}%`, background: '#A3FF3C' }} />
                    </div>
                  </div>
                )}

                <div className="flex gap-2">
                  <HudButton
                    className="flex-1"
                    variant="primary"
                    onClick={() => { if (file) detectMutation.mutate(file); }}
                    loading={detectMutation.isPending}
                  >
                    {detectMutation.isPending ? 'Processing...' : 'Detect Violations'}
                  </HudButton>
                  <HudButton
                    className="flex-1"
                    variant="danger"
                    onClick={() => { setFile(null); setPreview(null); setViolations([]); setUploadError(null); setProgress(0); }}
                  >
                    Clear
                  </HudButton>
                </div>

                {violations.length > 0 && (
                  <div className="grid grid-cols-3 gap-2 pt-2">
                    <div className="text-center p-2" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.3)' }}>
                      <p className="text-lg font-bold font-mono" style={{ color: '#FF5D5D' }}>{violations.length}</p>
                      <p className="hud-label">Total</p>
                    </div>
                    <div className="text-center p-2" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.3)' }}>
                      <p className="text-lg font-bold font-mono" style={{ color: '#A3FF3C' }}>{violations.filter(v => v.confidence > 0.8).length}</p>
                      <p className="hud-label">High Conf.</p>
                    </div>
                    <div className="text-center p-2" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.3)' }}>
                      <p className="text-lg font-bold font-mono" style={{ color: '#7BFF7B' }}>{violations.filter(v => v.plateText).length}</p>
                      <p className="hud-label">Plates</p>
                    </div>
                  </div>
                )}
              </div>
            )}

            {uploadError && (
              <div className="mt-4 p-3 flex items-start gap-2" style={{ background: 'rgba(255,93,93,0.05)', border: '1px solid rgba(255,93,93,0.2)' }}>
                <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" style={{ color: '#FF5D5D' }} />
                <p className="text-xs font-medium" style={{ color: '#FF5D5D' }}>{uploadError}</p>
              </div>
            )}
          </HudCard>
        </div>
        <div className="lg:col-span-1 space-y-5">
          <HudCard title="Recent Timeline" accent>
            <ViolationTimeline violations={recentViolations} realtime={true} />
          </HudCard>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <HudCard title="📍 Violation Heatmap" accent>
            <Heatmap />
          </HudCard>
        </div>
        <div className="lg:col-span-1">
          <HudCard title="Repeat Offenders" accent>
            <RiskScoreCard />
          </HudCard>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-1">
          <HudCard title="Violation Dots" accent>
            <ViolationHeatmap />
          </HudCard>
        </div>
        <div className="lg:col-span-1">
          <HudCard title="AI Summary" accent>
            <AISummary />
          </HudCard>
        </div>
      </div>

      <HudCard title="Recent Violations" accent>
        {recentViolations.length > 0 ? (
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {recentViolations.map((violation: any, index: number) => (
              <div key={index} className="flex items-center justify-between py-3 px-4 mb-2 last:mb-0 transition-colors"
                style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}>
                <div className="flex items-center gap-4">
                  <span className="text-xs text-[#6B7280] font-mono w-16">
                    {violation.timestamp ? new Date(violation.timestamp).toLocaleTimeString() : ''}
                  </span>
                  <span className="text-sm font-medium" style={{ color: '#FF5D5D' }}>{violation.type || violation.violation_type}</span>
                  <span className="text-xs text-[#6B7280] font-mono">{violation.plateText || violation.plate_text || 'NO PLATE'}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm font-mono text-[#A3FF3C]">
                    {(violation.confidence * 100).toFixed(0)}%
                  </span>
                  <span className="hud-tag hud-tag-green">LIVE</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-[#6B7280]">
            <p className="text-4xl mb-2">📡</p>
            <p className="font-mono text-sm">Waiting for violations...</p>
            <p className="text-xs mt-1">{isConnected ? 'Real-time feed active' : 'Connect to WebSocket for live updates'}</p>
          </div>
        )}
      </HudCard>
    </>
  );
};

export default Dashboard;