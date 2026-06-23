import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { HudCard } from '../components/common/HudCard';
import { HudSpinner } from '../components/common/HudSpinner';
import { MapPin, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';
import type { DangerousJunction, RepeatOffender } from '../types';

const insightsApi = {
  getDangerousJunctions: (params?: Record<string, string>) =>
    fetch(`/api/insights/dangerous-junctions${params ? '?' + new URLSearchParams(params) : ''}`).then(r => r.json()),
  getRepeatOffenders: (params?: Record<string, string>) =>
    fetch(`/api/insights/repeat-offenders${params ? '?' + new URLSearchParams(params) : ''}`).then(r => r.json()),
};

const HeatmapCanvas: React.FC<{ data: DangerousJunction[] }> = ({ data }) => {
  const canvasRef = React.useRef<HTMLCanvasElement>(null);

  React.useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !data.length) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;

    ctx.fillStyle = '#0B0F13';
    ctx.fillRect(0, 0, w, h);

    const lats = data.map(d => d.lat);
    const lngs = data.map(d => d.lng);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLng = Math.min(...lngs);
    const maxLng = Math.max(...lngs);
    const padLat = (maxLat - minLat) * 0.1 || 0.01;
    const padLng = (maxLng - minLng) * 0.1 || 0.01;

    const toX = (lng: number) => ((lng - (minLng - padLng)) / ((maxLng - minLng) + 2 * padLng)) * w;
    const toY = (lat: number) => ((1 - (lat - (minLat - padLat)) / ((maxLat - minLat) + 2 * padLat))) * h;

    const points = data.map(d => ({ x: toX(d.lng), y: toY(d.lat), w: d.severityScore }));

    const grad = ctx.createRadialGradient(0, 0, 0, 0, 0, 50);
    grad.addColorStop(0, 'rgba(163,255,60,0.6)');
    grad.addColorStop(0.4, 'rgba(255,212,59,0.3)');
    grad.addColorStop(1, 'rgba(255,93,93,0)');

    for (const p of points) {
      const radius = Math.max(20, Math.min(60, p.w * 2));
      const g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, radius);
      g.addColorStop(0, 'rgba(163,255,60,0.5)');
      g.addColorStop(0.3, 'rgba(255,212,59,0.25)');
      g.addColorStop(1, 'rgba(255,93,93,0)');
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
      ctx.fill();
    }

    for (const p of points) {
      ctx.fillStyle = '#A3FF3C';
      ctx.beginPath();
      ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#0B0F13';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    ctx.strokeStyle = 'rgba(58,67,79,0.3)';
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= 5; i++) {
      const y = (h / 5) * i;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }
    for (let i = 0; i <= 8; i++) {
      const x = (w / 8) * i;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }

    data.forEach(d => {
      const x = toX(d.lng);
      const y = toY(d.lat);
      ctx.fillStyle = 'rgba(234,234,234,0.8)';
      ctx.font = '9px IBM Plex Mono';
      ctx.textAlign = 'center';
      ctx.fillText(d.location, x, y - 12);
    });
  }, [data]);

  return (
    <div className="relative rounded-lg overflow-hidden" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}>
      <canvas ref={canvasRef} width={800} height={400} className="w-full h-auto" style={{ minHeight: '300px' }} />
      <div className="absolute bottom-3 left-3 flex items-center gap-3 text-[10px] font-mono" style={{ color: '#6B7280' }}>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full" style={{ background: '#A3FF3C' }} /> Junction</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded" style={{ background: 'rgba(163,255,60,0.4)' }} /> Severity</span>
      </div>
    </div>
  );
};

const riskBadge = (level: string) => {
  const colors: Record<string, string> = {
    high: '#FF5D5D',
    medium: '#FFD43B',
    low: '#A3FF3C',
  };
  return (
    <span className="text-xs font-mono px-2 py-0.5 rounded" style={{
      background: `${colors[level]}15`,
      color: colors[level],
      border: `1px solid ${colors[level]}40`,
    }}>
      {level.toUpperCase()}
    </span>
  );
};

