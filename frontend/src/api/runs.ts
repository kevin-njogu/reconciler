import { apiClient } from './client';
import type { RunListResponse, ReconciliationRun } from '@/types';

export interface RunListParams {
  gateway?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

export interface RunDetailResponse extends ReconciliationRun {
  transaction_count: number;
  unreconciled_count: number;
}

export const runsApi = {
  /**
   * List reconciliation runs with optional filters and pagination.
   */
  list: async (params: RunListParams = {}): Promise<RunListResponse> => {
    const response = await apiClient.get<RunListResponse>('/runs', { params });
    return response.data;
  },

  /**
   * Get details of a single reconciliation run.
   */
  getById: async (runId: string): Promise<RunDetailResponse> => {
    const response = await apiClient.get<RunDetailResponse>(`/runs/${runId}`);
    return response.data;
  },
};
