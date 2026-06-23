import { apiClient } from './client';
import type { AnalyticsStats, ViolationRecord, MetricsData } from '../types';

export const analyticsApi = {
  getStats: () =>
    apiClient.get<{ success: boolean; data: AnalyticsStats }>('/analytics/stats'),

  getViolations: (params?: Record<string, string>) =>
    apiClient.get<{ success: boolean; data: { rows: ViolationRecord[]; total: number } }>(
      '/analytics/violations', { params }
    ),

  getCompliance: () =>
    apiClient.get<{ success: boolean; data: { helmetCompliance: number; seatbeltCompliance: number } }>(
      '/analytics/compliance'
    ),

  getMetrics: () =>
    apiClient.get<{ success: boolean; data: MetricsData }>('/analytics/metrics'),

  markFalsePositive: (id: string) =>
    apiClient.patch<{ success: boolean; undoAvailable: boolean }>(`/analytics/violations/${id}/false-positive`),

  undoFalsePositive: (id: string) =>
    apiClient.delete<{ success: boolean }>(`/analytics/violations/${id}/false-positive?undo=true`),
};
