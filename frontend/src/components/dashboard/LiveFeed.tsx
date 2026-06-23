import React, { useState, useEffect, useRef } from 'react';

interface LiveFeedProps {
  realtime?: boolean;
  recentViolations?: any[];
}

export const LiveFeed: React.FC<LiveFeedProps> = ({ realtime = false, recentViolations = [] }) => {
  const [fps, setFps] = useState(0);
  const [lastFrameTime, setLastFrameTime] = useState(Date.now());
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();

  useEffect(() => {
    if (!realtime) return;

    const drawFrame = () => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      ctx.fillStyle = '#0B0F13';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.strokeStyle = '#3A434F';
      ctx.lineWidth = 1;
      ctx.strokeRect(10, 10, canvas.width - 20, canvas.height - 20);

      ctx.fillStyle = '#06b6d4';
      ctx.font = '14px monospace';
      ctx.fillText('CAM-001 · MG ROAD', 20, 35);

      ctx.fillStyle = '#c9d1d9';
      ctx.font = '12px monospace';
      ctx.fillText(new Date().toLocaleTimeString(), canvas.width - 180, 35);

      ctx.fillStyle = '#22c55e';
      ctx.font = '12px monospace';
      ctx.fillText(`FPS: ${fps}`, canvas.width - 100, 60);

      const violations = recentViolations.slice(0, 5);
      violations.forEach((violation, index) => {
        const x = 50 + (index % 3) * 250;
        const y = 100 + Math.floor(index / 3) * 150;
        const bbox = violation.bbox || [x, y, x + 200, y + 100];

        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 2;
        ctx.strokeRect(
          bbox[0] / 4, bbox[1] / 4,
          (bbox[2] - bbox[0]) / 4, (bbox[3] - bbox[1]) / 4
        );

        ctx.fillStyle = 'rgba(239, 68, 68, 0.8)';
        const label = `${violation.type || violation.violation_type || 'VIOLATION'} ${(violation.confidence * 100).toFixed(0)}%`;
        const metrics = ctx.measureText(label);
        ctx.fillRect(bbox[0] / 4, bbox[1] / 4 - 20, metrics.width + 10, 20);

        ctx.fillStyle = '#ffffff';
        ctx.font = '12px monospace';
        ctx.fillText(label, bbox[0] / 4 + 5, bbox[1] / 4 - 5);
      });

      ctx.fillStyle = 'rgba(0, 0, 0, 0.03)';
      for (let i = 0; i < canvas.height; i += 3) {
        ctx.fillRect(0, i, canvas.width, 1);
      }

      const now = Date.now();
      if (now - lastFrameTime > 1000) {
        setFps(Math.round(1000 / (now - lastFrameTime) * 10));
        setLastFrameTime(now);
      }

      animationRef.current = requestAnimationFrame(drawFrame);
    };

    drawFrame();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [realtime, recentViolations, lastFrameTime]);

  if (!realtime) {
    return (
      <div className="aspect-video rounded-lg flex items-center justify-center relative overflow-hidden scan-overlay"
        style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.4)' }}>
        <div className="absolute top-3 left-3 flex items-center gap-2 px-2 py-1 z-10" style={{ background: 'rgba(0,0,0,0.6)' }}>
          <span className="status-dot online" />
          <span className="text-xs text-[#A3FF3C] font-mono font-medium tracking-wider">LIVE</span>
        </div>
        <div className="absolute top-3 right-3 px-2 py-1 z-10" style={{ background: 'rgba(0,0,0,0.6)' }}>
          <span className="text-xs text-[#EAEAEA] font-mono tracking-wider">CAM-001 · MG ROAD</span>
        </div>
        <div className="text-center z-10">
          <svg className="w-16 h-16 mx-auto" style={{ color: '#3A434F' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          <p className="text-sm text-[#6B7280] mt-2 font-mono">Camera Feed</p>
          <p className="text-xs text-[#3A434F] mt-1 font-mono">Streaming live traffic at 30 FPS</p>
        </div>
        <div className="absolute bottom-3 left-3 text-[10px] text-[#3A434F] font-mono z-10">
          1920×1080 · H.264
        </div>
      </div>
    );
  }

  return (
    <div className="relative">
      <canvas
        ref={canvasRef}
        width={800}
        height={450}
        className="w-full rounded-lg"
      />
      <div className="absolute top-4 left-4 flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
        <span className="text-xs text-red-400 font-mono">LIVE</span>
      </div>
      {recentViolations.length > 0 && (
        <div className="absolute top-4 right-4 bg-black/50 px-3 py-1 rounded-lg">
          <span className="text-xs font-mono" style={{ color: '#A3FF3C' }}>
            {recentViolations.length} violations detected
          </span>
        </div>
      )}
    </div>
  );
};