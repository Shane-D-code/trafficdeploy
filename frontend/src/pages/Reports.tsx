import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { reportsApi } from '../api/reports';
import { analyticsApi } from '../api/analytics';
import { HudCard } from '../components/common/HudCard';
import { HudButton } from '../components/common/HudButton';
import { HudSpinner } from '../components/common/HudSpinner';
import { Download, Calendar } from 'lucide-react';
import type { ReportData } from '../types';

const Reports: React.FC = () => {
  const [generating, setGenerating] = useState(false);
  const [report, setReport] = useState<ReportData | null>(null);
  const [dateRange, setDateRange] = useState({
    start: new Date(Date.now() - 30 * 86400000).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0],
  });

  const { data: statsData } = useQuery({
    queryKey: ['analytics-stats'],
    queryFn: () => analyticsApi.getStats(),
    refetchInterval: 30000,
  });

  const totalViolations = statsData?.data?.data?.total || 0;
  const totalVehicles = statsData?.data?.data?.totalVehicles || 0;
  const violationTypeCount = statsData?.data?.data?.byType ? Object.keys(statsData.data.data.byType).length : 0;

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const resp = await reportsApi.generate(dateRange.start, dateRange.end);
      setReport(resp.data.data);
    } catch (e: any) {
      alert(e.response?.data?.error || 'Failed to generate report');
    } finally {
      setGenerating(false);
    }
  };

  const downloadJSON = () => {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `gridlock-report-${dateRange.start}-to-${dateRange.end}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <div>
        <h1 className="text-lg font-heading text-[#EAEAEA] tracking-widest">REPORTS</h1>
        <p className="text-xs text-[#6B7280] font-mono mt-0.5 tracking-wider">GENERATE AND DOWNLOAD VIOLATION REPORTS</p>
      </div>

      <HudCard title="Generate Report" accent>
        <p className="text-sm mb-4 font-mono" style={{ color: '#6B7280' }}>
          Database contains <span className="text-[#A3FF3C] font-semibold">{totalViolations}</span> total violations
        </p>
        <div className="flex flex-wrap gap-4 mb-4">
          <div>
            <label className="hud-label block mb-1.5">Start Date</label>
            <div className="relative">
              <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: '#6B7280' }} />
              <input type="date" value={dateRange.start}
                onChange={(e) => setDateRange(p => ({ ...p, start: e.target.value }))}
                className="hud-input pl-9" />
            </div>
          </div>
          <div>
            <label className="hud-label block mb-1.5">End Date</label>
            <div className="relative">
              <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: '#6B7280' }} />
              <input type="date" value={dateRange.end}
                onChange={(e) => setDateRange(p => ({ ...p, end: e.target.value }))}
                className="hud-input pl-9" />
            </div>
          </div>
        </div>
        <HudButton variant="primary" onClick={handleGenerate} loading={generating}>
          {generating ? 'Generating...' : 'Generate Report'}
        </HudButton>
      </HudCard>

      {generating && <HudSpinner size="lg" text="Compiling report data" />}

      <HudCard title="Live Statistics" accent>
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="hud-panel p-4 text-center">
            <span className="corner-bl" /><span className="corner-br" />
            <p className="text-2xl font-bold font-mono" style={{ color: '#A3FF3C' }}>{totalViolations}</p>
            <p className="hud-label mt-1">Total Violations</p>
          </div>
          <div className="hud-panel p-4 text-center">
            <span className="corner-bl" /><span className="corner-br" />
            <p className="text-2xl font-bold font-mono" style={{ color: '#7BFF7B' }}>{totalVehicles}</p>
            <p className="hud-label mt-1">Vehicles</p>
          </div>
          <div className="hud-panel p-4 text-center">
            <span className="corner-bl" /><span className="corner-br" />
            <p className="text-sm font-bold font-mono" style={{ color: '#A3FF3C' }}>{new Date().toLocaleDateString()}</p>
            <p className="hud-label mt-1">Updated</p>
          </div>
          <div className="hud-panel p-4 text-center">
            <span className="corner-bl" /><span className="corner-br" />
            <p className="text-2xl font-bold font-mono" style={{ color: '#FFD43B' }}>{violationTypeCount}</p>
            <p className="hud-label mt-1">Violation Types</p>
          </div>
        </div>

        {statsData?.data?.data?.compliance && (
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="p-3" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}>
              <div className="flex items-center justify-between mb-1">
                <span className="hud-label">Helmet Compliance</span>
                <span className="text-sm font-bold font-mono" style={{ color: '#A3FF3C' }}>{statsData.data.data.compliance.helmetCompliance.toFixed(0)}%</span>
              </div>
              <div className="w-full h-2" style={{ background: '#3A434F' }}>
                <div className="h-full" style={{ width: `${statsData.data.data.compliance.helmetCompliance}%`, background: '#A3FF3C' }} />
              </div>
            </div>
            <div className="p-3" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}>
              <div className="flex items-center justify-between mb-1">
                <span className="hud-label">Seatbelt Compliance</span>
                <span className="text-sm font-bold font-mono" style={{ color: '#7BFF7B' }}>{statsData.data.data.compliance.seatbeltCompliance.toFixed(0)}%</span>
              </div>
              <div className="w-full h-2" style={{ background: '#3A434F' }}>
                <div className="h-full" style={{ width: `${statsData.data.data.compliance.seatbeltCompliance}%`, background: '#7BFF7B' }} />
              </div>
            </div>
          </div>
        )}

        {statsData?.data?.data?.byType && Object.keys(statsData.data.data.byType).length > 0 && (
          <div className="mb-6">
            <h3 className="text-xs font-mono mb-2" style={{ color: '#6B7280' }}>BREAKDOWN BY TYPE</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
              {Object.entries(statsData.data.data.byType).sort(([, a], [, b]) => b - a).map(([type, count]) => (
                <div key={type} className="flex items-center justify-between p-2" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.2)' }}>
                  <span className="text-xs font-mono" style={{ color: '#EAEAEA' }}>{type.replace('_', ' ')}</span>
                  <span className="text-xs font-bold font-mono" style={{ color: '#FF5D5D' }}>{count}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </HudCard>

      {report && (
        <HudCard title={`Report Summary (${dateRange.start} to ${dateRange.end})`} accent
          titleExtra={<HudButton size="sm" variant="primary" onClick={downloadJSON}><Download className="w-4 h-4" /> Export JSON</HudButton>}>
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="hud-panel p-4 text-center">
              <span className="corner-bl" /><span className="corner-br" />
              <p className="text-2xl font-bold font-mono" style={{ color: '#A3FF3C' }}>{report.totalViolations}</p>
              <p className="hud-label mt-1">Violations (Filtered)</p>
            </div>
            <div className="hud-panel p-4 text-center">
              <span className="corner-bl" /><span className="corner-br" />
              <p className="text-2xl font-bold font-mono" style={{ color: '#7BFF7B' }}>{report.stats.totalVehicles}</p>
              <p className="hud-label mt-1">Vehicles (Filtered)</p>
            </div>
            <div className="hud-panel p-4 text-center">
              <span className="corner-bl" /><span className="corner-br" />
              <p className="text-sm font-bold font-mono" style={{ color: '#A3FF3C' }}>{new Date(report.generatedAt).toLocaleDateString()}</p>
              <p className="hud-label mt-1">Generated</p>
            </div>
            <div className="hud-panel p-4 text-center">
              <span className="corner-bl" /><span className="corner-br" />
              <p className="text-2xl font-bold font-mono" style={{ color: '#FFD43B' }}>{Object.keys(report.stats.byType).length}</p>
              <p className="hud-label mt-1">Types (Filtered)</p>
            </div>
          </div>

          {report.violations.length > 0 && (
            <div className="overflow-x-auto">
              <table className="hud-table w-full">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Plate</th>
                    <th>Confidence</th>
                    <th>Location</th>
                    <th>Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {report.violations.map((v: any) => (
                    <tr key={v.id}>
                      <td className="text-sm" style={{ color: '#EAEAEA' }}>{v.type}</td>
                      <td className="text-sm font-mono" style={{ color: '#6B7280' }}>{v.plateText || '-'}</td>
                      <td className="text-sm font-mono" style={{ color: '#A3FF3C' }}>{(v.confidence * 100).toFixed(1)}%</td>
                      <td className="text-sm font-mono" style={{ color: '#6B7280' }}>{v.location || '-'}</td>
                      <td className="text-sm font-mono" style={{ color: '#6B7280' }}>{new Date(v.timestamp).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </HudCard>
      )}
    </>
  );
};

export default Reports;
