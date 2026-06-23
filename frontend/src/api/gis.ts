import { apiClient } from './client';

export const gisApi = {
  getHeatmap: (params?: { days?: number }) =>
    apiClient.get<{ success: boolean; data: any[]; total: number }>('/gis/heatmap', { params }).then(res => res.data),

  getDangerousZones: (params?: { threshold?: number }) =>
    apiClient.get<{ success: boolean; zones: any[]; total: number }>('/gis/dangerous-zones', { params }).then(res => res.data),
};
