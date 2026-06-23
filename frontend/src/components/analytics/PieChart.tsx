import React from 'react';
import { PieChart as RechartsPieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { NEON_COLORS } from '../../utils/constants';

interface Props {
  data: Array<{ type: string; count: number }>;
}

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload?.length) {
    return (
      <div className="bg-dark-card border border-dark-border rounded-lg p-3">
        <p className="font-mono text-xs text-white">{payload[0].name}</p>
        <p className="font-mono text-sm text-neon-cyan">{payload[0].value} violations</p>
      </div>
    );
  }
  return null;
};

export const PieChartComponent: React.FC<Props> = ({ data }) => {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <RechartsPieChart>
        <Pie data={data} dataKey="count" nameKey="type" cx="50%" cy="50%" outerRadius={100} label={({ type }) => type}>
          {data.map((_, i) => <Cell key={i} fill={NEON_COLORS[i % NEON_COLORS.length]} />)}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
      </RechartsPieChart>
    </ResponsiveContainer>
  );
};
