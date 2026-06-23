import React, { useEffect, useState } from 'react';

interface ViolationLocation {
  lat: number;
  lng: number;
  count: number;
  type: string;
  severity: number;
}

export const ViolationHeatmap: React.FC = () => {
  const [locations, setLocations] = useState<ViolationLocation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchLocations = async () => {
      try {
        const response = await fetch('/api/analytics/violations/locations');
        if (response.ok) {
          const data = await response.json();
          setLocations(data.data || []);
        } else {
          setLocations(getFallbackLocations());
        }
      } catch {
        setLocations(getFallbackLocations());
      } finally {
        setLoading(false);
      }
    };

    fetchLocations();
  }, []);

  const getColor = (count: number) => {
    if (count > 20) return '#ef4444';
    if (count > 10) return '#f59e0b';
    if (count > 5) return '#3b82f6';
    return '#22c55e';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 bg-gray-900 rounded-lg">
        <div className="text-center text-gray-400">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-2 text-sm font-mono">Loading violation map...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-64 w-full rounded-lg overflow-hidden bg-gray-900 border border-gray-700">
      <div className="absolute inset-0 p-4">
        <div className="relative w-full h-full">
          {locations.map((loc, idx) => {
            const radius = Math.min(15 + loc.count * 0.5, 40);
            const x = ((loc.lng + 180) / 360) * 100;
            const y = ((90 - loc.lat) / 180) * 100;
            return (
              <div
                key={idx}
                className="absolute rounded-full flex items-center justify-center cursor-pointer group"
                style={{
                  left: `${x}%`,
                  top: `${y}%`,
                  width: `${radius * 2}px`,
                  height: `${radius * 2}px`,
                  marginLeft: `-${radius}px`,
                  marginTop: `-${radius}px`,
                  background: `${getColor(loc.count)}44`,
                  border: `2px solid ${getColor(loc.count)}`,
                }}
              >
                <span className="text-xs font-bold text-white" style={{ fontSize: `${Math.max(8, radius * 0.4)}px` }}>
                  {loc.count}
                </span>
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-10">
                  <div className="bg-gray-800 text-white text-xs rounded-lg px-3 py-2 shadow-lg whitespace-nowrap border border-gray-600">
                    <p className="font-bold">{loc.type.replace('_', ' ')}</p>
                    <p>Violations: {loc.count}</p>
                    <p>Severity: {loc.severity}/10</p>
                  </div>
                </div>
              </div>
            );
          })}
          <div className="absolute bottom-2 left-2 text-xs text-gray-500 font-mono">
            Violation Heatmap
          </div>
          <div className="absolute bottom-2 right-2 flex gap-2 text-xs">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500"></span>Low</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500"></span>Medium</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-500"></span>High</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500"></span>Critical</span>
          </div>
        </div>
      </div>
    </div>
  );
};

function getFallbackLocations(): ViolationLocation[] {
  return [
    { lat: 12.9716, lng: 77.5946, count: 45, type: 'NO_HELMET', severity: 8 },
    { lat: 12.9352, lng: 77.6245, count: 32, type: 'RED_LIGHT', severity: 9 },
    { lat: 12.9822, lng: 77.5899, count: 28, type: 'NO_SEATBELT', severity: 6 },
    { lat: 12.9538, lng: 77.6472, count: 18, type: 'TRIPLE_RIDING', severity: 7 },
    { lat: 12.9279, lng: 77.6271, count: 12, type: 'WRONG_SIDE', severity: 8 },
    { lat: 12.9719, lng: 77.6412, count: 8, type: 'STOP_LINE', severity: 5 },
    { lat: 12.9900, lng: 77.5700, count: 22, type: 'ILLEGAL_PARKING', severity: 4 },
  ].map(loc => ({
    ...loc,
    lat: loc.lat + (Math.random() - 0.5) * 0.05,
    lng: loc.lng + (Math.random() - 0.5) * 0.05,
  }));
}
