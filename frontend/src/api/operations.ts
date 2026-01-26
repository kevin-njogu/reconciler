import { apiClient } from './client';

// Types
export interface UnreconciledTransaction {
  id: number;
  gateway: string;
  transaction_type: string;
  date: string | null;
  transaction_id: string | null;
  narrative: string | null;
  debit: number | null;
  credit: number | null;
  amount: number | null;
  status: string | null;
  remarks: string | null;
  reconciliation_status: string | null;
  reconciliation_key: string | null;
  batch_id: string;
  is_manually_reconciled: string | null;
  manual_recon_note: string | null;
  manual_recon_by: number | null;
  manual_recon_by_username: string | null;
  manual_recon_at: string | null;
  authorization_status: string | null;
  authorized_by: number | null;
  authorized_by_username: string | null;
  authorized_at: string | null;
  authorization_note: string | null;
}

export interface UnreconciledResponse {
  batch_id: string;
  gateway_filter: string | null;
  available_gateways: string[];
  total_count: number;
  by_gateway: Record<string, UnreconciledTransaction[]>;
}

export interface PendingAuthorizationGroup {
  batch_id: string;
  gateway: string;
  transactions: UnreconciledTransaction[];
}

export interface PendingAuthorizationResponse {
  total_count: number;
  groups: PendingAuthorizationGroup[];
}

export interface ManualReconcileResponse {
  message: string;
  transaction: UnreconciledTransaction;
}

export interface AuthorizeResponse {
  message: string;
  transaction: UnreconciledTransaction;
}

export interface BulkAuthorizeResponse {
  message: string;
  action: string;
  count: number;
  transaction_ids: number[];
}

export interface BulkManualReconcileResponse {
  message: string;
  count: number;
  transaction_ids: number[];
}

// API Methods
export const operationsApi = {
  /**
   * Get unreconciled transactions for a batch
   */
  getUnreconciled: async (
    batchId: string,
    gateway?: string
  ): Promise<UnreconciledResponse> => {
    const params: Record<string, string> = { batch_id: batchId };
    if (gateway) {
      params.gateway = gateway;
    }
    const response = await apiClient.get<UnreconciledResponse>('/operations/unreconciled', {
      params,
    });
    return response.data;
  },

  /**
   * Get transactions pending authorization (admin only)
   */
  getPendingAuthorization: async (
    batchId?: string,
    gateway?: string
  ): Promise<PendingAuthorizationResponse> => {
    const params: Record<string, string> = {};
    if (batchId) {
      params.batch_id = batchId;
    }
    if (gateway) {
      params.gateway = gateway;
    }
    const response = await apiClient.get<PendingAuthorizationResponse>(
      '/operations/pending-authorization',
      { params }
    );
    return response.data;
  },

  /**
   * Manually reconcile a transaction
   */
  manualReconcile: async (
    transactionId: number,
    note: string
  ): Promise<ManualReconcileResponse> => {
    const response = await apiClient.post<ManualReconcileResponse>(
      `/operations/manual-reconcile/${transactionId}`,
      { note }
    );
    return response.data;
  },

  /**
   * Bulk manually reconcile transactions
   */
  manualReconcileBulk: async (
    transactionIds: number[],
    note: string
  ): Promise<BulkManualReconcileResponse> => {
    const response = await apiClient.post<BulkManualReconcileResponse>(
      '/operations/manual-reconcile-bulk',
      { transaction_ids: transactionIds, note }
    );
    return response.data;
  },

  /**
   * Authorize or reject a transaction (admin only)
   */
  authorize: async (
    transactionId: number,
    action: 'authorize' | 'reject',
    note?: string
  ): Promise<AuthorizeResponse> => {
    const response = await apiClient.post<AuthorizeResponse>(
      `/operations/authorize/${transactionId}`,
      { action, note }
    );
    return response.data;
  },

  /**
   * Bulk authorize or reject transactions (admin only)
   */
  authorizeBulk: async (
    transactionIds: number[],
    action: 'authorize' | 'reject',
    note?: string
  ): Promise<BulkAuthorizeResponse> => {
    const response = await apiClient.post<BulkAuthorizeResponse>('/operations/authorize-bulk', {
      transaction_ids: transactionIds,
      action,
      note,
    });
    return response.data;
  },
};
