import React from 'react';
import { BarChart as RechartsBarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface Props {
  data: Array<{ type: string; count: number }>;
  color?: string;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload?.length) {
    return (
      <div className="bg-dark-card border border-dark-border rounded-lg p-3">
        <p className="font-mono text-xs text-white">{label}</p>
        {payload.map((p: any, i: number) => (
          <p key={i} className="font-mono text-sm" style={{ color: p.color }}>{p.name}: {p.value}</p>
        ))}
      </div>
    );
  }
  return null;
};

export const BarChartComponent: React.FC<Props> = ({ data, color = '#a855f7' }) => {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <RechartsBarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
        <XAxis dataKey="type" tick={{ fill: '#8b949e', fontSize: 10, fontFamily: 'VT323' }} />
        <YAxis tick={{ fill: '#8b949e', fontSize: 10, fontFamily: 'VT323' }} />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="count" fill={color} radius={[4, 4, 0, 0]} />
      </RechartsBarChart>
    </ResponsiveContainer>
  );
};
