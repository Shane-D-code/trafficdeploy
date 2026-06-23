import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, Cell } from 'recharts';
import { analyticsApi } from '../api/analytics';
import { HudCard } from '../components/common/HudCard';
import { HudSpinner } from '../components/common/HudSpinner';
import { NEON_COLORS } from '../utils/constants';
import type { MetricsData } from '../types';

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload?.length) {
    return (
      <div style={{ background: '#1B232C', border: '1px solid #3A434F', padding: '8px 12px' }}>
        <p className="text-xs font-medium text-[#EAEAEA] mb-1">{label}</p>
        {payload.map((p: any, i: number) => (
          <p key={i} className="text-sm font-mono" style={{ color: p.color }}>{p.name}: {typeof p.value === 'number' ? p.value.toFixed(1) : p.value}</p>
        ))}
      </div>
    );
  }
  return null;
};

const Gauge: React.FC<{ value: number; label: string; max?: number; color?: string }> = ({ value, label, max = 100, color = '#A3FF3C' }) => {
  const pct = Math.min(value / max, 1);
  const degrees = pct * 180;
  return (
    <div className="flex flex-col items-center">
      <svg width="140" height="100" viewBox="0 0 140 100">
        <path d="M 10 90 A 60 60 0 0 1 130 90" fill="none" stroke="#3A434F" strokeWidth="12" strokeLinecap="round" />
        <path d="M 10 90 A 60 60 0 0 1 130 90" fill="none" stroke={color} strokeWidth="12" strokeLinecap="round"
          strokeDasharray={`${(degrees / 180) * 188.5} 188.5`} />
        <text x="70" y="70" textAnchor="middle" fill={color} fontSize="22" fontFamily="IBM Plex Mono" fontWeight="bold">
          {value.toFixed(1)}%
        </text>
      </svg>
      <span className="text-xs font-mono mt-1" style={{ color: '#6B7280' }}>{label}</span>
    </div>
  );
};

const Metrics: React.FC = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['analytics-metrics'],
    queryFn: () => analyticsApi.getMetrics(),
    refetchInterval: 30000,
  });

  if (isLoading) return <HudSpinner size="lg" text="Loading metrics" />;

  const m = data?.data?.data as MetricsData | undefined;
  if (!m) return <p className="text-center" style={{ color: '#6B7280', padding: '4rem 0' }}>No metrics available</p>;

  const tpFpFnData = [
    { name: 'True Positives', value: m.truePositives, fill: '#A3FF3C' },
    { name: 'False Positives', value: m.falsePositives, fill: '#FFD43B' },
    { name: 'False Negatives', value: m.falseNegatives, fill: '#FF5D5D' },
  ];

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="hud-panel p-4 text-center">
          <p className="text-2xl font-bold font-mono" style={{ color: '#A3FF3C' }}>{m.totalSamples}</p>
          <p className="hud-label mt-1">Total Samples</p>
        </div>
        <div className="hud-panel p-4 text-center">
          <p className="text-2xl font-bold font-mono" style={{ color: '#7BFF7B' }}>{m.fps.toFixed(1)}</p>
          <p className="hud-label mt-1">FPS</p>
        </div>
        <div className="hud-panel p-4 text-center">
          <p className="text-2xl font-bold font-mono" style={{ color: '#FFD43B' }}>{m.p95InferenceTime.toFixed(0)}ms</p>
          <p className="hud-label mt-1">p95 Latency</p>
        </div>
        <div className="hud-panel p-4 text-center">
          <p className="text-2xl font-bold font-mono" style={{ color: '#FF5D5D' }}>{m.p99InferenceTime.toFixed(0)}ms</p>
          <p className="hud-label mt-1">p99 Latency</p>
        </div>
        <div className="hud-panel p-4 text-center">
          <p className="text-2xl font-bold font-mono" style={{ color: '#60A5FA' }}>{(m.avgConfidence * 100).toFixed(0)}%</p>
          <p className="hud-label mt-1">Avg Confidence</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <HudCard title="mAP (Mean Average Precision)" accent>
          <div className="flex justify-center py-4">
            <Gauge value={m.mAP} label="Overall mAP" color="#A3FF3C" />
          </div>
        </HudCard>

        <HudCard title="Accuracy" accent>
          <div className="flex justify-center py-4">
            <Gauge value={m.accuracy} label="Detection Accuracy" color="#7BFF7B" />
          </div>
        </HudCard>

        <HudCard title="Precision" accent>
          <div className="flex justify-center py-4">
            <Gauge value={m.precision} label="Detection Precision" color="#60A5FA" />
          </div>
        </HudCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <HudCard title="TP / FP / FN" accent>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={tpFpFnData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(58,67,79,0.3)" />
              <XAxis dataKey="name" tick={{ fill: '#6B7280', fontSize: 11, fontFamily: 'IBM Plex Mono' }} />
              <YAxis tick={{ fill: '#6B7280', fontSize: 11, fontFamily: 'IBM Plex Mono' }} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="value">
                {tpFpFnData.map((e, i) => <Cell key={i} fill={e.fill} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </HudCard>

        <HudCard title="mAP per Class" accent>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={Object.entries(m.mapPerClass).map(([type, val]) => ({ type, value: val }))} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(58,67,79,0.3)" />
              <XAxis type="number" domain={[0, 100]} tick={{ fill: '#6B7280', fontSize: 11, fontFamily: 'IBM Plex Mono' }} />
              <YAxis dataKey="type" type="category" tick={{ fill: '#6B7280', fontSize: 10, fontFamily: 'IBM Plex Mono' }} width={100} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="value" fill="#A3FF3C" />
            </BarChart>
          </ResponsiveContainer>
        </HudCard>
      </div>

      {m.inferenceTimeSeries.length > 0 && (
        <HudCard title="Inference Time (Last Hour)" accent>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={m.inferenceTimeSeries}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(58,67,79,0.3)" />
              <XAxis dataKey="time" tick={{ fill: '#6B7280', fontSize: 10, fontFamily: 'IBM Plex Mono' }}
                tickFormatter={(v) => { try { return new Date(v).toLocaleTimeString(); } catch { return v; }}} />
              <YAxis tick={{ fill: '#6B7280', fontSize: 11, fontFamily: 'IBM Plex Mono' }} />
              <Tooltip content={<CustomTooltip />} />
              <Line type="monotone" dataKey="p95" stroke="#FFD43B" strokeWidth={2} dot={false} name="p95" />
              <Line type="monotone" dataKey="p99" stroke="#FF5D5D" strokeWidth={2} dot={false} name="p99" />
            </LineChart>
          </ResponsiveContainer>
        </HudCard>
      )}

      {m.confidenceDistribution.length > 0 && (
        <HudCard title="Confidence Distribution" accent>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={m.confidenceDistribution}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(58,67,79,0.3)" />
              <XAxis dataKey="bin" tick={{ fill: '#6B7280', fontSize: 9, fontFamily: 'IBM Plex Mono' }} angle={-45} textAnchor="end" height={60} />
              <YAxis tick={{ fill: '#6B7280', fontSize: 11, fontFamily: 'IBM Plex Mono' }} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="count" fill="#60A5FA" />
            </BarChart>
          </ResponsiveContainer>
        </HudCard>
      )}
    </div>
  );
};

export default Metrics;