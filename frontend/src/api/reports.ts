import { apiClient } from './client';

export type ReportFormat = 'xlsx' | 'csv';

export interface AvailableGateway {
  gateway: string;
  display_name: string;
  transaction_count: number;
}

export interface AvailableGatewaysResponse {
  gateways: AvailableGateway[];
  count: number;
}

export interface ReportRun {
  run_id: string;
  gateway: string;
  matched: number;
  unmatched_external: number;
  unmatched_internal: number;
  created_at: string | null;
}

export interface RunsResponse {
  runs: ReportRun[];
  count: number;
}

export const reportsApi = {
  /**
   * Get gateways that have transactions in the database.
   */
  getAvailableGateways: async (): Promise<AvailableGatewaysResponse> => {
    const response = await apiClient.get<AvailableGatewaysResponse>('/reports/available-gateways');
    return response.data;
  },

  /**
   * Get reconciliation runs for report drill-down.
   */
  getRuns: async (gateway?: string, limit: number = 20): Promise<RunsResponse> => {
    const params: Record<string, string | number> = {};
    if (gateway) params.gateway = gateway;
    if (limit) params.limit = limit;

    const response = await apiClient.get<RunsResponse>('/reports/runs', { params });
    return response.data;
  },

  /**
   * Download reconciliation report.
   * Gateway is required. Optional: date range and run_id for filtering.
   */
  downloadReport: async (
    gateway: string,
    format: ReportFormat = 'xlsx',
    dateFrom?: string,
    dateTo?: string,
    runId?: string
  ): Promise<Blob> => {
    const params: Record<string, string> = { gateway, format };
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    if (runId) params.run_id = runId;

    const response = await apiClient.get('/reports/download', {
      params,
      responseType: 'blob',
    });
    return response.data;
  },
};
