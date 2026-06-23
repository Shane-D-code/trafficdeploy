import React from 'react';
import { LineChart as RechartsLineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface Props {
  data: Array<{ date: string; count: number }>;
  dataKey?: string;
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

export const LineChartComponent: React.FC<Props> = ({ data, dataKey = 'count', color = '#06b6d4' }) => {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <RechartsLineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
        <XAxis dataKey="date" tick={{ fill: '#8b949e', fontSize: 10, fontFamily: 'VT323' }} />
        <YAxis tick={{ fill: '#8b949e', fontSize: 10, fontFamily: 'VT323' }} />
        <Tooltip content={<CustomTooltip />} />
        <Legend wrapperStyle={{ fontSize: '10px', fontFamily: 'VT323', color: '#8b949e' }} />
        <Line type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2} dot={{ r: 3, fill: color }} />
      </RechartsLineChart>
    </ResponsiveContainer>
  );
};
