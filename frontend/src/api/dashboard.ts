import { apiClient } from './client';

// Types
export interface GatewayTile {
  base_gateway: string;
  display_name: string;
  external_debit_count: number;
  internal_payout_count: number;
  unreconciled_count: number;
  matching_percentage: number;
}

export interface DashboardSummary {
  reconciliation_rate: number;
  pending_authorizations: number;
  unreconciled_count: number;
  unreconciled_amount: number;
}

export interface DashboardStats {
  gateway_tiles: GatewayTile[];
  summary: DashboardSummary;
}

// API Methods
export const dashboardApi = {
  getStats: async (): Promise<DashboardStats> => {
    const response = await apiClient.get<DashboardStats>('/dashboard/stats');
    return response.data;
  },
};
