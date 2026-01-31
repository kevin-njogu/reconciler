import { apiClient } from './client';

export type ReportFormat = 'xlsx' | 'csv';

export interface ReportBatch {
  batch_id: string;
  batch_db_id: number;
  status: string;
  description?: string;
  created_at: string;
  closed_at?: string;
  created_by?: string;
}

export interface BatchesResponse {
  batches: ReportBatch[];
  count: number;
}

// Legacy alias for backwards compatibility
export type ClosedBatch = ReportBatch;
export type ClosedBatchesResponse = BatchesResponse;

export interface AvailableGateway {
  gateway: string;
  display_name: string;
  transaction_count: number;
}

export interface AvailableGatewaysResponse {
  gateways: AvailableGateway[];
  count: number;
}

export const reportsApi = {
  /**
   * Get batches for report generation.
   * Returns latest 5 by default, supports search by batch ID and status filter.
   */
  getBatches: async (
    search?: string,
    limit: number = 5,
    status?: 'pending' | 'completed' | 'all'
  ): Promise<BatchesResponse> => {
    const response = await apiClient.get<BatchesResponse>('/reports/batches', {
      params: { search, limit, status },
    });
    return response.data;
  },

  /**
   * Get closed batches for report generation (legacy endpoint).
   * Returns latest 5 by default, supports search by batch ID.
   */
  getClosedBatches: async (search?: string, limit: number = 5): Promise<BatchesResponse> => {
    const response = await apiClient.get<BatchesResponse>('/reports/closed-batches', {
      params: { search, limit },
    });
    return response.data;
  },

  /**
   * Get available gateways for a specific batch.
   * Only returns gateways that have transactions in the batch.
   */
  getAvailableGateways: async (batchId: string): Promise<AvailableGatewaysResponse> => {
    const response = await apiClient.get<AvailableGatewaysResponse>('/reports/available-gateways', {
      params: { batch_id: batchId },
    });
    return response.data;
  },

  /**
   * Download reconciliation report for a batch and gateway.
   * Both batch_id and gateway are required. Supports XLSX and CSV formats.
   */
  downloadReport: async (
    batchId: string,
    gateway: string,
    format: ReportFormat = 'xlsx'
  ): Promise<Blob> => {
    const response = await apiClient.get('/reports/download/batch', {
      params: { batch_id: batchId, gateway, format },
      responseType: 'blob',
    });
    return response.data;
  },

  // Legacy endpoints (kept for backwards compatibility)
  downloadGatewayReport: async (gateway: string, batchId: string): Promise<Blob> => {
    const response = await apiClient.get(`/reports/download/${gateway}`, {
      params: { batch_id: batchId },
      responseType: 'blob',
    });
    return response.data;
  },

  downloadFullReport: async (batchId: string): Promise<Blob> => {
    const response = await apiClient.get('/reports/download', {
      params: { batch_id: batchId },
      responseType: 'blob',
    });
    return response.data;
  },
};
