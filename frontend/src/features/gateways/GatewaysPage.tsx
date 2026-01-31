import { useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plus,
  MoreVertical,
  Edit2,
  Power,
  Clock,
  CheckCircle,
  XCircle,
  Eye,
  Trash2,
  ChevronDown,
  ChevronUp,
  FileText,
  Server,
} from 'lucide-react';
import { gatewaysApi, settingsApi, getErrorMessage } from '@/api';
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  TableEmpty,
  Badge,
  PageLoading,
  Alert,
  Modal,
  ModalFooter,
  Input,
  Select,
  CompactPagination,
} from '@/components/ui';
import { useToast } from '@/hooks/useToast';
import { formatDateTime } from '@/lib/utils';
import type { UnifiedGateway, ChangeRequestType, ChangeRequestStatus } from '@/types';

const PAGE_SIZE = 8;

// Custom hook for pagination
function usePagination<T>(items: T[], pageSize: number = PAGE_SIZE) {
  const [currentPage, setCurrentPage] = useState(1);

  const totalPages = Math.ceil(items.length / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const paginatedItems = items.slice(startIndex, startIndex + pageSize);

  if (currentPage > totalPages && totalPages > 0) {
    setCurrentPage(1);
  }

  return {
    currentPage,
    setCurrentPage,
    totalPages,
    paginatedItems,
    totalItems: items.length,
    pageSize,
  };
}

const STATUS_VARIANTS: Record<ChangeRequestStatus, 'warning' | 'success' | 'danger'> = {
  pending: 'warning',
  approved: 'success',
  rejected: 'danger',
};

const DEFAULT_FILETYPES = ['xlsx', 'xls', 'csv'];

// Template columns for column mapping
const TEMPLATE_COLUMNS = ['Date', 'Reference', 'Details', 'Debit', 'Credit'] as const;

interface FileConfigFormData {
  name: string;
  filename_prefix: string;
  expected_filetypes: string[];
  header_row_xlsx: number;
  header_row_xls: number;
  header_row_csv: number;
  end_of_data_signal: string;
  date_format_id: number | null;
  column_mapping: Record<string, string>; // Template column -> comma-separated raw column names
}

interface GatewayFormData {
  display_name: string;
  description: string;
  country_id: number | null;
  currency_id: number | null;
  external_config: FileConfigFormData;
  internal_config: FileConfigFormData;
}

const initialFileConfig: FileConfigFormData = {
  name: '',
  filename_prefix: '',
  expected_filetypes: [...DEFAULT_FILETYPES],
  header_row_xlsx: 0,
  header_row_xls: 0,
  header_row_csv: 0,
  end_of_data_signal: '',
  date_format_id: null,
  column_mapping: {
    Date: '',
    Reference: '',
    Details: '',
    Debit: '',
    Credit: '',
  },
};

const initialFormData: GatewayFormData = {
  display_name: '',
  description: '',
  country_id: null,
  currency_id: null,
  external_config: { ...initialFileConfig },
  internal_config: { ...initialFileConfig },
};

export function GatewaysPage() {
  const toast = useToast();
  const queryClient = useQueryClient();

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isRequestsModalOpen, setIsRequestsModalOpen] = useState(false);
  const [isDeleteConfirmModalOpen, setIsDeleteConfirmModalOpen] = useState(false);
  const [selectedGateway, setSelectedGateway] = useState<UnifiedGateway | null>(null);
  const [gatewayToDelete, setGatewayToDelete] = useState<UnifiedGateway | null>(null);
  const [activeDropdown, setActiveDropdown] = useState<number | null>(null);
  const [dropdownPosition, setDropdownPosition] = useState<{ top: number; left: number } | null>(
    null
  );
  const dropdownButtonRefs = useRef<Record<number, HTMLButtonElement | null>>({});

  // Section collapse state for form
  const [externalExpanded, setExternalExpanded] = useState(true);
  const [internalExpanded, setInternalExpanded] = useState(true);

  // Form state
  const [formData, setFormData] = useState<GatewayFormData>({ ...initialFormData });

  // Fetch unified gateways
  const {
    data: gatewaysData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['unified-gateways', { include_inactive: true }],
    queryFn: () => gatewaysApi.unified.list(true),
    staleTime: 0, // Always refetch to get latest data after admin approval
    refetchOnWindowFocus: true, // Refetch when user returns to tab
  });

  // Fetch settings for dropdowns
  const { data: allSettings } = useQuery({
    queryKey: ['all-settings'],
    queryFn: () => settingsApi.getAll(),
  });

  // Fetch my change requests (legacy + unified)
  const { data: myRequestsData } = useQuery({
    queryKey: ['my-gateway-requests'],
    queryFn: () => gatewaysApi.getMyChangeRequests(),
    staleTime: 0, // Always refetch to get latest approval status
    refetchOnWindowFocus: true, // Refetch when user returns to tab
  });

  // Create change request mutation
  const createRequestMutation = useMutation({
    mutationFn: gatewaysApi.unified.createChangeRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-gateway-requests'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['unified-gateways'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['gateway-change-requests'], refetchType: 'all' });
      toast.success('Change request submitted for approval');
      setIsCreateModalOpen(false);
      resetForm();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  // Update change request mutation
  const updateRequestMutation = useMutation({
    mutationFn: gatewaysApi.unified.createChangeRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-gateway-requests'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['unified-gateways'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['gateway-change-requests'], refetchType: 'all' });
      toast.success('Update request submitted for approval');
      setIsEditModalOpen(false);
      setSelectedGateway(null);
      resetForm();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  // Delete/Deactivate change request mutation
  const deleteRequestMutation = useMutation({
    mutationFn: gatewaysApi.unified.createChangeRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-gateway-requests'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['unified-gateways'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['gateway-change-requests'], refetchType: 'all' });
      toast.success('Request submitted for approval');
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const gateways = gatewaysData?.gateways || [];
  const pagination = usePagination(gateways);

  const resetForm = () => {
    setFormData({ ...initialFormData });
    setExternalExpanded(true);
    setInternalExpanded(true);
  };

  const updateFileConfig = (
    configType: 'external_config' | 'internal_config',
    field: keyof FileConfigFormData,
    value: string | number | string[] | null
  ) => {
    setFormData((prev) => ({
      ...prev,
      [configType]: {
        ...prev[configType],
        [field]: value,
      },
    }));
  };

  const toggleFiletype = (configType: 'external_config' | 'internal_config', filetype: string) => {
    setFormData((prev) => {
      const currentTypes = prev[configType].expected_filetypes;
      const newTypes = currentTypes.includes(filetype)
        ? currentTypes.filter((t) => t !== filetype)
        : [...currentTypes, filetype];
      return {
        ...prev,
        [configType]: {
          ...prev[configType],
          expected_filetypes: newTypes.length > 0 ? newTypes : [filetype], // At least one required
        },
      };
    });
  };

  // Helper to convert column_mapping from form format (comma-separated string) to API format (string[])
  const columnMappingToApi = (
    formMapping: Record<string, string>
  ): Record<string, string[]> | null => {
    const result: Record<string, string[]> = {};
    let hasMapping = false;

    for (const col of TEMPLATE_COLUMNS) {
      const value = formMapping[col]?.trim();
      if (value) {
        result[col] = value.split(',').map((s) => s.trim()).filter(Boolean);
        if (result[col].length > 0) hasMapping = true;
      }
    }

    return hasMapping ? result : null;
  };

  const buildProposedChanges = () => {
    return {
      display_name: formData.display_name,
      description: formData.description || null,
      country_id: formData.country_id,
      currency_id: formData.currency_id,
      external_config: {
        config_type: 'external',
        name: formData.external_config.name,
        filename_prefix: formData.external_config.filename_prefix || null,
        expected_filetypes: formData.external_config.expected_filetypes,
        header_row_config: {
          xlsx: formData.external_config.header_row_xlsx,
          xls: formData.external_config.header_row_xls,
          csv: formData.external_config.header_row_csv,
        },
        end_of_data_signal: formData.external_config.end_of_data_signal || null,
        date_format_id: formData.external_config.date_format_id,
        column_mapping: columnMappingToApi(formData.external_config.column_mapping),
      },
      internal_config: {
        config_type: 'internal',
        name: formData.internal_config.name,
        filename_prefix: formData.internal_config.filename_prefix || null,
        expected_filetypes: formData.internal_config.expected_filetypes,
        header_row_config: {
          xlsx: formData.internal_config.header_row_xlsx,
          xls: formData.internal_config.header_row_xls,
          csv: formData.internal_config.header_row_csv,
        },
        end_of_data_signal: formData.internal_config.end_of_data_signal || null,
        date_format_id: formData.internal_config.date_format_id,
        column_mapping: columnMappingToApi(formData.internal_config.column_mapping),
      },
    };
  };

  const handleCreateRequest = () => {
    // Validate required fields
    if (!formData.display_name) {
      toast.error('Display name is required');
      return;
    }
    if (!formData.external_config.name) {
      toast.error('External config name is required');
      return;
    }
    if (!formData.internal_config.name) {
      toast.error('Internal config name is required');
      return;
    }
    if (!formData.internal_config.name.startsWith('workpay_')) {
      toast.error("Internal config name must start with 'workpay_'");
      return;
    }

    createRequestMutation.mutate({
      request_type: 'create' as ChangeRequestType,
      display_name: formData.display_name,
      proposed_changes: buildProposedChanges(),
    });
  };

  const handleUpdateRequest = () => {
    if (!selectedGateway) return;

    updateRequestMutation.mutate({
      request_type: 'update' as ChangeRequestType,
      display_name: selectedGateway.display_name,
      proposed_changes: buildProposedChanges(),
    });
  };

  const handleDeactivateRequest = (gateway: UnifiedGateway) => {
    deleteRequestMutation.mutate({
      request_type: 'delete' as ChangeRequestType,
      display_name: gateway.display_name,
      proposed_changes: {},
    });
    setActiveDropdown(null);
  };

  const handleActivateRequest = (gateway: UnifiedGateway) => {
    deleteRequestMutation.mutate({
      request_type: 'activate' as ChangeRequestType,
      display_name: gateway.display_name,
      proposed_changes: {},
    });
    setActiveDropdown(null);
  };

  const handlePermanentDeleteRequest = (gateway: UnifiedGateway) => {
    setGatewayToDelete(gateway);
    setIsDeleteConfirmModalOpen(true);
    setActiveDropdown(null);
  };

  const confirmPermanentDelete = () => {
    if (!gatewayToDelete) return;
    deleteRequestMutation.mutate({
      request_type: 'permanent_delete' as ChangeRequestType,
      display_name: gatewayToDelete.display_name,
      proposed_changes: {},
    });
    setIsDeleteConfirmModalOpen(false);
    setGatewayToDelete(null);
  };

  // Helper to convert column_mapping from API format (string[]) to form format (comma-separated string)
  const columnMappingToForm = (
    apiMapping: Record<string, string[]> | undefined
  ): Record<string, string> => {
    const result: Record<string, string> = {
      Date: '',
      Reference: '',
      Details: '',
      Debit: '',
      Credit: '',
    };
    if (apiMapping) {
      for (const col of TEMPLATE_COLUMNS) {
        result[col] = apiMapping[col]?.join(', ') || '';
      }
    }
    return result;
  };

  const openEditModal = (gateway: UnifiedGateway) => {
    setSelectedGateway(gateway);

    const extConfig = gateway.external_config;
    const intConfig = gateway.internal_config;

    setFormData({
      display_name: gateway.display_name,
      description: gateway.description || '',
      country_id: gateway.country?.id || null,
      currency_id: gateway.currency?.id || null,
      external_config: {
        name: extConfig?.name || '',
        filename_prefix: extConfig?.filename_prefix || '',
        expected_filetypes: extConfig?.expected_filetypes || [...DEFAULT_FILETYPES],
        header_row_xlsx: extConfig?.header_row_config?.xlsx ?? 0,
        header_row_xls: extConfig?.header_row_config?.xls ?? 0,
        header_row_csv: extConfig?.header_row_config?.csv ?? 0,
        end_of_data_signal: extConfig?.end_of_data_signal || '',
        date_format_id: extConfig?.date_format?.id || null,
        column_mapping: columnMappingToForm(extConfig?.column_mapping),
      },
      internal_config: {
        name: intConfig?.name || '',
        filename_prefix: intConfig?.filename_prefix || '',
        expected_filetypes: intConfig?.expected_filetypes || [...DEFAULT_FILETYPES],
        header_row_xlsx: intConfig?.header_row_config?.xlsx ?? 0,
        header_row_xls: intConfig?.header_row_config?.xls ?? 0,
        header_row_csv: intConfig?.header_row_config?.csv ?? 0,
        end_of_data_signal: intConfig?.end_of_data_signal || '',
        date_format_id: intConfig?.date_format?.id || null,
        column_mapping: columnMappingToForm(intConfig?.column_mapping),
      },
    });
    setIsEditModalOpen(true);
    setActiveDropdown(null);
  };

  const pendingRequests = myRequestsData?.requests.filter((r) => r.status === 'pending') || [];

  const handleDropdownToggle = (gatewayId: number) => {
    if (activeDropdown === gatewayId) {
      setActiveDropdown(null);
      setDropdownPosition(null);
    } else {
      const buttonEl = dropdownButtonRefs.current[gatewayId];
      if (buttonEl) {
        const rect = buttonEl.getBoundingClientRect();
        setDropdownPosition({
          top: rect.top - 8,
          left: rect.right - 192,
        });
      }
      setActiveDropdown(gatewayId);
    }
  };

  const closeDropdown = () => {
    setActiveDropdown(null);
    setDropdownPosition(null);
  };

  const renderDropdownMenu = (gateway: UnifiedGateway) => {
    if (activeDropdown !== gateway.id || !dropdownPosition) return null;

    return createPortal(
      <>
        <div className="fixed inset-0 z-[100]" onClick={closeDropdown} />
        <div
          className="fixed z-[101] w-48 rounded-lg bg-white py-1 shadow-lg ring-1 ring-black/5"
          style={{
            top: dropdownPosition.top,
            left: dropdownPosition.left,
            transform: 'translateY(-100%)',
          }}
        >
          <button
            onClick={() => {
              openEditModal(gateway);
              closeDropdown();
            }}
            className="flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
          >
            <Edit2 className="h-4 w-4" />
            Edit
          </button>
          <div className="my-1 border-t border-gray-100" />
          {gateway.is_active ? (
            <button
              onClick={() => {
                handleDeactivateRequest(gateway);
                closeDropdown();
              }}
              className="flex w-full items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50"
            >
              <Power className="h-4 w-4" />
              Deactivate
            </button>
          ) : (
            <>
              <button
                onClick={() => {
                  handleActivateRequest(gateway);
                  closeDropdown();
                }}
                className="flex w-full items-center gap-2 px-4 py-2 text-sm text-green-600 hover:bg-green-50"
              >
                <Power className="h-4 w-4" />
                Activate
              </button>
              <button
                onClick={() => handlePermanentDeleteRequest(gateway)}
                className="flex w-full items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50"
              >
                <Trash2 className="h-4 w-4" />
                Delete
              </button>
            </>
          )}
        </div>
      </>,
      document.body
    );
  };

  // Get currencies for selected country
  const selectedCountry = allSettings?.countries.find((c) => c.id === formData.country_id);
  const availableCurrencies = selectedCountry?.currencies || [];

  // File config section component
  const renderFileConfigSection = (
    configType: 'external_config' | 'internal_config',
    title: string,
    icon: React.ReactNode,
    expanded: boolean,
    setExpanded: (v: boolean) => void
  ) => {
    const config = formData[configType];

    return (
      <div className="rounded-lg border border-gray-200">
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="flex w-full items-center justify-between bg-gray-50 px-4 py-3"
        >
          <div className="flex items-center gap-2">
            {icon}
            <span className="font-medium text-gray-900">{title}</span>
          </div>
          {expanded ? (
            <ChevronUp className="h-5 w-5 text-gray-500" />
          ) : (
            <ChevronDown className="h-5 w-5 text-gray-500" />
          )}
        </button>

        {expanded && (
          <div className="space-y-4 p-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Config Name <span className="text-red-500">*</span>
                </label>
                <Input
                  value={config.name}
                  onChange={(e) =>
                    updateFileConfig(configType, 'name', e.target.value.toLowerCase())
                  }
                  placeholder={
                    configType === 'external_config' ? 'e.g., equity' : 'e.g., workpay_equity'
                  }
                  helperText={
                    configType === 'internal_config' ? "Must start with 'workpay_'" : 'Lowercase'
                  }
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Filename Prefix
                </label>
                <Input
                  value={config.filename_prefix}
                  onChange={(e) => updateFileConfig(configType, 'filename_prefix', e.target.value)}
                  placeholder="e.g., Account_Statement"
                  helperText="Prefix to match uploaded files"
                />
              </div>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">
                Expected File Types
              </label>
              <div className="flex gap-4">
                {['xlsx', 'xls', 'csv'].map((ft) => (
                  <label key={ft} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={config.expected_filetypes.includes(ft)}
                      onChange={() => toggleFiletype(configType, ft)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700">.{ft}</span>
                  </label>
                ))}
              </div>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">
                Header Row Skip (per file type)
              </label>
              <div className="grid grid-cols-3 gap-4">
                {config.expected_filetypes.includes('xlsx') && (
                  <Input
                    type="number"
                    min={0}
                    value={config.header_row_xlsx}
                    onChange={(e) =>
                      updateFileConfig(configType, 'header_row_xlsx', parseInt(e.target.value) || 0)
                    }
                    label="XLSX"
                  />
                )}
                {config.expected_filetypes.includes('xls') && (
                  <Input
                    type="number"
                    min={0}
                    value={config.header_row_xls}
                    onChange={(e) =>
                      updateFileConfig(configType, 'header_row_xls', parseInt(e.target.value) || 0)
                    }
                    label="XLS"
                  />
                )}
                {config.expected_filetypes.includes('csv') && (
                  <Input
                    type="number"
                    min={0}
                    value={config.header_row_csv}
                    onChange={(e) =>
                      updateFileConfig(configType, 'header_row_csv', parseInt(e.target.value) || 0)
                    }
                    label="CSV"
                  />
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Date Format</label>
                <Select
                  value={config.date_format_id?.toString() || ''}
                  onChange={(e) =>
                    updateFileConfig(
                      configType,
                      'date_format_id',
                      e.target.value ? parseInt(e.target.value) : null
                    )
                  }
                  options={[
                    { value: '', label: 'Select date format...' },
                    ...(allSettings?.date_formats
                      .filter((f) => f.is_active)
                      .map((f) => ({
                        value: f.id.toString(),
                        label: `${f.format_string} (${f.example})`,
                      })) || []),
                  ]}
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  End of Data Signal
                </label>
                <Input
                  value={config.end_of_data_signal}
                  onChange={(e) =>
                    updateFileConfig(configType, 'end_of_data_signal', e.target.value)
                  }
                  placeholder="e.g., TOTAL"
                  helperText="Text that signals end of transactions"
                />
              </div>
            </div>

            {/* Column Mapping Section */}
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
              <div className="mb-3">
                <label className="block text-sm font-medium text-gray-700">
                  Column Mapping (Raw to Template)
                </label>
                <p className="mt-1 text-xs text-gray-500">
                  Map raw file column names to template columns. Enter comma-separated values for
                  multiple possible names.
                </p>
              </div>
              <div className="grid gap-3">
                {TEMPLATE_COLUMNS.map((col) => (
                  <div key={col} className="grid grid-cols-3 items-center gap-3">
                    <label className="text-sm font-medium text-gray-600">{col}</label>
                    <div className="col-span-2">
                      <Input
                        value={config.column_mapping[col] || ''}
                        onChange={(e) => {
                          const newMapping = { ...config.column_mapping, [col]: e.target.value };
                          setFormData((prev) => ({
                            ...prev,
                            [configType]: {
                              ...prev[configType],
                              column_mapping: newMapping,
                            },
                          }));
                        }}
                        placeholder={
                          col === 'Date'
                            ? 'e.g., Transaction Date, Trans Date, Value Date'
                            : col === 'Reference'
                              ? 'e.g., Ref No, Transaction ID, Receipt'
                              : col === 'Details'
                                ? 'e.g., Description, Narrative, Particulars'
                                : col === 'Debit'
                                  ? 'e.g., Debit Amount, Withdrawal, DR'
                                  : 'e.g., Credit Amount, Deposit, CR'
                        }
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  if (isLoading) return <PageLoading />;

  if (error) {
    return (
      <Alert variant="error" title="Error loading gateways">
        {getErrorMessage(error)}
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Gateway Configuration</h1>
          <p className="mt-1 text-gray-500">Manage payment gateway settings</p>
        </div>
        <div className="flex gap-3">
          {pendingRequests.length > 0 && (
            <Button variant="outline" onClick={() => setIsRequestsModalOpen(true)}>
              <Clock className="mr-2 h-4 w-4" />
              Pending ({pendingRequests.length})
            </Button>
          )}
          <Button onClick={() => setIsCreateModalOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add Gateway
          </Button>
        </div>
      </div>

      {/* Pending requests banner */}
      {pendingRequests.length > 0 && (
        <div className="flex items-center gap-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
          <Clock className="h-6 w-6 text-amber-600" />
          <div className="flex-1">
            <p className="font-medium text-amber-800">
              You have {pendingRequests.length} pending change request
              {pendingRequests.length !== 1 ? 's' : ''}
            </p>
            <p className="text-sm text-amber-600">Waiting for admin approval</p>
          </div>
          <Button variant="outline" size="sm" onClick={() => setIsRequestsModalOpen(true)}>
            <Eye className="mr-1 h-4 w-4" />
            View Requests
          </Button>
        </div>
      )}

      {/* Unified Gateways Table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Payment Gateways</CardTitle>
          <CardDescription>
            Configure external bank gateways and their internal Workpay counterparts
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Gateway</TableHead>
                <TableHead>External Config</TableHead>
                <TableHead>Internal Config</TableHead>
                <TableHead>Location</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="w-10"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {pagination.paginatedItems.length === 0 ? (
                <TableEmpty message="No gateways configured" colSpan={6} />
              ) : (
                pagination.paginatedItems.map((gateway) => (
                  <TableRow key={gateway.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium">{gateway.display_name}</div>
                        {gateway.description && (
                          <div className="text-xs text-gray-500">{gateway.description}</div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        <code className="rounded bg-blue-50 px-1.5 py-0.5 text-blue-700">
                          {gateway.external_config?.name || '-'}
                        </code>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        <code className="rounded bg-purple-50 px-1.5 py-0.5 text-purple-700">
                          {gateway.internal_config?.name || '-'}
                        </code>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        <div>{gateway.country?.name || '-'}</div>
                        <div className="text-gray-500">{gateway.currency?.code || '-'}</div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={gateway.is_active ? 'success' : 'danger'}
                        className="text-xs"
                      >
                        {gateway.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <button
                        ref={(el) => {
                          dropdownButtonRefs.current[gateway.id] = el;
                        }}
                        onClick={() => handleDropdownToggle(gateway.id)}
                        className="rounded p-1 hover:bg-gray-100"
                      >
                        <MoreVertical className="h-4 w-4 text-gray-500" />
                      </button>
                      {renderDropdownMenu(gateway)}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
          <CompactPagination
            currentPage={pagination.currentPage}
            totalPages={pagination.totalPages}
            onPageChange={pagination.setCurrentPage}
          />
        </CardContent>
      </Card>

      {/* Create Request Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => {
          setIsCreateModalOpen(false);
          resetForm();
        }}
        title="Request New Gateway"
        description="Submit a request to create a new payment gateway (requires admin approval)"
        size="xl"
      >
        <div className="max-h-[70vh] space-y-4 overflow-y-auto pr-2">
          {/* Basic Info */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Display Name <span className="text-red-500">*</span>
              </label>
              <Input
                value={formData.display_name}
                onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                placeholder="e.g., Equity Bank"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
              <Input
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Optional description"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Country</label>
              <Select
                value={formData.country_id?.toString() || ''}
                onChange={(e) => {
                  const countryId = e.target.value ? parseInt(e.target.value) : null;
                  setFormData({
                    ...formData,
                    country_id: countryId,
                    currency_id: null, // Reset currency when country changes
                  });
                }}
                options={[
                  { value: '', label: 'Select country...' },
                  ...(allSettings?.countries
                    .filter((c) => c.is_active)
                    .map((c) => ({
                      value: c.id.toString(),
                      label: `${c.name} (${c.code})`,
                    })) || []),
                ]}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Currency</label>
              <Select
                value={formData.currency_id?.toString() || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    currency_id: e.target.value ? parseInt(e.target.value) : null,
                  })
                }
                disabled={!formData.country_id}
                options={[
                  {
                    value: '',
                    label: formData.country_id ? 'Select currency...' : 'Select country first',
                  },
                  ...availableCurrencies
                    .filter((c) => c.is_active)
                    .map((c) => ({
                      value: c.id.toString(),
                      label: `${c.code} - ${c.name}`,
                    })),
                ]}
              />
            </div>
          </div>

          {/* External Config Section */}
          {renderFileConfigSection(
            'external_config',
            'External Configuration (Bank Statement)',
            <FileText className="h-5 w-5 text-blue-600" />,
            externalExpanded,
            setExternalExpanded
          )}

          {/* Internal Config Section */}
          {renderFileConfigSection(
            'internal_config',
            'Internal Configuration (Workpay)',
            <Server className="h-5 w-5 text-purple-600" />,
            internalExpanded,
            setInternalExpanded
          )}
        </div>
        <ModalFooter>
          <Button variant="outline" onClick={() => setIsCreateModalOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleCreateRequest} isLoading={createRequestMutation.isPending}>
            Submit Request
          </Button>
        </ModalFooter>
      </Modal>

      {/* Edit Request Modal */}
      <Modal
        isOpen={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false);
          setSelectedGateway(null);
          resetForm();
        }}
        title="Request Gateway Edit"
        description={`Submit a request to update: ${selectedGateway?.display_name} (requires admin approval)`}
        size="xl"
      >
        <div className="max-h-[70vh] space-y-4 overflow-y-auto pr-2">
          {/* Basic Info */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Display Name</label>
              <Input
                value={formData.display_name}
                onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                placeholder="e.g., Equity Bank"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
              <Input
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Optional description"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Country</label>
              <Select
                value={formData.country_id?.toString() || ''}
                onChange={(e) => {
                  const countryId = e.target.value ? parseInt(e.target.value) : null;
                  setFormData({
                    ...formData,
                    country_id: countryId,
                    currency_id: null,
                  });
                }}
                options={[
                  { value: '', label: 'Select country...' },
                  ...(allSettings?.countries
                    .filter((c) => c.is_active)
                    .map((c) => ({
                      value: c.id.toString(),
                      label: `${c.name} (${c.code})`,
                    })) || []),
                ]}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Currency</label>
              <Select
                value={formData.currency_id?.toString() || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    currency_id: e.target.value ? parseInt(e.target.value) : null,
                  })
                }
                disabled={!formData.country_id}
                options={[
                  {
                    value: '',
                    label: formData.country_id ? 'Select currency...' : 'Select country first',
                  },
                  ...availableCurrencies
                    .filter((c) => c.is_active)
                    .map((c) => ({
                      value: c.id.toString(),
                      label: `${c.code} - ${c.name}`,
                    })),
                ]}
              />
            </div>
          </div>

          {/* External Config Section */}
          {renderFileConfigSection(
            'external_config',
            'External Configuration (Bank Statement)',
            <FileText className="h-5 w-5 text-blue-600" />,
            externalExpanded,
            setExternalExpanded
          )}

          {/* Internal Config Section */}
          {renderFileConfigSection(
            'internal_config',
            'Internal Configuration (Workpay)',
            <Server className="h-5 w-5 text-purple-600" />,
            internalExpanded,
            setInternalExpanded
          )}
        </div>
        <ModalFooter>
          <Button variant="outline" onClick={() => setIsEditModalOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleUpdateRequest} isLoading={updateRequestMutation.isPending}>
            Submit Request
          </Button>
        </ModalFooter>
      </Modal>

      {/* My Requests Modal */}
      <Modal
        isOpen={isRequestsModalOpen}
        onClose={() => setIsRequestsModalOpen(false)}
        title="My Change Requests"
        description="Track the status of your gateway change requests"
        size="lg"
      >
        <div className="max-h-96 overflow-y-auto">
          {myRequestsData?.requests.length === 0 ? (
            <div className="py-8 text-center text-gray-500">No change requests submitted yet</div>
          ) : (
            <div className="space-y-3">
              {myRequestsData?.requests.map((request) => (
                <div key={request.id} className="space-y-2 rounded-lg border border-gray-200 p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-medium capitalize">{request.request_type}</span>
                      <code className="rounded bg-gray-100 px-2 py-0.5 text-sm">
                        {request.gateway_name}
                      </code>
                    </div>
                    <Badge variant={STATUS_VARIANTS[request.status as ChangeRequestStatus]}>
                      {request.status}
                    </Badge>
                  </div>
                  <div className="text-sm text-gray-500">
                    Submitted: {formatDateTime(request.created_at)}
                  </div>
                  {request.status === 'approved' && request.reviewed_by_name && (
                    <div className="flex items-center gap-2 text-sm text-green-600">
                      <CheckCircle className="h-4 w-4" />
                      Approved by {request.reviewed_by_name}
                    </div>
                  )}
                  {request.status === 'rejected' && (
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 text-sm text-red-600">
                        <XCircle className="h-4 w-4" />
                        Rejected by {request.reviewed_by_name}
                      </div>
                      {request.rejection_reason && (
                        <div className="pl-6 text-sm text-red-600">
                          Reason: {request.rejection_reason}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
        <ModalFooter>
          <Button variant="outline" onClick={() => setIsRequestsModalOpen(false)}>
            Close
          </Button>
        </ModalFooter>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={isDeleteConfirmModalOpen}
        onClose={() => {
          setIsDeleteConfirmModalOpen(false);
          setGatewayToDelete(null);
        }}
        title="Confirm Permanent Delete"
        size="sm"
      >
        <div className="space-y-4">
          <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4">
            <Trash2 className="h-6 w-6 shrink-0 text-red-600" />
            <div>
              <p className="font-medium text-red-800">
                Are you sure you want to request permanent deletion?
              </p>
              <p className="mt-1 text-sm text-red-600">
                This action cannot be undone once approved by an admin.
              </p>
            </div>
          </div>
          {gatewayToDelete && (
            <div className="rounded-lg bg-gray-50 p-3">
              <p className="text-sm text-gray-600">Gateway to delete:</p>
              <p className="font-medium">{gatewayToDelete.display_name}</p>
            </div>
          )}
        </div>
        <ModalFooter>
          <Button
            variant="outline"
            onClick={() => {
              setIsDeleteConfirmModalOpen(false);
              setGatewayToDelete(null);
            }}
          >
            No, Cancel
          </Button>
          <Button
            variant="danger"
            onClick={confirmPermanentDelete}
            isLoading={deleteRequestMutation.isPending}
          >
            Yes, Delete
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  );
}
