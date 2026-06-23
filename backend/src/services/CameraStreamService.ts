import fs from 'fs';
import path from 'path';
import { spawn } from 'child_process';
import { getWebSocketServer } from '../websocket/WebSocketServer';

interface ActiveStream {
  cameraId: number;
  timer: ReturnType<typeof setInterval>;
  currentTick: number;
}

export class CameraStreamService {
  private activeStreams: Map<number, ActiveStream> = new Map();
  private pythonPath: string;
  private modulePath: string;
  private uploadDir: string;
  private frameCache: Map<string, { image: string; violations: any[]; timestamp: string }> = new Map();

  constructor() {
    const defaultPython = process.platform === 'win32' ? 'python' : 'python3';
    this.pythonPath = process.env.PYTHON_PATH || defaultPython;
    this.modulePath = path.resolve(__dirname, process.env.PYTHON_MODULE_PATH || '../../../traffic_violation_project');
    this.uploadDir = path.resolve(__dirname, process.env.UPLOAD_DIR || '../../../uploads');
  }

  private getSampleImages(): string[] {
    try {
      if (!fs.existsSync(this.uploadDir)) return [];
      return fs.readdirSync(this.uploadDir)
        .filter(f => {
          const ext = path.extname(f).toLowerCase();
          return ['.jpg', '.jpeg', '.png', '.mp4', '.avi', '.mov'].includes(ext) || !path.extname(f);
        })
        .map(f => path.join(this.uploadDir, f));
    } catch {
      return [];
    }
  }

  async startStream(cameraId: number): Promise<void> {
    if (this.activeStreams.has(cameraId)) return;

    const images = this.getSampleImages();
    if (images.length === 0) {
      console.warn(`No sample images found in ${this.uploadDir} for camera ${cameraId} stream`);
    }

    const stream: ActiveStream = {
      cameraId,
      timer: setInterval(async () => {
        await this.processTick(stream);
      }, 5000),
      currentTick: 0,
    };

    this.activeStreams.set(cameraId, stream);
    console.log(`Camera ${cameraId} stream started`);

    const ws = getWebSocketServer();
    if (ws) {
      ws.broadcast({
        type: 'CAMERA_DETECTION_STARTED',
        cameraId,
        timestamp: new Date().toISOString(),
      });
    }

    await this.processTick(stream);
  }

  stopStream(cameraId: number): void {
    const stream = this.activeStreams.get(cameraId);
    if (!stream) return;

    clearInterval(stream.timer);
    this.activeStreams.delete(cameraId);
    console.log(`Camera ${cameraId} stream stopped`);

    const ws = getWebSocketServer();
    if (ws) {
      ws.broadcast({
        type: 'CAMERA_DETECTION_STOPPED',
        cameraId,
        timestamp: new Date().toISOString(),
      });
    }
  }

  isStreaming(cameraId: number): boolean {
    return this.activeStreams.has(cameraId);
  }

  private async processTick(stream: ActiveStream): Promise<void> {
    const images = this.getSampleImages();
    if (images.length === 0) {
      this.broadcastFrame(stream.cameraId, null, []);
      return;
    }

    stream.currentTick++;
    const imagePath = images[stream.currentTick % images.length];

    try {
      const result = await this.runDetection(imagePath);
      const violations = result?.violations || [];

      let base64Image: string | null = null;
      if (result?.annotated_image_path && fs.existsSync(result.annotated_image_path)) {
        base64Image = fs.readFileSync(result.annotated_image_path).toString('base64');
      } else if (fs.existsSync(imagePath)) {
        base64Image = fs.readFileSync(imagePath).toString('base64');
      }

      const timestamp = new Date().toISOString();

      this.broadcastFrame(stream.cameraId, base64Image, violations);
      this.frameCache.set(`cam_${stream.cameraId}`, {
        image: base64Image || '',
        violations,
        timestamp,
      });

      const ws = getWebSocketServer();
      if (ws) {
        for (const v of violations) {
          ws.broadcastViolation({
            ...v,
            cameraId: stream.cameraId,
            source: 'live',
            savedAt: timestamp,
          });
        }
      }
    } catch (err: any) {
      console.error(`Camera ${stream.cameraId} tick error:`, err.message);
      this.broadcastFrame(stream.cameraId, null, []);
    }
  }

  private broadcastFrame(cameraId: number, frameBase64: string | null, violations: any[]): void {
    const ws = getWebSocketServer();
    if (!ws) return;

    ws.broadcast({
      type: 'CAMERA_FRAME',
      cameraId,
      frame: frameBase64,
      violations: violations.map(v => ({
        type: v.type || v.violation_type,
        confidence: v.confidence,
        plateText: v.plateText || v.plate_text || null,
        bbox: v.bbox || v.box,
      })),
      timestamp: new Date().toISOString(),
    });
  }

  private runDetection(imagePath: string): Promise<any> {
    return new Promise((resolve, reject) => {
      const script = path.join(this.modulePath, 'violation_detector.py');
      const args = [script, '--image', imagePath, '--confidence', '0.3', '--preprocess', 'true', '--json'];

      const proc = spawn(this.pythonPath, args, { cwd: this.modulePath });
      let stdout = '';
      let stderr = '';

      proc.stdout.on('data', (data) => { stdout += data.toString(); });
      proc.stderr.on('data', (data) => { console.log('Python stream:', data.toString().trim()); });

      proc.on('close', (code) => {
        if (code !== 0) {
          resolve({ violations: [] });
          return;
        }
        try {
          resolve(JSON.parse(stdout.trim()));
        } catch {
          resolve({ violations: [] });
        }
      });

      proc.on('error', () => resolve({ violations: [] }));
    });
  }

  stopAll(): void {
    for (const [id] of this.activeStreams) {
      this.stopStream(id);
    }
  }
}

export const cameraStreamService = new CameraStreamService();
