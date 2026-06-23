import { apiClient } from './client';
import type { ReportData } from '../types';

export const reportsApi = {
  generate: (startDate?: string, endDate?: string, types?: string[]) =>
    apiClient.post<{ success: boolean; reportId: string; data: ReportData }>('/reports/generate', {
      startDate, endDate, types
    }),
};