const Insights: React.FC = () => {
  const [timeframe, setTimeframe] = useState('all');
  const [expandedPlate, setExpandedPlate] = useState<string | null>(null);

  const { data: junctionsData, isLoading: junctionsLoading } = useQuery({
    queryKey: ['dangerous-junctions', timeframe],
    queryFn: () => insightsApi.getDangerousJunctions(timeframe !== 'all' ? { timeframe } : undefined),
    refetchInterval: 60000,
  });

  const { data: offendersData, isLoading: offendersLoading } = useQuery({
    queryKey: ['repeat-offenders'],
    queryFn: () => insightsApi.getRepeatOffenders(),
    refetchInterval: 60000,
  });

  const junctions: DangerousJunction[] = junctionsData?.data || [];
  const offenders: RepeatOffender[] = offendersData?.data || [];

  const timeframes = [
    { label: 'All Time', value: 'all' },
    { label: 'Today', value: 'today' },
    { label: 'This Week', value: 'week' },
    { label: 'This Month', value: 'month' },
  ];

  return (
    <div className="space-y-5">
      <HudCard title="Dangerous Junctions" accent>
        <div className="flex gap-2 mb-4">
          {timeframes.map(tf => (
            <button
              key={tf.value}
              onClick={() => setTimeframe(tf.value)}
              className={`px-3 py-1 text-xs font-mono rounded transition-all ${
                timeframe === tf.value ? 'bg-blue-600 text-white' : 'text-[#6B7280] hover:text-white'
              }`}
              style={{ background: timeframe === tf.value ? undefined : '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}
            >
              {tf.label}
            </button>
          ))}
        </div>

        {junctionsLoading ? <HudSpinner size="lg" text="Loading junctions" /> : (
          <div className="space-y-4">
            <HeatmapCanvas data={junctions} />

            <div className="overflow-x-auto">
              <table className="hud-table w-full">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Location</th>
                    <th>Total</th>
                    <th>Severity Score</th>
                    <th>Top Violation</th>
                  </tr>
                </thead>
                <tbody>
                  {junctions.length === 0 ? (
                    <tr><td colSpan={5} className="py-8 text-center text-sm" style={{ color: '#6B7280' }}>No data</td></tr>
                  ) : (
                    junctions.map((j, i) => {
                      const topType = Object.entries(j.byType).sort((a, b) => b[1] - a[1])[0];
                      return (
                        <tr key={j.location}>
                          <td className="text-sm font-mono" style={{ color: '#6B7280' }}>{i + 1}</td>
                          <td className="text-sm font-medium" style={{ color: '#EAEAEA' }}>
                            <MapPin className="w-3 h-3 inline mr-1" style={{ color: '#FF5D5D' }} />
                            {j.location}
                          </td>
                          <td className="text-sm font-mono" style={{ color: '#A3FF3C' }}>{j.total}</td>
                          <td className="text-sm font-mono">
                            <span className="px-2 py-0.5 rounded text-xs" style={{
                              background: j.severityScore > 100 ? 'rgba(255,93,93,0.15)' : j.severityScore > 50 ? 'rgba(255,212,59,0.15)' : 'rgba(163,255,60,0.15)',
                              color: j.severityScore > 100 ? '#FF5D5D' : j.severityScore > 50 ? '#FFD43B' : '#A3FF3C',
                              border: `1px solid ${j.severityScore > 100 ? 'rgba(255,93,93,0.3)' : j.severityScore > 50 ? 'rgba(255,212,59,0.3)' : 'rgba(163,255,60,0.3)'}`,
                            }}>
                              {j.severityScore}
                            </span>
                          </td>
                          <td className="text-sm font-mono" style={{ color: '#6B7280' }}>
                            {topType ? `${topType[0].replace('_', ' ')} (${topType[1]})` : '-'}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </HudCard>

      <HudCard title="Repeat Offenders" accent>
        {offendersLoading ? <HudSpinner size="lg" text="Loading offenders" /> : (
          <div className="overflow-x-auto">
            <table className="hud-table w-full">
              <thead>
                <tr>
                  <th>Plate</th>
                  <th>Violations</th>
                  <th>Types</th>
                  <th>Risk</th>
                  <th>Last Seen</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {offenders.length === 0 ? (
                  <tr><td colSpan={6} className="py-8 text-center text-sm" style={{ color: '#6B7280' }}>No repeat offenders</td></tr>
                ) : (
                  offenders.map((o) => {
                    const isExpanded = expandedPlate === o.plate;
                    const sortedHistory = (o.violationHistory || []).sort(
                      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
                    );
                    return (
                      <React.Fragment key={o.plate}>
                        <tr className="transition-colors" style={{ cursor: 'pointer' }}
                          onClick={() => setExpandedPlate(isExpanded ? null : o.plate)}>
                          <td className="text-sm font-mono" style={{ color: '#EAEAEA' }}>{o.plate}</td>
                          <td className="text-sm font-mono" style={{ color: '#FF5D5D' }}>{o.count}</td>
                          <td>
                            <div className="flex flex-wrap gap-1">
                              {o.types.map(t => (
                                <span key={t} className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                                  style={{ background: 'rgba(255,93,93,0.1)', color: '#FF5D5D', border: '1px solid rgba(255,93,93,0.2)' }}>
                                  {t.replace('_', ' ')}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td>{riskBadge(o.riskLevel)}</td>
                          <td className="text-xs font-mono" style={{ color: '#6B7280' }}>
                            {o.lastViolation ? new Date(o.lastViolation).toLocaleDateString() : '-'}
                          </td>
                          <td>
                            {isExpanded ? <ChevronUp className="w-4 h-4" style={{ color: '#6B7280' }} />
                              : <ChevronDown className="w-4 h-4" style={{ color: '#6B7280' }} />}
                          </td>
                        </tr>
                        {isExpanded && sortedHistory.length > 0 && (
                          <tr>
                            <td colSpan={6} className="p-0">
                              <div className="px-6 pb-3" style={{ background: 'rgba(11,15,19,0.5)' }}>
                                <table className="w-full">
                                  <thead>
                                    <tr className="text-[10px] font-mono" style={{ color: '#3A434F' }}>
                                      <th className="text-left py-1">Date</th>
                                      <th className="text-left py-1">Type</th>
                                      <th className="text-left py-1">Confidence</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {sortedHistory.slice(0, 10).map((h, idx) => (
                                      <tr key={idx} className="text-xs font-mono" style={{ color: '#6B7280' }}>
                                        <td className="py-1">{new Date(h.timestamp).toLocaleString()}</td>
                                        <td className="py-1">{h.type.replace('_', ' ')}</td>
                                        <td className="py-1" style={{ color: '#A3FF3C' }}>{(h.confidence * 100).toFixed(0)}%</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        )}
      </HudCard>
    </div>
  );
};

export default Insights;