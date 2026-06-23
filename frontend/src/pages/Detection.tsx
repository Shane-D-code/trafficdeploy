import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { detectionApi } from '../api/detection';
import { getWebSocketClient } from '../api/websocket';
import { HudCard } from '../components/common/HudCard';
import { HudButton } from '../components/common/HudButton';
import DetectionCanvas from '../components/detection/DetectionCanvas';
import { DetectionPanel } from '../components/detection/DetectionPanel';
import { ViolationList } from '../components/detection/ViolationList';
import { HudSpinner } from '../components/common/HudSpinner';
import { Upload, Image as ImageIcon, Video, AlertCircle } from 'lucide-react';
import type { Violation } from '../types';

const Detection: React.FC = () => {
  const [tab, setTab] = useState<'image' | 'video'>('image');
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [violations, setViolations] = useState<Violation[]>([]);
  const [selectedViolation, setSelectedViolation] = useState<Violation | null>(null);
  const [annotatedImageUrl, setAnnotatedImageUrl] = useState<string | null>(null);
  const [confidence, setConfidence] = useState(0.25);
  const [preprocess, setPreprocess] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [progress, setProgress] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollingAttempts = useRef(0);
  const jobCompleted = useRef(false);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const detectMutation = useMutation({
    mutationFn: async (f: File) => {
      setError(null);
      setProgress(0);
      setAnnotatedImageUrl(null);
      pollingAttempts.current = 0;
      jobCompleted.current = false;
      const resp = tab === 'video'
        ? await detectionApi.detectVideo(f, confidence)
        : await detectionApi.detectImage(f, confidence, preprocess);
      const { jobId } = resp.data;

      const ws = getWebSocketClient();
      ws.connect();

      return new Promise<Violation[]>((resolve, reject) => {
        let done = false;
        const finish = (err?: string, violations?: Violation[]) => {
          if (done) return;
          done = true;
          jobCompleted.current = true;
          stopPolling();
          unsubWs();
          if (err) reject(new Error(err));
          else resolve(violations || []);
        };

        const unsubWs = ws.onMessage((message: any) => {
          if (message.jobId !== jobId) return;
          if (message.type === 'JOB_PROGRESS') {
            setProgress(message.progress);
          }
          if (message.type === 'JOB_COMPLETE') {
            const err = message.results?.error;
            if (err) {
              finish(err);
              return;
            }
            const v = message.results?.violations || [];
            setViolations(v);
            setAnnotatedImageUrl(message.results?.annotated_image_url || null);
            setProgress(100);
            finish(undefined, v);
          }
          if (message.type === 'JOB_ERROR') {
            finish(message.error || 'Job failed');
          }
        });

        pollingRef.current = setInterval(async () => {
          if (done) return;

          pollingAttempts.current++;
          if (pollingAttempts.current > 300) {
            finish('Processing timeout - job took too long');
            return;
          }

          try {
            const status = await detectionApi.getStatus(jobId);
            if (status.data.status === 'complete') {
              const resultErr = status.data.result?.error;
              if (resultErr) {
                finish(resultErr);
                return;
              }
              setAnnotatedImageUrl(status.data.result?.annotated_image_url || null);
              finish(undefined, status.data.result?.violations || []);
            } else if (status.data.status === 'error') {
              finish(status.data.message || 'Processing failed');
            } else {
              setProgress(status.data.progress || 0);
            }
          } catch {
            // retry on transient errors
          }
        }, 2000);
      });
    },
    onSuccess: (data) => {
      if (data) setViolations(data);
    },
    onError: (e: any) => {
      setError(e.message || 'Detection failed. Check the server logs.');
    },
  });

  const handleFile = useCallback((f: File) => {
    const isImage = f.type.startsWith('image/');
    const isVideo = f.type.startsWith('video/');
    if (!isImage && !isVideo) { setError('Please select a valid image or video file'); return; }
    if (isImage) setTab('image');
    if (isVideo) setTab('video');
    setFile(f);
    setViolations([]);
    setSelectedViolation(null);
    setError(null);
    setProgress(0);
    if (isImage) {
      const reader = new FileReader();
      reader.onload = () => setPreview(reader.result as string);
      reader.readAsDataURL(f);
    } else {
      setPreview(null);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, [handleFile]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
  }, [handleFile]);

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  const isVideoTab = tab === 'video';
  const acceptAttr = isVideoTab ? 'video/mp4' : 'image/jpeg,image/png';

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-heading text-[#EAEAEA] tracking-widest">DETECTION CENTER</h1>
          <p className="text-xs text-[#6B7280] font-mono mt-0.5 tracking-wider">UPLOAD TRAFFIC MEDIA FOR AI VIOLATION ANALYSIS</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-5">
        <div className="lg:col-span-1 space-y-5">
          <HudCard title="Upload" accent>
            {/* Tab switcher */}
            <div className="flex gap-1 mb-4" style={{ borderBottom: '1px solid rgba(58,67,79,0.4)', paddingBottom: '12px' }}>
              {(['image', 'video'] as const).map(t => (
                <button
                  key={t}
                  onClick={() => { setTab(t); setFile(null); setPreview(null); setViolations([]); setError(null); }}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono transition-all"
                  style={{
                    background: tab === t ? 'rgba(163,255,60,0.1)' : 'transparent',
                    border: `1px solid ${tab === t ? 'rgba(163,255,60,0.4)' : 'rgba(58,67,79,0.4)'}`,
                    color: tab === t ? '#A3FF3C' : '#6B7280',
                  }}
                >
                  {t === 'image' ? <ImageIcon className="w-3 h-3" /> : <Video className="w-3 h-3" />}
                  {t.toUpperCase()}
                </button>
              ))}
            </div>

            <div
              onDrop={handleDrop}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onClick={() => inputRef.current?.click()}
              className="p-6 text-center cursor-pointer transition-all"
              style={{
                border: `2px dashed ${dragOver ? '#A3FF3C' : '#3A434F'}`,
                background: dragOver ? 'rgba(163,255,60,0.03)' : 'transparent',
              }}
            >
              <input ref={inputRef} type="file" accept={acceptAttr} className="hidden" onChange={handleChange} />
              {file ? (
                <div className="space-y-2">
                  <div className="w-12 h-12 mx-auto flex items-center justify-center" style={{ border: '1px solid rgba(163,255,60,0.3)' }}>
                    {isVideoTab
                      ? <Video className="w-6 h-6" style={{ color: '#A3FF3C' }} />
                      : <ImageIcon className="w-6 h-6" style={{ color: '#A3FF3C' }} />}
                  </div>
                  <p className="text-sm font-mono" style={{ color: '#A3FF3C' }}>{file.name}</p>
                  <p className="text-xs text-[#6B7280] font-mono">Click or drop to change</p>
                </div>
              ) : (
                <div className="space-y-2">
                  <Upload className="w-8 h-8 mx-auto" style={{ color: '#3A434F' }} />
                  <p className="text-sm text-[#6B7280] font-mono">
                    {isVideoTab ? 'Drop video or click' : 'Drop image or click'}
                  </p>
                  <p className="text-xs" style={{ color: '#3A434F' }}>
                    {isVideoTab ? 'MP4 · Max 100 MB · Every 30th frame' : 'JPG, PNG · Max 50 MB'}
                  </p>
                </div>
              )}
            </div>

            {file && (
              <div className="mt-4 space-y-4">
                <div>
                  <label className="text-xs text-[#6B7280] font-mono block mb-1.5">
                    Confidence Threshold: {(confidence * 100).toFixed(0)}%
                  </label>
                  <input type="range" min={0.05} max={0.9} step={0.05} value={confidence}
                    onChange={(e) => setConfidence(parseFloat(e.target.value))}
                    className="w-full" style={{ accentColor: '#A3FF3C' }} />
                  <div className="flex justify-between text-[10px] text-[#3A434F] font-mono mt-0.5">
                    <span>5%</span>
                    <span>90%</span>
                  </div>
                </div>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={preprocess} onChange={(e) => setPreprocess(e.target.checked)}
                    className="rounded" style={{ borderColor: '#3A434F', accentColor: '#A3FF3C' }} />
                  <span className="text-xs text-[#6B7280] font-mono">Enable preprocessing</span>
                </label>

                {detectMutation.isPending && (
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs text-[#6B7280] font-mono">
                      <span>Processing...</span>
                      <span>{progress}%</span>
                    </div>
                    <div className="w-full h-1.5" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.3)' }}>
                      <div className="h-full transition-all duration-300" style={{ width: `${progress}%`, background: '#A3FF3C' }} />
                    </div>
                  </div>
                )}

                <HudButton className="w-full" variant="primary" onClick={() => file && detectMutation.mutate(file)} loading={detectMutation.isPending}>
                  {detectMutation.isPending ? 'Processing...' : 'Detect Violations'}
                </HudButton>
                <HudButton className="w-full" variant="danger" onClick={() => {
                  setFile(null); setPreview(null); setViolations([]); setSelectedViolation(null); setError(null); setProgress(0);
                }}>
                  Clear
                </HudButton>
              </div>
            )}

            {error && (
              <div className="mt-4 p-3 flex items-start gap-2" style={{ background: 'rgba(255,93,93,0.05)', border: '1px solid rgba(255,93,93,0.2)' }}>
                <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" style={{ color: '#FF5D5D' }} />
                <p className="text-xs font-medium" style={{ color: '#FF5D5D' }}>{error}</p>
              </div>
            )}
          </HudCard>

          {violations.length > 0 && (
            <HudCard title={`Detections (${violations.length})`} accent>
              <ViolationList violations={violations} onViolationSelect={setSelectedViolation} />
            </HudCard>
          )}
        </div>

        <div className="lg:col-span-2">
          <HudCard title="Analysis View" accent scan>
            {detectMutation.isPending ? (
              <HudSpinner size="lg" text="Running AI detection" />
            ) : (
              <DetectionCanvas image={preview} violations={violations} annotatedImageUrl={annotatedImageUrl} onViolationClick={setSelectedViolation} />
            )}
          </HudCard>

          {violations.length > 0 && (
            <HudCard title={`Violations (${violations.length})`} accent className="mt-5">
              <div className="grid grid-cols-3 gap-3">
                <div className="text-center p-3" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.3)' }}>
                  <p className="text-2xl font-bold font-mono" style={{ color: '#FF5D5D' }}>{violations.length}</p>
                  <p className="hud-label mt-0.5">Total</p>
                </div>
                <div className="text-center p-3" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.3)' }}>
                  <p className="text-2xl font-bold font-mono" style={{ color: '#A3FF3C' }}>{violations.filter(v => v.confidence > 0.8).length}</p>
                  <p className="hud-label mt-0.5">High Conf.</p>
                </div>
                <div className="text-center p-3" style={{ background: '#0B0F13', border: '1px solid rgba(58,67,79,0.3)' }}>
                  <p className="text-2xl font-bold font-mono" style={{ color: '#7BFF7B' }}>{violations.filter(v => v.plateText).length}</p>
                  <p className="hud-label mt-0.5">Plates</p>
                </div>
              </div>
            </HudCard>
          )}
        </div>

        <div className="lg:col-span-1">
          <DetectionPanel violation={selectedViolation} violations={violations} />
        </div>
      </div>
    </>
  );
};

export default Detection;