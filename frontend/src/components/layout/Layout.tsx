import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { Footer } from './Footer';

const Layout: React.FC = () => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="h-screen flex overflow-hidden" style={{ background: '#0B0F13' }}>
      {/* Grid overlay */}
      <div className="fixed inset-0 pointer-events-none z-0"
        style={{
          backgroundImage: `
            linear-gradient(rgba(163,255,60,0.015) 1px, transparent 1px),
            linear-gradient(90deg, rgba(163,255,60,0.015) 1px, transparent 1px)
          `,
          backgroundSize: '50px 50px',
        }}
      />
      {/* Scan line */}
      <div className="fixed left-0 right-0 h-[2px] pointer-events-none z-0"
        style={{
          background: 'linear-gradient(90deg, transparent, rgba(163,255,60,0.08), transparent)',
          animation: 'scanLine 3s ease-in-out infinite',
        }}
      />

      <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(c => !c)} />
      <div className="flex-1 flex flex-col min-w-0 relative z-10">
        <Header />
        <main className="flex-1 overflow-y-auto p-5 space-y-5" style={{ animation: 'fadeIn 0.3s ease-out' }}>
          <Outlet />
        </main>
        <Footer />
      </div>
    </div>
  );
};

export default Layout;
