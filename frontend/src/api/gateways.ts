import { apiClient } from './client';
import type {
  GatewayConfig,
  GatewayCreateRequest,
  GatewayUpdateRequest,
  GatewayInfo,
  GatewayListItem,
  GatewayType,
  GatewayChangeRequestCreate,
  GatewayChangeRequestReview,
  GatewayChangeRequest,
  GatewayChangeRequestListResponse,
  ChangeRequestStatus,
  GatewayOptions,
  // Unified gateway types
  UnifiedGateway,
  UnifiedGatewayListResponse,
  UnifiedGatewayChangeRequest,
  UnifiedGatewayChangeRequestCreate,
  UnifiedGatewayChangeRequestListResponse,
} from '@/types';

export interface GatewayListParams {
  gateway_type?: GatewayType;
  include_inactive?: boolean;
}


export const gatewaysApi = {
  // Get dropdown options for gateway configuration forms
  getOptions: async (): Promise<GatewayOptions> => {
    const response = await apiClient.get<GatewayOptions>('/gateway-config/options');
    return response.data;
  },

  // Get gateway configs from database for accurate display names
  getGateways: async (): Promise<GatewayListItem[]> => {
    // Fetch from gateway-config endpoint which has database display names
    const response = await apiClient.get<GatewayConfig[]>('/gateway-config/', {
      params: { gateway_type: 'external', include_inactive: false },
    });

    // Transform to GatewayListItem format
    return response.data.map((config) => ({
      gateway: config.name,
      display_name: config.display_name,
      upload_name: config.name,
      internal_upload_name: `workpay_${config.name}`,
      charge_keywords: config.charge_keywords || [],
    }));
  },

  // Gateway config endpoints
  list: async (params?: GatewayListParams): Promise<GatewayConfig[]> => {
    const response = await apiClient.get<GatewayConfig[]>('/gateway-config/', { params });
    return response.data;
  },

  getInfo: async (): Promise<GatewayInfo> => {
    const response = await apiClient.get<GatewayInfo>('/gateway-config/info');
    return response.data;
  },

  getByName: async (gatewayName: string): Promise<GatewayConfig> => {
    const response = await apiClient.get<GatewayConfig>(`/gateway-config/${gatewayName}`);
    return response.data;
  },

  create: async (data: GatewayCreateRequest): Promise<GatewayConfig> => {
    const response = await apiClient.post<GatewayConfig>('/gateway-config', data);
    return response.data;
  },

  update: async (gatewayName: string, data: GatewayUpdateRequest): Promise<GatewayConfig> => {
    const response = await apiClient.put<GatewayConfig>(`/gateway-config/${gatewayName}`, data);
    return response.data;
  },

  delete: async (gatewayName: string, permanent: boolean = false): Promise<{ message: string }> => {
    const response = await apiClient.delete<{ message: string }>(`/gateway-config/${gatewayName}`, {
      params: { permanent },
    });
    return response.data;
  },

  activate: async (gatewayName: string): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>(`/gateway-config/${gatewayName}/activate`);
    return response.data;
  },

  seedDefaults: async (): Promise<{ message: string; seeded_count: number }> => {
    const response = await apiClient.post<{ message: string; seeded_count: number }>(
      '/gateway-config/seed-defaults'
    );
    return response.data;
  },

  getUploadNames: async (gatewayName: string): Promise<{
    gateway: string;
    external_upload_name: string;
    internal_upload_names: string[];
  }> => {
    const response = await apiClient.get<{
      gateway: string;
      external_upload_name: string;
      internal_upload_names: string[];
    }>(
      `/gateway-config/upload-names/${gatewayName}`
    );
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
  getPendingChangeRequests: async (): Promise<GatewayChangeRequestListResponse> => {
    const response = await apiClient.get<GatewayChangeRequestListResponse>('/gateway-config/change-requests/pending');
    return response.data;
  },

  getAllChangeRequests: async (status?: ChangeRequestStatus): Promise<GatewayChangeRequestListResponse> => {
    const response = await apiClient.get<GatewayChangeRequestListResponse>('/gateway-config/change-requests/all', {
      params: status ? { status } : undefined,
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

  // ==========================================================================
  // Unified Gateway endpoints (new)
  // ==========================================================================
  unified: {
    // List all unified gateways
    list: async (includeInactive = false): Promise<UnifiedGatewayListResponse> => {
      const response = await apiClient.get<UnifiedGatewayListResponse>('/gateway-config/unified/list', {
        params: { include_inactive: includeInactive },
      });
      return response.data;
    },

    // Get a single unified gateway by ID
    get: async (gatewayId: number): Promise<UnifiedGateway> => {
      const response = await apiClient.get<UnifiedGateway>(`/gateway-config/unified/${gatewayId}`);
      return response.data;
    },

    // Create a change request for a unified gateway
    createChangeRequest: async (data: UnifiedGatewayChangeRequestCreate): Promise<UnifiedGatewayChangeRequest> => {
      const response = await apiClient.post<UnifiedGatewayChangeRequest>(
        '/gateway-config/unified/change-request',
        data
      );
      return response.data;
    },

    // Get pending change requests for unified gateways (admin only)
    getPendingChangeRequests: async (): Promise<UnifiedGatewayChangeRequestListResponse> => {
      const response = await apiClient.get<UnifiedGatewayChangeRequestListResponse>(
        '/gateway-config/unified/change-requests/pending'
      );
      return response.data;
    },

    // Review a unified gateway change request (admin only)
    reviewChangeRequest: async (
      requestId: number,
      review: GatewayChangeRequestReview
    ): Promise<UnifiedGatewayChangeRequest> => {
      const response = await apiClient.post<UnifiedGatewayChangeRequest>(
        `/gateway-config/unified/change-requests/${requestId}/review`,
        review
      );
      return response.data;
    },
  },
};
