import { apiClient } from './client';
import type { ReviewItem } from '../types';

export const reviewApi = {
  getPendingReviews: () =>
    apiClient.get<{ success: boolean; data: ReviewItem[] }>('/analytics/violations'),

  updateStatus: (id: string, status: 'approved' | 'rejected' | 'false_positive', notes?: string) =>
    apiClient.post<{ success: boolean }>('/analytics/review', { id, status, notes }),
};
