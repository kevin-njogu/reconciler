// User & Auth Types
export type UserRole = 'super_admin' | 'admin' | 'user';
export type UserStatus = 'active' | 'blocked' | 'deactivated';

export interface User {
  id: number;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  mobile_number?: string;
  role: UserRole;
  status: UserStatus;
  must_change_password: boolean;
  created_by_id?: number;
  created_at: string;
  updated_at: string;
  last_login_at?: string;
  password_changed_at?: string;
}

// --- Login Types ---

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

// --- Forgot Password Types ---

export interface ForgotPasswordRequest {
  email: string;
}

export interface ForgotPasswordResponse {
  message: string;
}

export interface ResetPasswordRequest {
  reset_token: string;
  new_password: string;
}

export interface ResetPasswordResponse {
  message: string;
}

// --- Token & Auth Types ---

export interface TokenRefreshResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
}

// --- User Management Types ---

export interface UserCreateRequest {
  first_name: string;
  last_name: string;
  email: string;
  mobile_number?: string;
  role: UserRole;
}

export interface UserCreateResponse {
  user: User;
  initial_password: string;
  welcome_email_sent: boolean;
  message: string;
}

export interface UserUpdateRequest {
  email?: string;
  mobile_number?: string;
  role?: UserRole;
}

export interface SuperAdminCreateRequest {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
}

// Reconciliation Run Types (replaces Batch)
export interface ReconciliationRun {
  id: number;
  run_id: string;
  gateway: string;
  status: string;
  total_external: number;
  total_internal: number;
  matched: number;
  unmatched_external: number;
  unmatched_internal: number;
  carry_forward_matched: number;
  created_by?: string;
  created_at: string;
}

export interface PaginationInfo {
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface RunListResponse {
  runs: ReconciliationRun[];
  pagination: PaginationInfo;
}

// Uploaded File Types (replaces BatchFile)
export interface UploadedFile {
  id: number;
  filename: string;
  original_filename: string;
  gateway: string;
  gateway_type: string;
  file_size?: number;
  content_type?: string;
  uploaded_by?: string;
  uploaded_at: string;
  is_processed: boolean;
}

// =============================================================================
// Gateway Types
// =============================================================================

export type FileConfigType = 'external' | 'internal';
export type ChangeRequestType = 'create' | 'update' | 'delete' | 'activate' | 'permanent_delete';
export type ChangeRequestStatus = 'pending' | 'approved' | 'rejected';

export interface GatewayFileConfig {
  id: number;
  gateway_id: number;
  config_type: FileConfigType;
  name: string;
  expected_filetypes: string[];
  header_row_config: Record<string, number>;
  end_of_data_signal?: string;
  date_format?: string;
  charge_keywords: string[];
  column_mapping?: Record<string, string[]>;
  is_active: boolean;
}

export interface UnifiedGateway {
  id: number;
  display_name: string;
  description?: string;
  country?: string;
  currency_code?: string;
  is_active: boolean;
  external_config?: GatewayFileConfig;
  internal_config?: GatewayFileConfig;
  created_at?: string;
  updated_at?: string;
}

export interface GatewayFileConfigCreate {
  config_type: FileConfigType;
  name: string;
  expected_filetypes?: string[];
  header_row_config?: Record<string, number>;
  end_of_data_signal?: string;
  date_format?: string;
  charge_keywords?: string[];
  column_mapping?: Record<string, string[]>;
}

export interface GatewayFileConfigUpdate {
  name?: string;
  expected_filetypes?: string[];
  header_row_config?: Record<string, number>;
  end_of_data_signal?: string;
  date_format?: string;
  charge_keywords?: string[];
  column_mapping?: Record<string, string[]>;
  is_active?: boolean;
}

export interface UnifiedGatewayCreate {
  display_name: string;
  description?: string;
  country?: string;
  currency_code?: string;
  external_config: GatewayFileConfigCreate;
  internal_config: GatewayFileConfigCreate;
}

export interface UnifiedGatewayUpdate {
  display_name?: string;
  description?: string;
  country?: string;
  currency_code?: string;
  external_config?: GatewayFileConfigUpdate;
  internal_config?: GatewayFileConfigUpdate;
  is_active?: boolean;
}

export interface UnifiedGatewayListResponse {
  gateways: UnifiedGateway[];
  total_count: number;
}

export interface GatewayChangeRequestReview {
  approved: boolean;
  rejection_reason?: string;
}

export interface GatewayChangeRequest {
  id: number;
  request_type: ChangeRequestType;
  status: ChangeRequestStatus;
  unified_gateway_id?: number;
  gateway_display_name: string;
  proposed_changes: Record<string, unknown>;
  requested_by_id: number;
  requested_by_name?: string;
  created_at: string;
  reviewed_by_id?: number;
  reviewed_by_name?: string;
  reviewed_at?: string;
  rejection_reason?: string;
}

export interface GatewayChangeRequestCreate {
  request_type: ChangeRequestType;
  display_name: string;
  proposed_changes: Record<string, unknown>;
}

export interface GatewayChangeRequestListResponse {
  count: number;
  requests: GatewayChangeRequest[];
  page: number;
  page_size: number;
  total_pages: number;
}

// Transaction Types
export type GatewayType = 'external' | 'internal';
export type TransactionType = 'deposit' | 'debit' | 'charge' | 'payout' | 'refund';
export type ReconciliationStatus = 'reconciled' | 'unreconciled';
export type ReconciliationCategory = 'reconcilable' | 'auto_reconciled' | 'non_reconcilable';

export interface Transaction {
  id: number;
  gateway: string;
  gateway_type?: GatewayType;
  transaction_type: TransactionType;
  reconciliation_category?: ReconciliationCategory;
  date: string;
  transaction_id: string;
  narrative: string;
  debit?: number;
  credit?: number;
  reconciliation_status: ReconciliationStatus;
  run_id?: string;
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
  available_gateways: AvailableGateway[];
}

// Reconciliation result format
export interface ReconciliationResult {
  message: string;
  run_id: string;
  gateway: string;
  summary: {
    total_external: number;
    total_internal: number;
    matched: number;
    unmatched_external: number;
    unmatched_internal: number;
    credits: number;
    charges: number;
    carry_forward_matched?: number;
  };
  saved: {
    external_records: number;
    internal_records: number;
    total: number;
  };
}

// File Upload Types
export interface FileUploadResponse {
  message: string;
  gateway: string;
  filename: string;
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
