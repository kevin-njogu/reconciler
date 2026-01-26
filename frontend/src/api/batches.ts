import { apiClient } from './client';
import type {
  Batch,
  BatchStatus,
  BatchCreateResponse,
  BatchCloseResponse,
  BatchFilesResponse,
  BatchListResponse,
  BatchDeleteRequestResponse,
  BatchDeleteRequestListResponse,
  ReviewDeleteRequestBody,
} from '@/types';

export interface BatchListParams {
  status?: BatchStatus;
  page?: number;
  page_size?: number;
  search?: string;
}

interface BatchDetailResponse {
  batch_id: string;
  batch_db_id: number;
  status: string;
  description?: string;
  created_at: string;
  closed_at?: string;
  created_by?: string;
  created_by_id?: number;
  file_count: number;
  transaction_count: number;
  unreconciled_count: number;
}

export const batchesApi = {
  list: async (params?: BatchListParams): Promise<BatchListResponse> => {
    const response = await apiClient.get<{
      batches: Array<{
        batch_id: string;
        batch_db_id: number;
        status: string;
        description?: string;
        created_at: string;
        closed_at?: string;
        created_by?: string;
        created_by_id?: number;
        file_count: number;
      }>;
      pagination: {
        page: number;
        page_size: number;
        total_count: number;
        total_pages: number;
        has_next: boolean;
        has_previous: boolean;
      };
    }>('/batch', { params });

    return {
      batches: response.data.batches.map((b) => ({
        id: b.batch_db_id,
        batch_id: b.batch_id,
        status: b.status as BatchStatus,
        description: b.description,
        created_at: b.created_at,
        closed_at: b.closed_at,
        created_by: b.created_by,
        created_by_id: b.created_by_id,
        file_count: b.file_count,
      })),
      pagination: response.data.pagination,
    };
  },

  getById: async (batchId: string): Promise<Batch> => {
    const response = await apiClient.get<BatchDetailResponse>(`/batch/${batchId}`);
    return {
      id: response.data.batch_db_id,
      batch_id: response.data.batch_id,
      status: response.data.status as BatchStatus,
      description: response.data.description,
      created_at: response.data.created_at,
      closed_at: response.data.closed_at,
      created_by: response.data.created_by,
      created_by_id: response.data.created_by_id,
      file_count: response.data.file_count,
      transaction_count: response.data.transaction_count,
      unreconciled_count: response.data.unreconciled_count,
    };
  },

  create: async (description?: string): Promise<BatchCreateResponse> => {
    const response = await apiClient.post<BatchCreateResponse>('/batch', { description });
    return response.data;
  },

  close: async (batchId: string): Promise<BatchCloseResponse> => {
    const response = await apiClient.post<BatchCloseResponse>(`/batch/${batchId}/close`);
    return response.data;
  },

  // Delete request endpoints (maker-checker workflow)
  requestDelete: async (batchId: string, reason?: string): Promise<BatchDeleteRequestResponse> => {
    const response = await apiClient.post<BatchDeleteRequestResponse>(
      `/batch/${batchId}/delete-request`,
      { reason }
    );
    return response.data;
  },

  getDeleteRequests: async (status?: string): Promise<BatchDeleteRequestListResponse> => {
    const response = await apiClient.get<BatchDeleteRequestListResponse>(
      '/batch/delete-requests/list',
      { params: status ? { status } : undefined }
    );
    return response.data;
  },

  reviewDeleteRequest: async (
    requestId: number,
    body: ReviewDeleteRequestBody
  ): Promise<Record<string, unknown>> => {
    const response = await apiClient.post<Record<string, unknown>>(
      `/batch/delete-requests/${requestId}/review`,
      body
    );
    return response.data;
  },

  // File management endpoints
  getFiles: async (batchId: string): Promise<BatchFilesResponse> => {
    const response = await apiClient.get<BatchFilesResponse>(`/batch/${batchId}/files`);
    return response.data;
  },
};
