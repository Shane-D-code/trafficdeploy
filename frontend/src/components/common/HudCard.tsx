import React from 'react';

interface HudCardProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
  accent?: boolean;
  titleExtra?: React.ReactNode;
  scan?: boolean;
  fullHeight?: boolean;
}

export const HudCard: React.FC<HudCardProps> = ({ title, children, className = '', accent = false, titleExtra, scan, fullHeight }) => {
  return (
    <div className={`hud-panel ${fullHeight ? 'h-full' : ''} ${className} ${scan ? 'scan-overlay' : ''} overflow-hidden`}>
      <span className="corner-bl" /><span className="corner-br" />
      {title && (
        <div className="flex items-center justify-between px-5 py-3 border-b" style={{ borderColor: 'rgba(58,67,79,0.4)' }}>
          <div className="flex items-center gap-2">
            {accent && <div className="w-[2px] h-3 bg-[#A3FF3C]" />}
            <h3 className="hud-title">{title}</h3>
          </div>
          {titleExtra && <div className="flex items-center gap-2">{titleExtra}</div>}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
};
