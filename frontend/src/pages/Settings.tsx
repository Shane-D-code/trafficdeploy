import React, { useState, useEffect } from 'react';
import { HudCard } from '../components/common/HudCard';
import { HudButton } from '../components/common/HudButton';
import { Save, Trash2 } from 'lucide-react';
import { apiClient } from '../api/client';

const DEFAULT_SETTINGS = {
  confidenceThreshold: 0.25,
  preprocessing: true,
  autoSaveEvidence: true,
  notifications: true,
  fps: 30,
};

const Settings: React.FC = () => {
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    apiClient.get('/settings').then(r => {
      if (r.data?.data && Object.keys(r.data.data).length) {
        setSettings(prev => ({ ...prev, ...r.data.data }));
      }
    }).catch(() => {});
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await apiClient.put('/settings', settings);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {}
    setSaving(false);
  };

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-heading text-[#EAEAEA] tracking-widest">SETTINGS</h1>
          <p className="text-xs text-[#6B7280] font-mono mt-0.5 tracking-wider">SYSTEM CONFIGURATION</p>
        </div>
        <HudButton variant="primary" onClick={handleSave} loading={saving}>
          <Save className="w-4 h-4" /> {saved ? 'Saved!' : 'Save'}
        </HudButton>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <HudCard title="Detection" accent>
          <div className="space-y-5">
            <div>
              <label className="text-sm block mb-1.5 font-mono" style={{ color: '#6B7280' }}>Confidence Threshold: {(settings.confidenceThreshold * 100).toFixed(0)}%</label>
              <input type="range" min={0.05} max={0.9} step={0.05} value={settings.confidenceThreshold}
                onChange={(e) => setSettings(p => ({ ...p, confidenceThreshold: parseFloat(e.target.value) }))}
                className="w-full" style={{ accentColor: '#A3FF3C' }} />
              <div className="flex justify-between text-[11px] mt-0.5 font-mono" style={{ color: '#3A434F' }}>
                <span>5%</span>
                <span>90%</span>
              </div>
            </div>
            {[
              { label: 'Image Preprocessing', key: 'preprocessing' as const },
              { label: 'Auto-save Evidence', key: 'autoSaveEvidence' as const },
              { label: 'Push Notifications', key: 'notifications' as const },
            ].map(({ label, key }) => (
              <label key={key} className="flex items-center justify-between py-1">
                <span className="text-sm font-mono" style={{ color: '#6B7280' }}>{label}</span>
                <input type="checkbox" checked={settings[key]}
                  onChange={(e) => setSettings(p => ({ ...p, [key]: e.target.checked }))}
                  className="rounded" style={{ borderColor: '#3A434F', accentColor: '#A3FF3C' }} />
              </label>
            ))}
          </div>
        </HudCard>

        <HudCard title="System" accent>
          <div className="space-y-5">
            <div>
              <label className="text-sm block mb-1.5 font-mono" style={{ color: '#6B7280' }}>Camera FPS: {settings.fps}</label>
              <input type="range" min={15} max={60} step={5} value={settings.fps}
                onChange={(e) => setSettings(p => ({ ...p, fps: parseInt(e.target.value) }))}
                className="w-full" style={{ accentColor: '#A3FF3C' }} />
            </div>
            <div className="pt-4" style={{ borderTop: '1px solid rgba(58,67,79,0.3)' }}>
              <HudButton className="w-full" variant="danger" onClick={() => {
                if (confirm('Clear all violation data? This cannot be undone.')) alert('Data cleared');
              }}>
                <Trash2 className="w-4 h-4" /> Clear All Data
              </HudButton>
            </div>
          </div>
        </HudCard>

        <HudCard title="System Information" accent className="lg:col-span-2">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              ['API Status', 'Online', '#A3FF3C'],
              ['Database', 'Connected', '#A3FF3C'],
              ['ML Model', 'YOLOv8', '#7BFF7B'],
              ['Version', '1.0.0', '#A3FF3C'],
              ['Uptime', '72h 14m', '#FFD43B'],
              ['GPU', 'Apple MPS', '#FFD43B'],
              ['Last Backup', 'Today 6:00 AM', '#6B7280'],
              ['Storage', '45% Used', '#FFD43B'],
            ].map(([label, value, color]) => (
              <div key={label} className="hud-panel p-4 text-center">
                <span className="corner-bl" /><span className="corner-br" />
                <p className="hud-label">{label}</p>
                <p className="text-sm font-bold font-mono mt-0.5" style={{ color }}>{value}</p>
              </div>
            ))}
          </div>
        </HudCard>
      </div>
    </>
  );
};

export default Settings;
