import { apiClient } from './client';
import type { BatchFilesResponse } from '@/types';

// Response for single file upload
export interface FileUploadResponse {
  message: string;
  batch_id: string;
  gateway: string;
  upload_gateway: string;
  filename: string;
  original_filename: string;
  file_size: number;
  uploaded_by: string;
}

// Response for file validation
export interface FileValidationResponse {
  valid: boolean;
  filename: string;
  file_size: number;
  required_columns: string[];
  found_columns: string[];
  missing_columns: string[];
  message: string;
}

// Response for pending batches
export interface PendingBatch {
  batch_id: string;
  description?: string;
  created_at?: string;
}

export interface PendingBatchesResponse {
  batches: PendingBatch[];
}

// Response for file deletion
export interface FileDeleteResponse {
  message: string;
  batch_id: string;
  gateway: string;
  filename: string;
}

// Template column info response
export interface TemplateColumnInfo {
  name: string;
  description: string;
  format: string;
  mandatory: boolean;
  example: string;
}

export interface TemplateInfoResponse {
  columns: TemplateColumnInfo[];
  date_format: string;
  supported_formats: string[];
  notes: string[];
}

export const uploadApi = {
  /**
   * Get current user's pending batches for the upload batch dropdown.
   */
  getPendingBatches: async (): Promise<PendingBatchesResponse> => {
    const response = await apiClient.get<PendingBatchesResponse>('/upload/pending-batches');
    return response.data;
  },

  /**
   * Upload a single file to a batch's gateway subdirectory.
   * File is renamed to {gateway_name}.{ext} and stored in:
   * {batch_id}/{external_gateway}/{gateway_name}.{ext}
   */
  uploadFile: async (
    batchId: string,
    gatewayName: string,
    file: File
  ): Promise<FileUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<FileUploadResponse>('/upload/file', formData, {
      params: { batch_id: batchId, gateway_name: gatewayName },
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * Delete an uploaded file from a batch.
   */
  deleteFile: async (
    batchId: string,
    filename: string,
    gateway: string
  ): Promise<FileDeleteResponse> => {
    const response = await apiClient.delete<FileDeleteResponse>('/upload/file', {
      params: { batch_id: batchId, filename, gateway },
    });
    return response.data;
  },

  /**
   * Download an uploaded file from a batch.
   */
  downloadFile: async (
    batchId: string,
    filename: string,
    gateway: string
  ): Promise<Blob> => {
    const response = await apiClient.get('/upload/file/download', {
      params: { batch_id: batchId, filename, gateway },
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * List all uploaded files for a batch.
   */
  listFiles: async (batchId: string): Promise<BatchFilesResponse> => {
    const response = await apiClient.get<BatchFilesResponse>('/upload/files', {
      params: { batch_id: batchId },
    });
    return response.data;
  },

  /**
   * Download unified template for file uploads.
   * Columns: Date, Reference, Details, Debit, Credit
   */
  downloadTemplate: async (format: 'xlsx' | 'csv' = 'xlsx'): Promise<Blob> => {
    const response = await apiClient.get('/upload/template', {
      params: { format },
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * Get template column information for the download popup.
   */
  getTemplateInfo: async (): Promise<TemplateInfoResponse> => {
    const response = await apiClient.get<TemplateInfoResponse>('/upload/template-info');
    return response.data;
  },

  /**
   * Validate file columns before upload.
   */
  validateFile: async (file: File): Promise<FileValidationResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<FileValidationResponse>('/upload/validate', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};
