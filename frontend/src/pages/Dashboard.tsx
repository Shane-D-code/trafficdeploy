import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '../api/analytics';
import { WebSocketClient } from '../api/websocket';
import { StatsCards } from '../components/dashboard/StatsCards';
import { ViolationTimeline } from '../components/dashboard/ViolationTimeline';
import { LiveFeed } from '../components/dashboard/LiveFeed';
import { HudCard } from '../components/common/HudCard';
import { ViolationHeatmap } from '../components/maps/ViolationHeatmap';
import { RiskScoreCard } from '../components/dashboard/RiskScoreCard';
import { AISummary } from '../components/dashboard/AISummary';

const Dashboard: React.FC = () => {
  const [realtimeStats, setRealtimeStats] = useState<any>(null);
  const [recentViolations, setRecentViolations] = useState<any[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboardStats'],
    queryFn: () => analyticsApi.getStats().then(r => r.data.data),
    refetchInterval: 30000
  });

  useEffect(() => {
    const ws = new WebSocketClient();
    ws.connect();

    ws.onMessage((message) => {
      switch (message.type) {
        case 'NEW_VIOLATION':
          setRealtimeStats((prev: any) => ({
            ...prev,
            total: (prev?.total || 0) + 1,
            [message.data.type]: ((prev?.[message.data.type] || 0) + 1)
          }));
          setRecentViolations((prev: any[]) => [
            { ...message.data, timestamp: message.timestamp },
            ...prev
          ].slice(0, 20));
          break;
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

    return () => ws.disconnect();
  }, []);

  const displayStats = realtimeStats || stats;

  const todayStats = {
    total: displayStats?.total || 0,
    helmet: displayStats?.byType?.['NO HELMET'] || 0,
    seatbelt: displayStats?.byType?.['NO SEATBELT'] || 0,
    triple: displayStats?.byType?.['TRIPLE RIDING'] || 0,
    wrongSide: displayStats?.byType?.['WRONG SIDE'] || 0,
    redLight: displayStats?.byType?.['RED LIGHT'] || 0,
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <HudCard title="Live Camera Feed" accent scan>
            <LiveFeed realtime={true} recentViolations={recentViolations} />
          </HudCard>
        </div>
        <div className="lg:col-span-1 space-y-5">
          <HudCard title="Recent Timeline" accent>
            <ViolationTimeline violations={recentViolations} realtime={true} />
          </HudCard>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-1">
          <HudCard title="Violation Heatmap" accent>
            <ViolationHeatmap />
          </HudCard>
        </div>
        <div className="lg:col-span-1">
          <HudCard title="Repeat Offenders" accent>
            <RiskScoreCard />
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