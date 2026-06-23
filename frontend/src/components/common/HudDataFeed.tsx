import React, { useState, useEffect } from 'react';

const events = [
  { time: '12:04', msg: 'Model Updated', type: 'info' },
  { time: '12:05', msg: 'Vector DB Connected', type: 'success' },
  { time: '12:08', msg: 'Agent Started', type: 'info' },
  { time: '12:09', msg: 'Drone Linked', type: 'success' },
  { time: '12:12', msg: 'Anomaly Detected', type: 'warning' },
  { time: '12:15', msg: 'System Check Passed', type: 'success' },
];

export const HudDataFeed: React.FC = () => {
  const [visible, setVisible] = useState(3);

  useEffect(() => {
    const t = setInterval(() => setVisible(v => Math.min(v + 1, events.length)), 3000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="space-y-0">
      {events.slice(0, visible).map((ev, i) => (
        <div key={i} className="data-feed-item">
          <span className="data-feed-time">[{ev.time}]</span>{' '}
          <span className="data-feed-dot">◆</span>{' '}
          <span className={ev.type === 'warning' ? 'text-[#FFD43B]' : 'text-[#EAEAEA]'}>{ev.msg}</span>
        </div>
      ))}
    </div>
  );
};
