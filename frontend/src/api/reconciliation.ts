import { apiClient } from './client';
import type {
  AvailableGatewaysResponse,
  ReconciliationResult,
  ReconciliationSummary,
  ReconciliationSaveResponse,
} from '@/types';

export interface ReconcileParams {
  batch_id: string;
  gateway: string;
}

// Legacy params for backwards compatibility
export interface ReconciliationParams {
  batch_id: string;
  external_gateway: string;
  internal_gateway?: string;
}

export const reconciliationApi = {
  /**
   * Get gateways that have files uploaded for a batch.
   * Returns gateway status for reconciliation readiness.
   */
  getAvailableGateways: async (batchId: string): Promise<AvailableGatewaysResponse> => {
    const response = await apiClient.get<AvailableGatewaysResponse>(
      `/reconcile/available-gateways/${batchId}`
    );
    return response.data;
  },

  /**
   * Run reconciliation for a batch and gateway.
   * This validates, reconciles, and saves in a single operation.
   */
  reconcile: async (params: ReconcileParams): Promise<ReconciliationResult> => {
    const response = await apiClient.post<ReconciliationResult>('/reconcile', null, {
      params: {
        batch_id: params.batch_id,
        gateway: params.gateway,
      },
    });
    return response.data;
  },

  // Legacy methods for backwards compatibility

  /**
   * @deprecated Use reconcile() instead
   */
  preview: async (params: ReconciliationParams): Promise<ReconciliationSummary> => {
    const response = await apiClient.post<ReconciliationSummary>('/reconcile', null, {
      params: {
        batch_id: params.batch_id,
        gateway: params.external_gateway,
      },
    });
    // Transform new response to legacy format
    const data = response.data as unknown as ReconciliationResult;
    return {
      batch_id: data.batch_id,
      external_gateway: data.gateway,
      internal_gateway: `workpay_${data.gateway}`,
      total_external_debits: data.summary?.total_external || 0,
      total_internal_records: data.summary?.total_internal || 0,
      matched: data.summary?.matched || 0,
      unmatched_external: data.summary?.unmatched_external || 0,
      unmatched_internal: data.summary?.unmatched_internal || 0,
      total_credits: data.summary?.credits || 0,
      total_charges: data.summary?.charges || 0,
    };
  },

  /**
   * @deprecated Use reconcile() instead
   */
  save: async (params: ReconciliationParams): Promise<ReconciliationSaveResponse> => {
    const response = await apiClient.post<ReconciliationResult>('/reconcile', null, {
      params: {
        batch_id: params.batch_id,
        gateway: params.external_gateway,
      },
    });
    // Transform new response to legacy format
    const data = response.data;
    return {
      message: data.message,
      batch_id: data.batch_id,
      external_gateway: data.gateway,
      internal_gateway: `workpay_${data.gateway}`,
      saved: {
        credits: data.summary?.credits || 0,
        debits: data.summary?.total_external - (data.summary?.credits || 0) - (data.summary?.charges || 0),
        charges: data.summary?.charges || 0,
        internal: data.saved?.internal_records || 0,
        total: data.saved?.total || 0,
      },
    };
  },
};
