import { apiClient } from './client';
import type { JobStatus } from '../types';

export const detectionApi = {
  detectImage: (file: File, confidence = 0.5, preprocess = true, enhanced = false) => {
    const fd = new FormData();
    fd.append('image', file);
    fd.append('confidence', String(confidence));
    fd.append('preprocess', String(preprocess));
    fd.append('enhanced', String(enhanced));
    return apiClient.post<{ success: boolean; jobId: string; enhanced: boolean }>('/detection/image', fd);
  },

  detectVideo: (file: File, confidence = 0.5, frameInterval = 30, maxFrames = 100, enhanced = false) => {
    const fd = new FormData();
    fd.append('video', file);
    fd.append('confidence', String(confidence));
    fd.append('frameInterval', String(frameInterval));
    fd.append('maxFrames', String(maxFrames));
    fd.append('enhanced', String(enhanced));
    return apiClient.post<{ success: boolean; jobId: string; enhanced: boolean }>('/detection/video', fd);
  },

  getStatus: (jobId: string) =>
    apiClient.get<JobStatus>(`/detection/status/${jobId}`),
};
