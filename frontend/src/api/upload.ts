import { apiClient } from './client';
import type { UploadedFile } from '@/types';

// Response for single file upload (legacy/template mode)
export interface FileUploadResponse {
  message: string;
  gateway: string;
  upload_gateway: string;
  filename: string;
  original_filename: string;
  file_size: number;
  uploaded_by: string;
}

// Response for transform upload (raw file transformation)
export interface TransformUploadResponse extends FileUploadResponse {
  transformation: {
    success: boolean;
    row_count: number;
    column_mapping_used: Record<string, string>;
    unmapped_columns: string[];
    warnings: string[];
  };
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

// Response for file deletion
export interface FileDeleteResponse {
  message: string;
  gateway: string;
  filename: string;
}

// Response for file listing
export interface FileListResponse {
  gateway?: string;
  file_count: number;
  files: UploadedFile[];
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
   * Upload a single file for a gateway.
   * File is renamed to {gateway_name}.{ext} and stored in:
   * {external_gateway}/{gateway_name}.{ext}
   *
   * @param transform - If true, transforms raw file using gateway column mapping
   */
  uploadFile: async (
    gatewayName: string,
    file: File,
    transform: boolean = false
  ): Promise<FileUploadResponse | TransformUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<FileUploadResponse | TransformUploadResponse>(
      '/upload/file',
      formData,
      {
        params: { gateway_name: gatewayName, transform },
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  /**
   * Delete an uploaded file.
   */
  deleteFile: async (
    filename: string,
    gateway: string
  ): Promise<FileDeleteResponse> => {
    const response = await apiClient.delete<FileDeleteResponse>('/upload/file', {
      params: { filename, gateway },
    });
    return response.data;
  },

  /**
   * Download an uploaded file.
   */
  downloadFile: async (
    filename: string,
    gateway: string
  ): Promise<Blob> => {
    const response = await apiClient.get('/upload/file/download', {
      params: { filename, gateway },
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * List uploaded files, optionally filtered by gateway.
   */
  listFiles: async (gateway?: string): Promise<FileListResponse> => {
    const params: Record<string, string> = {};
    if (gateway) params.gateway = gateway;

    const response = await apiClient.get<FileListResponse>('/upload/files', { params });
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
