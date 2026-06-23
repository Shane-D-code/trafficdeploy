import React, { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { gisApi } from '../../api/gis';

interface HeatmapPoint {
  lat: number;
  lng: number;
  count: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
}

export const Heatmap: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [points, setPoints] = useState<HeatmapPoint[]>([]);

  const { data, isLoading } = useQuery({
    queryKey: ['gis-heatmap'],
    queryFn: () => gisApi.getHeatmap({ days: 30 }),
  });

  useEffect(() => {
    if (data?.data) {
      const aggregated: Record<string, { count: number; lat: number; lng: number }> = {};
      for (const v of data.data) {
        const key = `${v.lat.toFixed(4)}_${v.lng.toFixed(4)}`;
        if (!aggregated[key]) {
          aggregated[key] = { count: 0, lat: v.lat, lng: v.lng };
        }
        aggregated[key].count++;
      }

      const maxCount = Math.max(...Object.values(aggregated).map(a => a.count), 1);
      setPoints(
        Object.values(aggregated).map(a => ({
          lat: a.lat,
          lng: a.lng,
          count: a.count,
          severity: a.count > maxCount * 0.5 ? 'critical' : a.count > maxCount * 0.3 ? 'high' : a.count > maxCount * 0.1 ? 'medium' : 'low',
        }))
      );
    }
  }, [data]);

  useEffect(() => {
    if (canvasRef.current && points.length > 0) {
      drawHeatmap(canvasRef.current, points);
    }
  }, [points]);

  const drawHeatmap = (canvas: HTMLCanvasElement, pts: HeatmapPoint[]) => {
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    ctx.fillStyle = '#0D1117';
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = '#1a1a2e';
    ctx.lineWidth = 1;
    for (let i = 0; i < width; i += 50) {
      ctx.beginPath();
      ctx.moveTo(i, 0);
      ctx.lineTo(i, height);
      ctx.stroke();
    }
    for (let i = 0; i < height; i += 50) {
      ctx.beginPath();
      ctx.moveTo(0, i);
      ctx.lineTo(width, i);
      ctx.stroke();
    }

    const maxCount = Math.max(...pts.map(p => p.count), 1);

    for (const point of pts) {
      const x = ((point.lng - 77.5) / 0.2) * width + width / 2;
      const y = ((13.0 - point.lat) / 0.1) * (height * 0.5) + height * 0.15;

      if (x > 0 && x < width && y > 0 && y < height) {
        const radius = Math.max(10, Math.min(40, (point.count / maxCount) * 40));
        const intensity = Math.min(1, point.count / maxCount);

        let color: [number, number, number];
        switch (point.severity) {
          case 'critical':
            color = [255, 0, 0];
            break;
          case 'high':
            color = [255, 165, 0];
            break;
          case 'medium':
            color = [255, 255, 0];
            break;
          default:
            color = [0, 255, 0];
        }

        const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius);
        gradient.addColorStop(0, `rgba(${color[0]}, ${color[1]}, ${color[2]}, ${0.6 * intensity})`);
        gradient.addColorStop(0.5, `rgba(${color[0]}, ${color[1]}, ${color[2]}, ${0.3 * intensity})`);
        gradient.addColorStop(1, `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0)`);

        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.8)`;
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    const legendX = width - 150;
    const legendY = 20;

    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    ctx.fillRect(legendX - 10, legendY - 10, 160, 130);

    ctx.font = '12px monospace';
    ctx.fillStyle = '#fff';
    ctx.fillText('Heatmap Legend', legendX, legendY + 20);

    const legendItems: [string, [number, number, number], string][] = [
      ['Critical', [255, 0, 0], '>50 violations'],
      ['High', [255, 165, 0], '20-50 violations'],
      ['Medium', [255, 255, 0], '10-20 violations'],
      ['Low', [0, 255, 0], '<10 violations'],
    ];

    let y = legendY + 40;
    for (const [label, color, desc] of legendItems) {
      ctx.fillStyle = `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
      ctx.beginPath();
      ctx.arc(legendX + 10, y + 5, 6, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = '#fff';
      ctx.font = '11px monospace';
      ctx.fillText(label, legendX + 25, y + 10);
      ctx.fillStyle = '#888';
      ctx.font = '10px monospace';
      ctx.fillText(desc, legendX + 100, y + 10);

      y += 25;
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96 bg-gray-900 rounded-lg">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
      </div>
    );
  }

  return (
    <div className="relative">
      <canvas
        ref={canvasRef}
        width={800}
        height={400}
        className="w-full rounded-lg border border-gray-700"
      />
      <div className="absolute top-2 left-2 bg-black/50 px-3 py-1 rounded-lg text-xs text-gray-400">
        Bangalore Heatmap • {points.length} data points
      </div>
    </div>
  );
};
