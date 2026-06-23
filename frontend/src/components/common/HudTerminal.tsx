import React, { useState, useEffect } from 'react';

const lines = [
  '> Initializing Agent...',
  '> Loading Model ██████████ Done',
  '> Connecting... Latency 23ms',
  '> ML Pipeline Online',
  '> GPU Accelerated Inference',
];

export const HudTerminal: React.FC = () => {
  const [visible, setVisible] = useState(1);

  useEffect(() => {
    if (visible < lines.length) {
      const t = setTimeout(() => setVisible(v => v + 1), 1200);
      return () => clearTimeout(t);
    }
  }, [visible]);

  return (
    <div className="space-y-1">
      {lines.slice(0, visible).map((line, i) => (
        <p key={i} className={`terminal-line text-[#A3FF3C] ${i === visible - 1 && i < lines.length - 1 ? 'terminal-cursor' : ''}`}>
          {line}
        </p>
      ))}
    </div>
  );
};
