import { apiClient } from './client';
import type { User, UserCreateRequest, UserCreateResponse, UserUpdateRequest, UserStatus, UserRole } from '@/types';

export interface UsersListParams {
  status?: UserStatus;
  role?: UserRole;
  skip?: number;
  limit?: number;
}

// Backend response structure for /users list endpoint
interface UserListResponse {
  count: number;
  users: User[];
}

export const usersApi = {
  list: async (params?: UsersListParams): Promise<User[]> => {
    const response = await apiClient.get<UserListResponse>('/users', { params });
    return response.data.users;
  },

  getById: async (userId: number): Promise<User> => {
    const response = await apiClient.get<User>(`/users/${userId}`);
    return response.data;
  },

  create: async (data: UserCreateRequest): Promise<UserCreateResponse> => {
    const response = await apiClient.post<UserCreateResponse>('/users', data);
    return response.data;
  },

  update: async (userId: number, data: UserUpdateRequest): Promise<User> => {
    const response = await apiClient.patch<User>(`/users/${userId}`, data);
    return response.data;
  },

  block: async (userId: number): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>(`/users/${userId}/block`);
    return response.data;
  },

  unblock: async (userId: number): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>(`/users/${userId}/unblock`);
    return response.data;
  },

  deactivate: async (userId: number): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>(`/users/${userId}/deactivate`);
    return response.data;
  },

  resetPassword: async (userId: number): Promise<{ message: string; initial_password: string; email_sent: boolean }> => {
    const response = await apiClient.post<{ message: string; initial_password: string; email_sent: boolean }>(
      `/users/${userId}/reset-password`
    );
    return response.data;
  },
};
