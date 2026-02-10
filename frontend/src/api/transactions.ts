import { apiClient } from './client';

// Types
export interface TransactionRecord {
  id: number;
  date: string | null;
  transaction_id: string | null;
  reconciliation_key: string | null;
  run_id: string | null;
  gateway: string | null;
  amount: number | null;
  reconciliation_status: string | null;
  transaction_type: string | null;
}

export interface TransactionPagination {
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface TransactionListResponse {
  transactions: TransactionRecord[];
  pagination: TransactionPagination;
}

export interface TransactionFilters {
  page?: number;
  page_size?: number;
  search?: string;
  gateway?: string;
  run_id?: string;
  date_from?: string;
  date_to?: string;
  reconciliation_status?: string;
  transaction_type?: string;
}

export interface FilterOptions {
  gateways: string[];
  run_ids: string[];
  reconciliation_statuses: string[];
  transaction_types: string[];
}

// API Methods
export const transactionsApi = {
  /**
   * List transactions with pagination and filters
   */
  list: async (filters: TransactionFilters = {}): Promise<TransactionListResponse> => {
    const params: Record<string, string | number> = {};

    if (filters.page) params.page = filters.page;
    if (filters.page_size) params.page_size = filters.page_size;
    if (filters.search) params.search = filters.search;
    if (filters.gateway) params.gateway = filters.gateway;
    if (filters.run_id) params.run_id = filters.run_id;
    if (filters.date_from) params.date_from = filters.date_from;
    if (filters.date_to) params.date_to = filters.date_to;
    if (filters.reconciliation_status) params.reconciliation_status = filters.reconciliation_status;
    if (filters.transaction_type) params.transaction_type = filters.transaction_type;

    const response = await apiClient.get<TransactionListResponse>('/transactions', { params });
    return response.data;
  },

  /**
   * Get filter options (unique values for dropdowns)
   */
  getFilterOptions: async (): Promise<FilterOptions> => {
    const response = await apiClient.get<FilterOptions>('/transactions/filters');
    return response.data;
  },

  /**
   * Get a single transaction by ID
   */
  get: async (id: number): Promise<TransactionRecord> => {
    const response = await apiClient.get<TransactionRecord>(`/transactions/${id}`);
    return response.data;
  },
};
