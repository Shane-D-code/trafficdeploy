import { useState, useCallback } from 'react';
import { detectionApi } from '../api/detection';
import type { Violation } from '../types';

export function useDetection() {
  const [violations, setViolations] = useState<Violation[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const detectImage = useCallback(async (file: File, confidence = 0.5, preprocess = true) => {
    setIsProcessing(true);
    setError(null);
    try {
      const resp = await detectionApi.detectImage(file, confidence, preprocess);
      const { jobId } = resp.data;
      return new Promise<Violation[]>((resolve, reject) => {
        const poll = setInterval(async () => {
          try {
            const status = await detectionApi.getStatus(jobId);
            if (status.data.status === 'complete') {
              clearInterval(poll);
              const result = status.data.result?.violations || [];
              setViolations(result);
              resolve(result);
            } else if (status.data.status === 'error') {
              clearInterval(poll);
              reject(new Error(status.data.message));
            }
          } catch { /* retry */ }
        }, 2000);
      });
    } catch (e: any) {
      setError(e.message);
      throw e;
    } finally {
      setIsProcessing(false);
    }
  }, []);

  const clear = useCallback(() => {
    setViolations([]);
    setError(null);
  }, []);

  return { violations, isProcessing, error, detectImage, clear };
}
