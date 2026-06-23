import { apiClient } from './client';
import type { DangerousJunction, RepeatOffender } from '../types';

export const insightsApi = {
  getDangerousJunctions: (params?: Record<string, string>) =>
    apiClient.get<{ success: boolean; data: DangerousJunction[] }>('/insights/dangerous-junctions', { params }),

  getRepeatOffenders: (params?: Record<string, string>) =>
    apiClient.get<{ success: boolean; data: RepeatOffender[] }>('/insights/repeat-offenders', { params }),
};