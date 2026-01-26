// User & Auth Types
export type UserRole = 'super_admin' | 'admin' | 'user';
export type UserStatus = 'active' | 'blocked' | 'deactivated';

export interface User {
  id: number;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  role: UserRole;
  status: UserStatus;
  must_change_password: boolean;
  created_by_id?: number;
  created_at: string;
  updated_at: string;
  last_login_at?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  must_change_password: boolean;
  user: User;
}

export interface TokenRefreshResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
}

export interface UserCreateRequest {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
  role: UserRole;
}

export interface UserUpdateRequest {
  email?: string;
  role?: UserRole;
}

export interface SuperAdminCreateRequest {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
  secret_key: string;
}

// Batch Types
export type BatchStatus = 'pending' | 'completed';
export type DeleteRequestStatus = 'pending' | 'approved' | 'rejected';

export interface Batch {
  id: number;
  batch_id: string;
  status: BatchStatus;
  description?: string;
  created_at: string;
  closed_at?: string;
  created_by?: string;
  created_by_id?: number;
  file_count?: number;
  transaction_count?: number;
  unreconciled_count?: number;
}

export interface BatchCreateResponse {
  batch_id: string;
  batch_db_id: number;
  status: BatchStatus;
  description?: string;
  created_by: string;
  created_at: string;
  message: string;
}

export interface BatchCloseResponse {
  batch_id: string;
  status: BatchStatus;
  closed_at: string;
  message: string;
}

export interface BatchDeleteRequestCreate {
  reason?: string;
}

export interface BatchDeleteRequest {
  id: number;
  batch_id: string;
  status: DeleteRequestStatus;
  reason?: string;
  requested_by?: string;
  requested_by_id: number;
  reviewed_by?: string;
  reviewed_at?: string;
  rejection_reason?: string;
  created_at: string;
}

export interface BatchDeleteRequestResponse {
  id: number;
  batch_id: string;
  status: string;
  reason?: string;
  requested_by: string;
  created_at: string;
  message: string;
}

export interface BatchDeleteRequestListResponse {
  count: number;
  requests: BatchDeleteRequest[];
}

export interface ReviewDeleteRequestBody {
  approved: boolean;
  rejection_reason?: string;
}

export interface BatchFile {
  id: number;
  filename: string;
  original_filename: string;
  gateway: string;
  file_size?: number;
  content_type?: string;
  uploaded_at: string;
  uploaded_by?: string;
}

export interface BatchFilesResponse {
  batch_id: string;
  batch_status: BatchStatus;
  file_count: number;
  files: BatchFile[];
}

export interface PaginationInfo {
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface BatchListResponse {
  batches: Batch[];
  pagination: PaginationInfo;
}

// Gateway Types
export type GatewayType = 'external' | 'internal';
export type ChangeRequestType = 'create' | 'update' | 'delete' | 'activate' | 'permanent_delete';
export type ChangeRequestStatus = 'pending' | 'approved' | 'rejected';

export interface GatewayConfig {
  id: number;
  name: string;
  gateway_type: GatewayType;
  display_name: string;
  country: string;
  currency: string;
  date_format: string;
  charge_keywords: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface GatewayCreateRequest {
  name: string;
  gateway_type: GatewayType;
  display_name: string;
  country: string;
  currency: string;
  date_format?: string;
  charge_keywords?: string[];
}

export interface GatewayUpdateRequest {
  display_name?: string;
  country?: string;
  currency?: string;
  date_format?: string;
  charge_keywords?: string[];
  is_active?: boolean;
}

// Gateway Options Types (for dropdowns)
export interface CountryOption {
  code: string;
  name: string;
}

export interface CurrencyOption {
  code: string;
  name: string;
}

export interface DateFormatOption {
  format: string;
  example: string;
}

export interface GatewayOptions {
  countries: CountryOption[];
  currencies: CurrencyOption[];
  date_formats: DateFormatOption[];
}

export interface GatewayInfo {
  external_gateways: GatewayConfig[];
  internal_gateways: GatewayConfig[];
  upload_mappings: Record<string, string[]>;
}

export interface GatewayListItem {
  gateway: string;
  display_name: string;
  upload_name: string;
  internal_upload_name: string;
  charge_keywords: string[];
}

// Gateway Change Request Types
export interface GatewayChangeRequestCreate {
  request_type: ChangeRequestType;
  gateway_name: string;
  proposed_changes: Record<string, unknown>;
}

export interface GatewayChangeRequestReview {
  approved: boolean;
  rejection_reason?: string;
}

export interface GatewayChangeRequest {
  id: number;
  request_type: ChangeRequestType;
  status: ChangeRequestStatus;
  gateway_id?: number;
  gateway_name: string;
  proposed_changes: Record<string, unknown>;
  requested_by_id: number;
  requested_by_name?: string;
  created_at: string;
  reviewed_by_id?: number;
  reviewed_by_name?: string;
  reviewed_at?: string;
  rejection_reason?: string;
}

export interface GatewayChangeRequestListResponse {
  count: number;
  requests: GatewayChangeRequest[];
}

// Transaction Types
export type TransactionType = 'credit' | 'debit' | 'charge' | 'payout';
export type ReconciliationStatus = 'reconciled' | 'unreconciled';

/**
 * Unified transaction model.
 * Uses the unified template format: Date, Reference, Details, Debit, Credit
 */
export interface Transaction {
  id: number;
  gateway: string;
  transaction_type: TransactionType;
  date: string;
  transaction_id: string;
  narrative: string;
  debit?: number;
  credit?: number;
  reconciliation_status: ReconciliationStatus;
  batch_id: string;
  created_at: string;
}

// Reconciliation Types

// Available gateway info for reconciliation dropdown
export interface AvailableGateway {
  gateway: string;
  display_name: string;
  has_external: boolean;
  has_internal: boolean;
  external_file: string | null;
  internal_file: string | null;
  ready_for_reconciliation: boolean;
  error: string | null;
}

export interface AvailableGatewaysResponse {
  batch_id: string;
  available_gateways: AvailableGateway[];
}

// New reconciliation result format
export interface ReconciliationResult {
  message: string;
  batch_id: string;
  gateway: string;
  summary: {
    total_external: number;
    total_internal: number;
    matched: number;
    unmatched_external: number;
    unmatched_internal: number;
    credits: number;
    charges: number;
  };
  saved: {
    external_records: number;
    internal_records: number;
    total: number;
  };
}

// Legacy types for backwards compatibility
export interface ReconciliationSummary {
  batch_id: string;
  external_gateway: string;
  internal_gateway: string;
  total_external_debits: number;
  total_internal_records: number;
  matched: number;
  unmatched_external: number;
  unmatched_internal: number;
  total_credits: number;
  total_charges: number;
}

export interface ReconciliationSaveResponse {
  message: string;
  batch_id: string;
  external_gateway: string;
  internal_gateway: string;
  saved: {
    credits: number;
    debits: number;
    charges: number;
    internal: number;
    total: number;
  };
}

// File Upload Types
export interface FileUploadResponse {
  message: string;
  filename: string;
  batch_id: string;
}

// API Response Types
export interface ApiError {
  detail: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}
