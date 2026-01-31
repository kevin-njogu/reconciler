import { apiClient } from './client';
import type {
  AvailableGatewaysResponse,
  ReconciliationResult,
  ReconciliationSaveResponse,
} from '@/types';

export interface ReconcileParams {
  batch_id: string;
  gateway: string;
}

// Preview result type (dry run)
export interface ReconciliationPreviewResult {
  message: string;
  batch_id: string;
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
  };
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
   * Run reconciliation preview (dry run) without saving.
   * Returns insights for review before committing.
   */
  preview: async (params: ReconcileParams): Promise<ReconciliationPreviewResult> => {
    const response = await apiClient.post<ReconciliationPreviewResult>('/reconcile/preview', null, {
      params: {
        batch_id: params.batch_id,
        gateway: params.gateway,
      },
    });
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
