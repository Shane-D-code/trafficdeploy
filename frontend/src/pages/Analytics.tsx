import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line, Legend } from 'recharts';
import { analyticsApi } from '../api/analytics';
import { HudCard } from '../components/common/HudCard';
import { HudSpinner } from '../components/common/HudSpinner';
import { NEON_COLORS } from '../utils/constants';
import Metrics from './Metrics';
import Insights from './Insights';

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload?.length) {
    return (
      <div style={{ background: '#1B232C', border: '1px solid #3A434F', padding: '8px 12px' }}>
        <p className="text-xs font-medium text-[#EAEAEA] mb-1">{label}</p>
        {payload.map((p: any, i: number) => (
          <p key={i} className="text-sm font-mono" style={{ color: p.color }}>{p.name}: {p.value}</p>
        ))}
      </div>
    );
  }
  return null;
};

const tabs = [
  { key: 'summary', label: 'Summary' },
  { key: 'metrics', label: 'Metrics' },
  { key: 'insights', label: 'Insights' },
];

const Analytics: React.FC = () => {
  const [activeTab, setActiveTab] = useState('summary');

  const { data, isLoading } = useQuery({
    queryKey: ['analytics'],
    queryFn: () => analyticsApi.getStats(),
    refetchInterval: 30000,
  });

  if (activeTab === 'metrics') return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-heading text-[#EAEAEA] tracking-widest">ANALYTICS DASHBOARD</h1>
          <p className="text-xs text-[#6B7280] font-mono mt-0.5 tracking-wider">PERFORMANCE METRICS AND EVALUATION</p>
        </div>
        <div className="flex gap-1">
          {tabs.map(tab => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)}
              className={`px-3 py-1 text-xs font-mono rounded transition-all ${activeTab === tab.key ? 'bg-blue-600 text-white' : 'text-[#6B7280] hover:text-white'}`}
              style={{ background: activeTab === tab.key ? undefined : '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}>
              {tab.label}
            </button>
          ))}
        </div>
      </div>
      <Metrics />
    </>
  );

  if (activeTab === 'insights') return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-heading text-[#EAEAEA] tracking-widest">ANALYTICS DASHBOARD</h1>
          <p className="text-xs text-[#6B7280] font-mono mt-0.5 tracking-wider">DANGEROUS JUNCTIONS AND REPEAT OFFENDERS</p>
        </div>
        <div className="flex gap-1">
          {tabs.map(tab => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)}
              className={`px-3 py-1 text-xs font-mono rounded transition-all ${activeTab === tab.key ? 'bg-blue-600 text-white' : 'text-[#6B7280] hover:text-white'}`}
              style={{ background: activeTab === tab.key ? undefined : '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}>
              {tab.label}
            </button>
          ))}
        </div>
      </div>
      <Insights />
    </>
  );

  if (isLoading) return <HudSpinner size="lg" text="Loading analytics" />;

  const stats = data?.data?.data;
  if (!stats) return <p className="text-center" style={{ color: '#6B7280', padding: '4rem 0' }}>No data available</p>;

  const byTypeData = Object.entries(stats.byType).map(([type, count]) => ({ type: type.replace(/_/g, ' '), count }));
  const byDateData = Object.entries(stats.byDate).map(([date, count]) => ({ date, count })).sort((a, b) => a.date.localeCompare(b.date));

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-heading text-[#EAEAEA] tracking-widest">ANALYTICS DASHBOARD</h1>
          <p className="text-xs text-[#6B7280] font-mono mt-0.5 tracking-wider">COMPLIANCE METRICS AND VIOLATION TRENDS</p>
        </div>
        <div className="flex gap-1">
          {tabs.map(tab => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)}
              className={`px-3 py-1 text-xs font-mono rounded transition-all ${activeTab === tab.key ? 'bg-blue-600 text-white' : 'text-[#6B7280] hover:text-white'}`}
              style={{ background: activeTab === tab.key ? undefined : '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}>
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Violations', value: stats.total, color: '#FF5D5D' },
          { label: 'Violation Types', value: Object.keys(stats.byType).length, color: '#A3FF3C' },
          { label: 'Total Vehicles', value: stats.totalVehicles, color: '#7BFF7B' },
          { label: 'Plates Detected', value: Object.values(stats.byType).reduce((a: number, b: any) => a + b, 0), color: '#A3FF3C' },
        ].map((card) => (
          <div key={card.label} className="hud-panel p-4 text-center">
            <span className="corner-bl" /><span className="corner-br" />
            <p className="text-2xl font-bold font-mono" style={{ color: card.color }}>{card.value}</p>
            <p className="hud-label mt-1">{card.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <HudCard title="Violations by Type" accent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={byTypeData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(58,67,79,0.3)" />
              <XAxis dataKey="type" tick={{ fill: '#6B7280', fontSize: 11, fontFamily: 'IBM Plex Mono' }} />
              <YAxis tick={{ fill: '#6B7280', fontSize: 11, fontFamily: 'IBM Plex Mono' }} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="count" fill="#A3FF3C" />
            </BarChart>
          </ResponsiveContainer>
        </HudCard>

        <HudCard title="Distribution" accent>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie data={byTypeData} dataKey="count" nameKey="type" cx="50%" cy="50%" outerRadius={100} label={({ type }) => type}>
                {byTypeData.map((_, i) => <Cell key={i} fill={NEON_COLORS[i % NEON_COLORS.length]} />)}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </HudCard>
      </div>

      {byDateData.length > 0 && (
        <HudCard title="Daily Trend" accent>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={byDateData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(58,67,79,0.3)" />
              <XAxis dataKey="date" tick={{ fill: '#6B7280', fontSize: 11, fontFamily: 'IBM Plex Mono' }} />
              <YAxis tick={{ fill: '#6B7280', fontSize: 11, fontFamily: 'IBM Plex Mono' }} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: '12px', color: '#6B7280', fontFamily: 'IBM Plex Mono' }} />
              <Line type="monotone" dataKey="count" stroke="#A3FF3C" strokeWidth={2} dot={{ r: 3, fill: '#A3FF3C' }} />
            </LineChart>
          </ResponsiveContainer>
        </HudCard>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <HudCard title="Helmet Compliance" accent>
          <div className="flex items-center gap-4">
            <div className="flex-1" style={{ background: '#3A434F', height: '12px' }}>
              <div className="h-full transition-all duration-500" style={{ width: `${stats.compliance.helmetCompliance}%`, background: '#A3FF3C', boxShadow: '0 0 8px rgba(163,255,60,0.4)' }} />
            </div>
            <span className="text-xl font-bold font-mono" style={{ color: '#A3FF3C' }}>{stats.compliance.helmetCompliance.toFixed(0)}%</span>
          </div>
        </HudCard>
        <HudCard title="Seatbelt Compliance" accent>
          <div className="flex items-center gap-4">
            <div className="flex-1" style={{ background: '#3A434F', height: '12px' }}>
              <div className="h-full transition-all duration-500" style={{ width: `${stats.compliance.seatbeltCompliance}%`, background: '#7BFF7B', boxShadow: '0 0 8px rgba(123,255,123,0.4)' }} />
            </div>
            <span className="text-xl font-bold font-mono" style={{ color: '#7BFF7B' }}>{stats.compliance.seatbeltCompliance.toFixed(0)}%</span>
          </div>
        </HudCard>
      </div>
    </>
  );
};

export default Analytics;