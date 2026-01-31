import { apiClient } from './client';
import type {
  LoginRequest,
  LoginStep1Response,
  OTPVerifyRequest,
  OTPVerifyResponse,
  OTPResendRequest,
  OTPResendResponse,
  ForgotPasswordRequest,
  ForgotPasswordResponse,
  VerifyResetOTPRequest,
  VerifyResetOTPResponse,
  ResetPasswordRequest,
  ResetPasswordResponse,
  TokenRefreshResponse,
  PasswordChangeRequest,
  User,
  SuperAdminCreateRequest,
} from '@/types';

export const authApi = {
  // Step 1: Credentials verification → returns pre_auth_token + sends OTP
  login: async (data: LoginRequest): Promise<LoginStep1Response> => {
    const response = await apiClient.post<LoginStep1Response>('/auth/login', data);
    return response.data;
  },

  // Step 2: OTP verification → returns access + refresh tokens
  verifyOTP: async (data: OTPVerifyRequest): Promise<OTPVerifyResponse> => {
    const response = await apiClient.post<OTPVerifyResponse>('/auth/verify-otp', data);
    return response.data;
  },

  // Resend OTP (2-minute cooldown)
  resendOTP: async (data: OTPResendRequest): Promise<OTPResendResponse> => {
    const response = await apiClient.post<OTPResendResponse>('/auth/resend-otp', data);
    return response.data;
  },

  // Forgot password - request OTP
  forgotPassword: async (data: ForgotPasswordRequest): Promise<ForgotPasswordResponse> => {
    const response = await apiClient.post<ForgotPasswordResponse>('/auth/forgot-password', data);
    return response.data;
  },

  // Verify reset OTP → returns reset_token
  verifyResetOTP: async (data: VerifyResetOTPRequest): Promise<VerifyResetOTPResponse> => {
    const response = await apiClient.post<VerifyResetOTPResponse>('/auth/verify-reset-otp', data);
    return response.data;
  },

  // Reset password with reset_token
  resetPassword: async (data: ResetPasswordRequest): Promise<ResetPasswordResponse> => {
    const response = await apiClient.post<ResetPasswordResponse>('/auth/reset-password', data);
    return response.data;
  },

  refresh: async (refreshToken: string): Promise<TokenRefreshResponse> => {
    const response = await apiClient.post<TokenRefreshResponse>('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  logout: async (refreshToken: string): Promise<void> => {
    await apiClient.post('/auth/logout', { refresh_token: refreshToken });
  },

  changePassword: async (data: PasswordChangeRequest): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>('/auth/change-password', data);
    return response.data;
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get<User>('/auth/me');
    return response.data;
  },

  createSuperAdmin: async (data: SuperAdminCreateRequest): Promise<User> => {
    const response = await apiClient.post<User>('/users/create-super-admin', data);
    return response.data;
  },
};
