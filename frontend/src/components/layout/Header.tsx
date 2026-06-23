import React, { useState, useEffect } from 'react';
import { Bell, Wifi, Cpu, Activity, Radio } from 'lucide-react';

export const Header: React.FC = () => {
  const [time, setTime] = useState(new Date());
  const [notifications] = useState(3);
  const [gpu] = useState(89);
  const [latency] = useState(22);
  const [nodes] = useState(32);

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header
      className="h-14 px-5 flex items-center justify-between border-b"
      style={{ background: '#141A20', borderColor: '#3A434F' }}
    >
      {/* Left: System Status */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="status-dot online" />
          <span className="text-xs text-[#A3FF3C] font-mono font-medium tracking-wider">SYSTEM ONLINE</span>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <Cpu size={12} className="text-[#A3FF3C]" strokeWidth={1.5} />
            <span className="text-[11px] font-mono text-[#A3FF3C]">{gpu}%</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Radio size={12} className="text-[#A3FF3C]" strokeWidth={1.5} />
            <span className="text-[11px] font-mono text-[#A3FF3C]">{latency}ms</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Wifi size={12} className="text-[#A3FF3C]" strokeWidth={1.5} />
            <span className="text-[11px] font-mono text-[#A3FF3C]">{nodes} nodes</span>
          </div>
        </div>
      </div>

      {/* Right */}
      <div className="flex items-center gap-5">
        <div className="relative">
          <Bell size={16} className="text-[#6B7280] hover:text-[#EAEAEA] cursor-pointer transition-colors" strokeWidth={1.5} />
          {notifications > 0 && (
            <span className="absolute -top-1.5 -right-1.5 w-3.5 h-3.5 bg-[#FF5D5D] text-white text-[9px] font-bold font-mono flex items-center justify-center">
              {notifications}
            </span>
          )}
        </div>

        <div className="h-4 w-px" style={{ background: '#3A434F' }} />

        <div className="text-right">
          <div className="text-sm text-[#EAEAEA] font-mono tracking-wider">
            {time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </div>
          <div className="text-[9px] text-[#6B7280] font-mono tracking-wider">
            {time.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })}
          </div>
        </div>
      </div>
    </header>
  );
};
