import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '@/types';
import { tokenStorage } from '@/api/client';
import { authApi } from '@/api/auth';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  mustChangePassword: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
  setUser: (user: User | null) => void;
  setMustChangePassword: (value: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      isLoading: true,
      mustChangePassword: false,

      login: async (username: string, password: string) => {
        const response = await authApi.login({ username, password });
        tokenStorage.setTokens(response.access_token, response.refresh_token);
        set({
          user: response.user,
          isAuthenticated: true,
          mustChangePassword: response.must_change_password,
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
        set({ user: null, isAuthenticated: false, mustChangePassword: false });
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
