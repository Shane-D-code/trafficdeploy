import { EventEmitter } from 'events';
import { PythonBridge } from '../python-bridge/bridge';
import { DatabaseService } from './DatabaseService';
import { getWebSocketServer } from '../websocket/WebSocketServer';
import { DetectionResult } from '../types';

interface JobEntry {
  id: string;
  status: 'processing' | 'complete' | 'error';
  progress: number;
  message?: string;
  result?: DetectionResult;
  createdAt: string;
  updatedAt: string;
  options?: any;
  error?: string;
}

function getWS(): any {
  const ws = getWebSocketServer();
  if (!ws) {
    console.warn('WebSocket server not initialized, broadcasting disabled');
    return { broadcast: () => {}, broadcastViolation: () => {}, broadcastJobComplete: () => {}, broadcastJobProgress: () => {} };
  }
  return ws;
}

const JOB_TIMEOUT_MS = 600000; // 10 minutes

export class DetectionService extends EventEmitter {
  private bridge: PythonBridge;
  private db: DatabaseService;
  private jobs: Map<string, JobEntry>;

  constructor() {
    super();
    this.on('error', () => {});
    this.bridge = new PythonBridge();
    this.db = new DatabaseService();
    this.jobs = new Map();
  }

  async processImage(jobId: string, imagePath: string, options: { confidenceThreshold: number; enablePreprocessing: boolean }): Promise<void> {
    const now = new Date().toISOString();
    const jobEntry: JobEntry = {
      id: jobId,
      status: 'processing',
      progress: 0,
      createdAt: now,
      updatedAt: now,
      options
    };

    this.jobs.set(jobId, jobEntry);
    await this.db.saveJob(jobEntry).catch(e => console.error('Failed to save job:', e));
    getWS().broadcastJobProgress(jobId, 0, 'processing');

    try {
      const result = await this.bridge.detectImage(imagePath, options);

      jobEntry.status = 'complete';
      jobEntry.progress = 100;
      jobEntry.result = result;
      jobEntry.updatedAt = new Date().toISOString();
      this.jobs.set(jobId, jobEntry);
      await this.db.updateJob(jobEntry).catch(e => console.error('Failed to update job:', e));

      let savedCount = 0;
      const annotatedImagePath = result.annotated_image_path || null;
      for (const violation of result.violations) {
        try {
          await this.db.saveViolation({ ...violation, job_id: jobId, annotated_image_path: annotatedImagePath });
          savedCount++;
          getWS().broadcastViolation({ ...violation, jobId, annotatedImagePath, savedAt: new Date().toISOString() });
        } catch (error) {
          console.error('Failed to save violation:', error);
        }
      }

      getWS().broadcastJobComplete(jobId, {
        ...result,
        savedCount,
        totalViolations: result.violations.length
      });
    } catch (error: any) {
      jobEntry.status = 'error';
      jobEntry.error = error.message;
      jobEntry.updatedAt = new Date().toISOString();
      this.jobs.set(jobId, jobEntry);
      await this.db.updateJob(jobEntry).catch(e => console.error('Failed to update job:', e));

      getWS().broadcast({
        type: 'JOB_ERROR',
        jobId,
        error: error.message,
        timestamp: new Date().toISOString()
      });
    }
  }

  async processVideo(jobId: string, videoPath: string, options: { confidenceThreshold: number; frameInterval: number; maxFrames: number }): Promise<void> {
    const now = new Date().toISOString();
    const jobEntry: JobEntry = {
      id: jobId,
      status: 'processing',
      progress: 0,
      createdAt: now,
      updatedAt: now,
      options
    };

    this.jobs.set(jobId, jobEntry);
    await this.db.saveJob(jobEntry).catch(e => console.error('Failed to save job:', e));
    getWS().broadcastJobProgress(jobId, 0, 'processing');

    try {
      const result = await this.bridge.detectVideo(videoPath, options);

      jobEntry.status = 'complete';
      jobEntry.progress = 100;
      jobEntry.result = result;
      jobEntry.updatedAt = new Date().toISOString();
      this.jobs.set(jobId, jobEntry);
      await this.db.updateJob(jobEntry).catch(e => console.error('Failed to update job:', e));

      let savedCount = 0;
      const annotatedImagePath = result.annotated_image_path || null;
      if (result.violations) {
        for (const violation of result.violations) {
          try {
            await this.db.saveViolation({ ...violation, job_id: jobId, annotated_image_path: annotatedImagePath });
            savedCount++;
            getWS().broadcastViolation({ ...violation, jobId, annotatedImagePath, savedAt: new Date().toISOString() });
          } catch (error) {
            console.error('Failed to save violation:', error);
          }
        }
      }

      getWS().broadcastJobComplete(jobId, {
        ...result,
        savedCount,
        totalViolations: result.violations ? result.violations.length : 0
      });
    } catch (error: any) {
      jobEntry.status = 'error';
      jobEntry.error = error.message;
      jobEntry.updatedAt = new Date().toISOString();
      this.jobs.set(jobId, jobEntry);
      await this.db.updateJob(jobEntry).catch(e => console.error('Failed to update job:', e));

      getWS().broadcast({
        type: 'JOB_ERROR',
        jobId,
        error: error.message,
        timestamp: new Date().toISOString()
      });
    }
  }

  async getJobStatus(jobId: string): Promise<any> {
    const job = this.jobs.get(jobId);
    if (job) {
      return {
        jobId: job.id,
        status: job.status,
        progress: job.progress,
        message: job.message,
        result: job.result
      };
    }
    try {
      const dbJob = await this.db.getJob(jobId);
      if (dbJob) {
        return {
          jobId: dbJob.id,
          status: dbJob.status,
          progress: dbJob.progress || 0,
          message: dbJob.error || null,
          result: dbJob.result || null
        };
      }
    } catch {
      // DB fallback failed
    }
    return null;
  }

  getDatabaseService(): DatabaseService {
    return this.db;
  }
}
