import { apiClient } from './client';
import type {
  UnifiedGateway,
  UnifiedGatewayListResponse,
  GatewayChangeRequest,
  GatewayChangeRequestCreate,
  GatewayChangeRequestReview,
  GatewayChangeRequestListResponse,
  ChangeRequestStatus,
} from '@/types';


export const gatewaysApi = {
  // List all gateways
  list: async (includeInactive = false): Promise<UnifiedGatewayListResponse> => {
    const response = await apiClient.get<UnifiedGatewayListResponse>('/gateway-config/', {
      params: { include_inactive: includeInactive },
    });
    return response.data;
  },

  // Get a single gateway by ID
  get: async (gatewayId: number): Promise<UnifiedGateway> => {
    const response = await apiClient.get<UnifiedGateway>(`/gateway-config/${gatewayId}`);
    return response.data;
  },

  // Change Request endpoints (for user role)
  createChangeRequest: async (data: GatewayChangeRequestCreate): Promise<GatewayChangeRequest> => {
    const response = await apiClient.post<GatewayChangeRequest>('/gateway-config/change-request', data);
    return response.data;
  },

  getMyChangeRequests: async (status?: ChangeRequestStatus): Promise<GatewayChangeRequestListResponse> => {
    const response = await apiClient.get<GatewayChangeRequestListResponse>('/gateway-config/change-requests/my', {
      params: status ? { status } : undefined,
    });
    return response.data;
  },

  getChangeRequest: async (requestId: number): Promise<GatewayChangeRequest> => {
    const response = await apiClient.get<GatewayChangeRequest>(`/gateway-config/change-requests/${requestId}`);
    return response.data;
  },

  // Admin approval endpoints
  getPendingChangeRequests: async (page = 1, pageSize = 20): Promise<GatewayChangeRequestListResponse> => {
    const response = await apiClient.get<GatewayChangeRequestListResponse>('/gateway-config/change-requests/pending', {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },

  getAllChangeRequests: async (status?: ChangeRequestStatus, page = 1, pageSize = 20): Promise<GatewayChangeRequestListResponse> => {
    const response = await apiClient.get<GatewayChangeRequestListResponse>('/gateway-config/change-requests/all', {
      params: { ...(status ? { status } : {}), page, page_size: pageSize },
    });
    return response.data;
  },

  reviewChangeRequest: async (requestId: number, review: GatewayChangeRequestReview): Promise<GatewayChangeRequest> => {
    const response = await apiClient.post<GatewayChangeRequest>(
      `/gateway-config/change-requests/${requestId}/review`,
      review
    );
    return response.data;
  },
};
