import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '@/types';
import { tokenStorage } from '@/api/client';
import { authApi } from '@/api/auth';

type LoginStep = 'credentials' | 'otp';
type OTPSource = 'email' | 'welcome_email';

interface AuthState {
  // Persisted state
  user: User | null;
  isAuthenticated: boolean;
  mustChangePassword: boolean;

  // Transient state
  isLoading: boolean;
  loginStep: LoginStep;
  preAuthToken: string | null;
  otpExpiresIn: number;
  otpSource: OTPSource | null;
  resendAvailableIn: number;
  loginEmail: string | null;

  // Actions
  login: (username: string, password: string) => Promise<void>;
  verifyOTP: (otpCode: string) => Promise<void>;
  resendOTP: () => Promise<void>;
  cancelLogin: () => void;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
  setUser: (user: User | null) => void;
  setMustChangePassword: (value: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Persisted
      user: null,
      isAuthenticated: false,
      mustChangePassword: false,

      // Transient
      isLoading: true,
      loginStep: 'credentials' as LoginStep,
      preAuthToken: null,
      otpExpiresIn: 0,
      otpSource: null,
      resendAvailableIn: 0,
      loginEmail: null,

      // Step 1: Credentials → pre_auth_token + OTP sent
      login: async (username: string, password: string) => {
        const response = await authApi.login({ username, password });
        set({
          loginStep: 'otp',
          preAuthToken: response.pre_auth_token,
          otpExpiresIn: response.otp_expires_in,
          otpSource: response.otp_source,
          resendAvailableIn: response.resend_available_in,
          loginEmail: username,
        });
      },

      // Step 2: OTP verification → tokens + authenticated
      verifyOTP: async (otpCode: string) => {
        const { preAuthToken } = get();
        if (!preAuthToken) throw new Error('No pre-auth token available');

        const response = await authApi.verifyOTP({
          pre_auth_token: preAuthToken,
          otp_code: otpCode,
        });

        tokenStorage.setTokens(response.access_token, response.refresh_token);
        set({
          user: response.user,
          isAuthenticated: true,
          mustChangePassword: response.must_change_password,
          loginStep: 'credentials',
          preAuthToken: null,
          otpExpiresIn: 0,
          otpSource: null,
          resendAvailableIn: 0,
          loginEmail: null,
        });
      },

      // Resend OTP (2-minute cooldown)
      resendOTP: async () => {
        const { preAuthToken } = get();
        if (!preAuthToken) throw new Error('No pre-auth token available');

        const response = await authApi.resendOTP({
          pre_auth_token: preAuthToken,
        });

        set({
          otpExpiresIn: response.otp_expires_in,
          resendAvailableIn: response.resend_available_in,
        });
      },

      // Cancel OTP step → back to credentials
      cancelLogin: () => {
        set({
          loginStep: 'credentials',
          preAuthToken: null,
          otpExpiresIn: 0,
          otpSource: null,
          resendAvailableIn: 0,
          loginEmail: null,
        });
      },

      logout: async () => {
        const refreshToken = tokenStorage.getRefreshToken();
        if (refreshToken) {
          try {
            await authApi.logout(refreshToken);
          } catch {
            // Ignore logout errors
          }
        }
        tokenStorage.clearTokens();
        set({
          user: null,
          isAuthenticated: false,
          mustChangePassword: false,
          loginStep: 'credentials',
          preAuthToken: null,
          otpExpiresIn: 0,
          otpSource: null,
          resendAvailableIn: 0,
          loginEmail: null,
        });
      },

      checkAuth: async () => {
        const token = tokenStorage.getAccessToken();
        if (!token) {
          set({ isLoading: false, isAuthenticated: false, user: null });
          return;
        }

        try {
          const user = await authApi.getCurrentUser();
          set({ user, isAuthenticated: true, isLoading: false });
        } catch {
          tokenStorage.clearTokens();
          set({ user: null, isAuthenticated: false, isLoading: false });
        }
      },

      setUser: (user: User | null) => {
        set({ user, isAuthenticated: !!user });
      },

      setMustChangePassword: (value: boolean) => {
        set({ mustChangePassword: value });
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        mustChangePassword: state.mustChangePassword,
      }),
    }
  )
);

// Helper hooks
export const useUser = () => useAuthStore((state) => state.user);
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
export const useIsAdmin = () => {
  const user = useAuthStore((state) => state.user);
  return user?.role === 'admin' || user?.role === 'super_admin';
};
export const useIsSuperAdmin = () => {
  const user = useAuthStore((state) => state.user);
  return user?.role === 'super_admin';
};
export const useIsAdminOnly = () => {
  const user = useAuthStore((state) => state.user);
  return user?.role === 'admin';
};
export const useIsUserRole = () => {
  const user = useAuthStore((state) => state.user);
  return user?.role === 'user';
};
export const useUserRole = () => {
  const user = useAuthStore((state) => state.user);
  return user?.role;
};
