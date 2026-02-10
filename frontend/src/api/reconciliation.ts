import { apiClient } from './client';
import type {
  AvailableGatewaysResponse,
  ReconciliationResult,
} from '@/types';

// Preview result type (dry run)
export interface ReconciliationPreviewResult {
  message: string;
  gateway: string;
  is_preview: boolean;
  summary: {
    total_external: number;
    total_internal: number;
    matched: number;
    unmatched_external: number;
    unmatched_internal: number;
    deposits: number;
    charges: number;
    carry_forward_matched?: number;
    carry_forward_reclassified_charges?: number;
  };
  insights: {
    total_external: number;
    total_internal: number;
    matched: number;
    match_rate: number;
    unreconciled_external: number;
    unreconciled_internal: number;
    deposits: number;
    charges: number;
    carry_forward_matched?: number;
    carry_forward_reclassified_charges?: number;
  };
}

export const reconciliationApi = {
  /**
   * Get gateways that have files uploaded and are ready for reconciliation.
   */
  getReadyGateways: async (): Promise<AvailableGatewaysResponse> => {
    const response = await apiClient.get<AvailableGatewaysResponse>(
      '/reconcile/available-gateways'
    );
    return response.data;
  },

  /**
   * Run reconciliation preview (dry run) without saving.
   * Returns insights for review before committing.
   */
  preview: async (gateway: string): Promise<ReconciliationPreviewResult> => {
    const response = await apiClient.post<ReconciliationPreviewResult>('/reconcile/preview', null, {
      params: { gateway },
    });
    return response.data;
  },

  /**
   * Run reconciliation for a gateway.
   * Auto-creates a reconciliation run and saves results.
   */
  reconcile: async (gateway: string): Promise<ReconciliationResult> => {
    const response = await apiClient.post<ReconciliationResult>('/reconcile', null, {
      params: { gateway },
    });
    return response.data;
  },
};
