import React from 'react';
import { NavLink } from 'react-router-dom';
import { Home, Camera, Upload, Activity, FileText, BarChart, Database, Settings, ChevronLeft, Shield } from 'lucide-react';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

const menuItems = [
  { path: '/', icon: Home, label: 'Dashboard', id: 'DASH' },
  { path: '/live', icon: Camera, label: 'Live Camera', id: 'CAM' },
  { path: '/detection', icon: Upload, label: 'Upload Image', id: 'UPL' },
  { path: '/logs', icon: Activity, label: 'Violation Logs', id: 'LOG' },
  { path: '/reports', icon: FileText, label: 'Reports', id: 'RPT' },
  { path: '/review', icon: Shield, label: 'Review Panel', id: 'REV' },
  { path: '/analytics', icon: BarChart, label: 'Analytics', id: 'ANL' },
  { path: '/evidence', icon: Database, label: 'Evidence', id: 'EVI' },
  { path: '/settings', icon: Settings, label: 'Settings', id: 'CFG' },
];

export const Sidebar: React.FC<SidebarProps> = ({ collapsed, onToggle }) => {
  return (
    <div
      className={`transition-all duration-300 flex flex-col border-r ${
        collapsed ? 'w-16' : 'w-60'
      }`}
      style={{ background: '#141A20', borderColor: '#3A434F' }}
    >
      {/* Brand */}
      <div className="h-14 flex items-center px-4 border-b" style={{ borderColor: '#3A434F' }}>
        {!collapsed ? (
          <div className="flex items-center gap-3">
            <div className="relative flex items-center justify-center w-8 h-8">
              <div className="w-8 h-8 border border-[#A3FF3C] flex items-center justify-center" style={{ opacity: 0.6 }}>
                <span className="text-[#A3FF3C] text-xs font-bold font-heading">GL</span>
              </div>
              <div className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-[#A3FF3C]" style={{ opacity: 0.8 }} />
            </div>
            <div>
              <span className="text-sm font-heading text-[#EAEAEA] tracking-widest">GRIDLOCK</span>
              <span className="block text-[9px] text-[#6B7280] font-mono tracking-wider">MISSION CONTROL</span>
            </div>
          </div>
        ) : (
          <div className="mx-auto relative flex items-center justify-center w-8 h-8">
            <div className="w-8 h-8 border border-[#A3FF3C] flex items-center justify-center" style={{ opacity: 0.6 }}>
              <span className="text-[#A3FF3C] text-xs font-bold font-heading">GL</span>
            </div>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 px-2 space-y-0.5 overflow-y-auto">
        {menuItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => `
              flex items-center gap-3 px-3 py-2.5 transition-all duration-150 text-sm
              ${isActive
                ? 'text-[#A3FF3C] border border-[#A3FF3C]'
                : 'text-[#6B7280] hover:text-[#EAEAEA] border border-transparent'
              }
              ${collapsed ? 'justify-center' : ''}
            `}
            style={({ isActive }) => isActive ? {
              background: 'rgba(163,255,60,0.04)',
              boxShadow: '0 0 10px rgba(163,255,60,0.04), inset 0 0 10px rgba(163,255,60,0.02)'
            } : {}}
            title={collapsed ? item.label : ''}
          >
            <item.icon size={16} strokeWidth={1.5} />
            {!collapsed && <span className="font-body font-medium tracking-wide">{item.label}</span>}
            {!collapsed && (
              <span className="ml-auto text-[9px] font-mono text-[#3A434F]">{item.id}</span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Status */}
      <div className="p-4 border-t" style={{ borderColor: '#3A434F' }}>
        {!collapsed ? (
          <div className="flex items-center gap-2">
            <span className="status-dot online" />
            <span className="text-xs text-[#A3FF3C] font-mono font-medium tracking-wider">SYS.ONLINE</span>
          </div>
        ) : (
          <span className="status-dot online mx-auto block" />
        )}
      </div>

      {/* Collapse toggle */}
      <button
        onClick={onToggle}
        className="h-8 border-t flex items-center justify-center text-[#3A434F] hover:text-[#A3FF3C] transition-colors"
        style={{ borderColor: '#3A434F' }}
      >
        <ChevronLeft size={14} className={`transition-transform ${collapsed ? 'rotate-180' : ''}`} />
      </button>
    </div>
  );
};
