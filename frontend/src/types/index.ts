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

// --- 2-Step Login Types ---

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginStep1Response {
  pre_auth_token: string;
  otp_sent: boolean;
  otp_expires_in: number;
  otp_source: 'email' | 'welcome_email';
  resend_available_in: number;
  message: string;
}

export interface OTPVerifyRequest {
  pre_auth_token: string;
  otp_code: string;
}

export interface OTPVerifyResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  must_change_password: boolean;
  user: User;
}

export interface OTPResendRequest {
  pre_auth_token: string;
}

export interface OTPResendResponse {
  otp_sent: boolean;
  otp_expires_in: number;
  resend_available_in: number;
  message: string;
}

// --- Forgot Password Types ---

export interface ForgotPasswordRequest {
  email: string;
}

export interface ForgotPasswordResponse {
  message: string;
}

export interface VerifyResetOTPRequest {
  email: string;
  otp_code: string;
}

export interface VerifyResetOTPResponse {
  reset_token: string;
  expires_in: number;
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

// =============================================================================
// Unified Gateway Types (New)
// =============================================================================

export type FileConfigType = 'external' | 'internal';

export interface GatewayFileConfig {
  id: number;
  gateway_id: number;
  config_type: FileConfigType;
  name: string;
  filename_prefix?: string;
  expected_filetypes: string[];
  header_row_config: Record<string, number>;
  end_of_data_signal?: string;
  date_format?: {
    id: number;
    format_string: string;
    example: string;
  };
  charge_keywords: string[];
  column_mapping?: Record<string, string[]>;
  is_active: boolean;
}

export interface UnifiedGateway {
  id: number;
  display_name: string;
  description?: string;
  country?: {
    id: number;
    code: string;
    name: string;
  };
  currency?: {
    id: number;
    code: string;
    name: string;
    symbol?: string;
  };
  is_active: boolean;
  external_config?: GatewayFileConfig;
  internal_config?: GatewayFileConfig;
  created_at?: string;
  updated_at?: string;
}

export interface GatewayFileConfigCreate {
  config_type: FileConfigType;
  name: string;
  filename_prefix?: string;
  expected_filetypes?: string[];
  header_row_config?: Record<string, number>;
  end_of_data_signal?: string;
  date_format_id?: number;
  charge_keywords?: string[];
  column_mapping?: Record<string, string[]>;
}

export interface GatewayFileConfigUpdate {
  name?: string;
  filename_prefix?: string;
  expected_filetypes?: string[];
  header_row_config?: Record<string, number>;
  end_of_data_signal?: string;
  date_format_id?: number;
  charge_keywords?: string[];
  column_mapping?: Record<string, string[]>;
  is_active?: boolean;
}

export interface UnifiedGatewayCreate {
  display_name: string;
  description?: string;
  country_id?: number;
  currency_id?: number;
  external_config: GatewayFileConfigCreate;
  internal_config: GatewayFileConfigCreate;
}

export interface UnifiedGatewayUpdate {
  display_name?: string;
  description?: string;
  country_id?: number;
  currency_id?: number;
  external_config?: GatewayFileConfigUpdate;
  internal_config?: GatewayFileConfigUpdate;
  is_active?: boolean;
}

export interface UnifiedGatewayListResponse {
  gateways: UnifiedGateway[];
  total_count: number;
}

export interface UnifiedGatewayChangeRequest {
  id: number;
  request_type: ChangeRequestType;
  status: ChangeRequestStatus;
  gateway_id?: number;
  display_name: string;
  proposed_changes: Record<string, unknown>;
  requested_by_id: number;
  requested_by_name?: string;
  created_at: string;
  reviewed_by_id?: number;
  reviewed_by_name?: string;
  reviewed_at?: string;
  rejection_reason?: string;
}

export interface UnifiedGatewayChangeRequestCreate {
  request_type: ChangeRequestType;
  display_name: string;
  proposed_changes: Record<string, unknown>;
}

export interface UnifiedGatewayChangeRequestListResponse {
  count: number;
  requests: UnifiedGatewayChangeRequest[];
}

// Transaction Types
export type TransactionType = 'deposit' | 'debit' | 'charge' | 'payout' | 'refund';
export type ReconciliationStatus = 'reconciled' | 'unreconciled';
export type ReconciliationCategory = 'reconcilable' | 'auto_reconciled' | 'non_reconcilable';
// Note: GatewayType is already defined above in Gateway Types section

/**
 * Unified transaction model.
 * Uses the unified template format: Date, Reference, Details, Debit, Credit
 *
 * Enhanced discriminators:
 * - gateway_type: 'external' or 'internal'
 * - reconciliation_category: determines reconciliation behavior
 */
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
