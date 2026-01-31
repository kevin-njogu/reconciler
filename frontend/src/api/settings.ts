import { apiClient } from './client';

// =============================================================================
// Types
// =============================================================================

export interface DateFormat {
  id: number;
  format_string: string;
  display_name: string;
  example: string;
  is_default: boolean;
  is_active: boolean;
  created_at: string | null;
}

export interface Currency {
  id: number;
  code: string;
  name: string;
  symbol: string | null;
  country_id: number;
  is_default: boolean;
  is_active: boolean;
}

export interface Country {
  id: number;
  code: string;
  name: string;
  is_active: boolean;
  currencies: Currency[];
  created_at: string | null;
}

export interface ReconciliationKeyword {
  id: number;
  keyword: string;
  keyword_type: 'charge' | 'reversal';
  description: string | null;
  is_case_sensitive: boolean;
  is_active: boolean;
  gateway_id: number | null;
  gateway_name: string | null;
  created_at: string | null;
}

export interface SystemSetting {
  id: number;
  key: string;
  value: string | null;
  value_type: string;
  description: string | null;
  is_editable: boolean;
  updated_at: string | null;
}

export interface AllSettings {
  date_formats: DateFormat[];
  countries: Country[];
  keywords: {
    charge: ReconciliationKeyword[];
    reversal: ReconciliationKeyword[];
  };
  system_settings: SystemSetting[];
}

// =============================================================================
// Request Types
// =============================================================================

export interface DateFormatCreate {
  format_string: string;
  display_name: string;
  example: string;
  is_default?: boolean;
}

export interface DateFormatUpdate {
  format_string?: string;
  display_name?: string;
  example?: string;
  is_default?: boolean;
  is_active?: boolean;
}

export interface CountryCreate {
  code: string;
  name: string;
  currencies?: CurrencyCreate[];
}

export interface CountryUpdate {
  code?: string;
  name?: string;
  is_active?: boolean;
}

export interface CurrencyCreate {
  code: string;
  name: string;
  symbol?: string;
  is_default?: boolean;
}

export interface CurrencyUpdate {
  code?: string;
  name?: string;
  symbol?: string;
  is_default?: boolean;
  is_active?: boolean;
}

export interface KeywordCreate {
  keyword: string;
  keyword_type: 'charge' | 'reversal';
  description?: string;
  is_case_sensitive?: boolean;
  gateway_id?: number;
}

export interface KeywordUpdate {
  keyword?: string;
  keyword_type?: 'charge' | 'reversal';
  description?: string;
  is_case_sensitive?: boolean;
  is_active?: boolean;
  gateway_id?: number;
}

export interface KeywordBulkCreate {
  keyword_type: 'charge' | 'reversal';
  keywords: string[];
  gateway_id?: number;
}

export interface SystemSettingCreate {
  key: string;
  value?: string;
  value_type?: 'string' | 'number' | 'boolean' | 'json';
  description?: string;
  is_editable?: boolean;
}

// =============================================================================
// API Functions
// =============================================================================

export const settingsApi = {
  // Get all settings
  getAll: async (): Promise<AllSettings> => {
    const response = await apiClient.get('/settings');
    return response.data;
  },

  // Date Formats
  dateFormats: {
    list: async (includeInactive = false): Promise<DateFormat[]> => {
      const response = await apiClient.get('/settings/date-formats', {
        params: { include_inactive: includeInactive },
      });
      return response.data;
    },

    create: async (data: DateFormatCreate): Promise<DateFormat> => {
      const response = await apiClient.post('/settings/date-formats', data);
      return response.data;
    },

    update: async (id: number, data: DateFormatUpdate): Promise<DateFormat> => {
      const response = await apiClient.put(`/settings/date-formats/${id}`, data);
      return response.data;
    },

    delete: async (id: number): Promise<void> => {
      await apiClient.delete(`/settings/date-formats/${id}`);
    },
  },

  // Countries
  countries: {
    list: async (includeInactive = false): Promise<Country[]> => {
      const response = await apiClient.get('/settings/countries', {
        params: { include_inactive: includeInactive },
      });
      return response.data;
    },

    create: async (data: CountryCreate): Promise<Country> => {
      const response = await apiClient.post('/settings/countries', data);
      return response.data;
    },

    update: async (id: number, data: CountryUpdate): Promise<Country> => {
      const response = await apiClient.put(`/settings/countries/${id}`, data);
      return response.data;
    },

    delete: async (id: number): Promise<void> => {
      await apiClient.delete(`/settings/countries/${id}`);
    },

    addCurrency: async (countryId: number, data: CurrencyCreate): Promise<Currency> => {
      const response = await apiClient.post(`/settings/countries/${countryId}/currencies`, data);
      return response.data;
    },
  },

  // Currencies
  currencies: {
    update: async (id: number, data: CurrencyUpdate): Promise<Currency> => {
      const response = await apiClient.put(`/settings/currencies/${id}`, data);
      return response.data;
    },

    delete: async (id: number): Promise<void> => {
      await apiClient.delete(`/settings/currencies/${id}`);
    },
  },

  // Keywords
  keywords: {
    list: async (params?: {
      keyword_type?: string;
      gateway_id?: number;
      include_inactive?: boolean;
    }): Promise<ReconciliationKeyword[]> => {
      const response = await apiClient.get('/settings/keywords', { params });
      return response.data;
    },

    listGrouped: async (): Promise<{
      charge: ReconciliationKeyword[];
      reversal: ReconciliationKeyword[];
    }> => {
      const response = await apiClient.get('/settings/keywords/grouped');
      return response.data;
    },

    create: async (data: KeywordCreate): Promise<ReconciliationKeyword> => {
      const response = await apiClient.post('/settings/keywords', data);
      return response.data;
    },

    createBulk: async (data: KeywordBulkCreate): Promise<{
      message: string;
      created: string[];
      skipped: string[];
    }> => {
      const response = await apiClient.post('/settings/keywords/bulk', data);
      return response.data;
    },

    update: async (id: number, data: KeywordUpdate): Promise<ReconciliationKeyword> => {
      const response = await apiClient.put(`/settings/keywords/${id}`, data);
      return response.data;
    },

    delete: async (id: number): Promise<void> => {
      await apiClient.delete(`/settings/keywords/${id}`);
    },
  },

  // System Settings
  system: {
    list: async (): Promise<SystemSetting[]> => {
      const response = await apiClient.get('/settings/system');
      return response.data;
    },

    get: async (key: string): Promise<SystemSetting> => {
      const response = await apiClient.get(`/settings/system/${key}`);
      return response.data;
    },

    create: async (data: SystemSettingCreate): Promise<SystemSetting> => {
      const response = await apiClient.post('/settings/system', data);
      return response.data;
    },

    update: async (key: string, value: string): Promise<SystemSetting> => {
      const response = await apiClient.put(`/settings/system/${key}`, { value });
      return response.data;
    },

    delete: async (key: string): Promise<void> => {
      await apiClient.delete(`/settings/system/${key}`);
    },
  },

  // Seed defaults
  seedDefaults: async (): Promise<{
    message: string;
    created: {
      date_formats: number;
      countries: number;
      currencies: number;
      keywords: number;
    };
  }> => {
    const response = await apiClient.post('/settings/seed-defaults');
    return response.data;
  },
};
