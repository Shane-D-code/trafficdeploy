import { apiClient } from './client';

export interface IncidentSummary {
  total_violations: number;
  total_fine: number;
  max_confidence: number;
  timestamp: string;
  license_plate: string;
  image_path: string;
  evidence_path: string;
  status: string;
}

export interface Incident {
  incidentId: string;
  summary: IncidentSummary;
  violations: any[];
  fineBreakdown: {
    total: number;
    breakdown: Array<{
      violation_type: string;
      confidence: number;
      fine: number;
      status: string;
    }>;
  };
  totalFine: number;
  canApprove: boolean;
}

export const reviewApi = {
  getIncidents: (params?: { status?: string; page?: number; limit?: number }) =>
    apiClient.get<{ success: boolean; incidents: Incident[]; total: number }>('/analytics/incidents', { params }),

  approveIncident: (incidentId: string, data: { officerId: string; notes?: string }) =>
    apiClient.post<{ success: boolean; message: string }>(`/analytics/incidents/${incidentId}/review`, {
      status: 'approved',
      ...data,
    }),

  rejectIncident: (incidentId: string, data: { officerId: string; reason?: string }) =>
    apiClient.post<{ success: boolean; message: string }>(`/analytics/incidents/${incidentId}/review`, {
      status: 'rejected',
      ...data,
    }),

  falsePositive: (incidentId: string, data: { officerId: string; notes?: string }) =>
    apiClient.post<{ success: boolean; message: string }>(`/analytics/incidents/${incidentId}/review`, {
      status: 'false_positive',
      ...data,
    }),

  getPendingReviews: () =>
    apiClient.get<{ success: boolean; data: any[] }>('/analytics/violations'),

  updateStatus: (id: string, status: 'approved' | 'rejected' | 'false_positive', notes?: string) =>
    apiClient.post<{ success: boolean }>('/analytics/review', { id, status, notes }),
};
