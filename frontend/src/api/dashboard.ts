import { apiClient } from './client';

// Types
export interface DashboardBatch {
  batch_id: string;
  status: string;
}

export interface DashboardFilters {
  batch_id: string | null;
  gateway: string | null;
  available_batches: DashboardBatch[];
  available_gateways: string[];
}

export interface CountAmount {
  count: number;
  amount: number;
}

export interface WalletTopups {
  count: number;
  total_amount: number;
}

export interface ReconciledData {
  external: CountAmount;
  internal: CountAmount;
}

export interface UnreconciledData {
  external: CountAmount;
  internal: CountAmount;
}

export interface AdditionalInsights {
  total_payouts: number;
  reconciliation_rate: number;
  credits: CountAmount;
  charges: CountAmount;
  pending_authorizations: number;
  manually_reconciled: number;
}

export interface GatewayBreakdown {
  gateway: string;
  total_count: number;
  reconciled_count: number;
  unreconciled_count: number;
  total_debit: number;
  total_credit: number;
  total_amount: number;
}

export interface DashboardStats {
  filters: DashboardFilters;
  wallet_topups: WalletTopups;
  reconciled: ReconciledData;
  unreconciled: UnreconciledData;
  additional_insights: AdditionalInsights;
  gateway_breakdown: GatewayBreakdown[];
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
