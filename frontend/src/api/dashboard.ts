import { apiClient } from './client';

// Types
export interface CountAmount {
  count: number;
  amount: number;
}

export interface GatewayTile {
  base_gateway: string;
  display_name: string;
  external_debit_count: number;
  internal_debit_count: number;
  reconciled_debit_count: number;
  unreconciled_count: number;
  matching_percentage: number;
}

export interface DashboardSummary {
  total_reconciled: number;
  total_unreconciled: number;
  reconciliation_rate: number;
  manually_reconciled: number;
}

export interface DashboardStats {
  latest_batch_id: string | null;
  gateway_tiles: GatewayTile[];
  batch_charges: CountAmount;
  pending_authorizations: number;
  summary: DashboardSummary;
}

// API Methods
export const dashboardApi = {
  /**
   * Get dashboard statistics with optional filters
   */
  getStats: async (batchId?: string, gateway?: string): Promise<DashboardStats> => {
    const params: Record<string, string> = {};
    if (batchId) {
      params.batch_id = batchId;
    }
    if (gateway) {
      params.gateway = gateway;
    }
    const response = await apiClient.get<DashboardStats>('/dashboard/stats', { params });
    return response.data;
  },
};
