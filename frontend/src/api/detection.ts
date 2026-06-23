import { apiClient } from './client';
import type { JobStatus } from '../types';

export const detectionApi = {
  detectImage: (file: File, confidence = 0.5, preprocess = true) => {
    const fd = new FormData();
    fd.append('image', file);
    fd.append('confidence', String(confidence));
    fd.append('preprocess', String(preprocess));
    return apiClient.post<{ success: boolean; jobId: string }>('/detection/image', fd);
  },

  detectVideo: (file: File, confidence = 0.5, frameInterval = 30, maxFrames = 100) => {
    const fd = new FormData();
    fd.append('video', file);
    fd.append('confidence', String(confidence));
    fd.append('frameInterval', String(frameInterval));
    fd.append('maxFrames', String(maxFrames));
    return apiClient.post<{ success: boolean; jobId: string }>('/detection/video', fd);
  },

  getStatus: (jobId: string) =>
    apiClient.get<JobStatus>(`/detection/status/${jobId}`),
};
