import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '../api/analytics';
import type { AnalyticsStats } from '../types';

export function useAnalytics() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics'],
    queryFn: () => analyticsApi.getStats(),
    refetchInterval: 30000,
  });

  return {
    stats: data?.data?.data as AnalyticsStats | undefined,
    isLoading,
    error,
  };
}
