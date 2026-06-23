import React from 'react';
import { AlertTriangle, User, Car, Bike, MapPin } from 'lucide-react';

interface StatsCardsProps {
  stats: {
    total: number;
    helmet: number;
    seatbelt: number;
    triple: number;
    wrongSide: number;
    redLight: number;
  };
}

const cards = [
  { label: 'Total Violations', key: 'total' as const, icon: AlertTriangle, color: '#FF5D5D' },
  { label: 'No Helmet', key: 'helmet' as const, icon: User, color: '#FFD43B' },
  { label: 'No Seatbelt', key: 'seatbelt' as const, icon: Car, color: '#7BFF7B' },
  { label: 'Triple Riding', key: 'triple' as const, icon: Bike, color: '#A3FF3C' },
  { label: 'Wrong Side', key: 'wrongSide' as const, icon: MapPin, color: '#FF5D5D' },
  { label: 'Red Light', key: 'redLight' as const, icon: AlertTriangle, color: '#FF5D5D' },
];

export const StatsCards: React.FC<StatsCardsProps> = ({ stats }) => {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      {cards.map((card) => (
        <div key={card.key} className="hud-panel p-4 text-center cursor-default">
          <span className="corner-bl" /><span className="corner-br" />
          <card.icon className="mx-auto mb-2" size={20} strokeWidth={1.5} style={{ color: card.color }} />
          <p className="text-2xl font-bold font-mono" style={{ color: card.color }}>{stats[card.key]}</p>
          <p className="hud-label mt-1">{card.label}</p>
        </div>
      ))}
    </div>
  );
};
