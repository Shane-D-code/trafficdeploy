import { Request, Response } from 'express';
import { DetectionService } from '../services/DetectionService';
import { v4 as uuidv4 } from 'uuid';
import fs from 'fs';

const detectionService = new DetectionService();

export const detectImage = async (req: Request, res: Response): Promise<void> => {
  try {
    const file = req.file;
    if (!file) { res.status(400).json({ success: false, error: 'No image file provided' }); return; }

    const jobId = uuidv4();
    const confidence = parseFloat(req.body.confidence) || 0.25;
    const preprocess = req.body.preprocess !== 'false';

    detectionService.processImage(jobId, file.path, { confidenceThreshold: confidence, enablePreprocessing: preprocess });

    res.json({ success: true, jobId, message: 'Image processing started' });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
};

export const detectVideo = async (req: Request, res: Response): Promise<void> => {
  try {
    const file = req.file;
    if (!file) { res.status(400).json({ success: false, error: 'No video file provided' }); return; }

    const jobId = uuidv4();
    const confidence = parseFloat(req.body.confidence) || 0.25;
    const frameInterval = parseInt(req.body.frameInterval) || 30;
    const maxFrames = parseInt(req.body.maxFrames) || 100;

    detectionService.processVideo(jobId, file.path, { confidenceThreshold: confidence, frameInterval, maxFrames });

    res.json({ success: true, jobId, message: 'Video processing started' });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
};

export const getJobStatus = async (req: Request, res: Response): Promise<void> => {
  try {
    const { jobId } = req.params;
    const status = await detectionService.getJobStatus(jobId);
    if (!status) { res.status(404).json({ success: false, error: 'Job not found' }); return; }
    res.json({ success: true, status: status.status, progress: status.progress, message: status.message, result: status.result });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
};

export const getJobResults = async (req: Request, res: Response): Promise<void> => {
  try {
    const { jobId } = req.params;
    const status = await detectionService.getJobStatus(jobId);
    if (!status) { res.status(404).json({ success: false, error: 'Job not found' }); return; }
    if (status.status !== 'complete') { res.status(400).json({ success: false, error: 'Job is not complete yet' }); return; }
    res.json({ success: true, result: status.result });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
};
