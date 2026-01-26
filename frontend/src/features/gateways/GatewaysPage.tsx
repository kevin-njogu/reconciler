import { useState, useRef, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, MoreVertical, Edit2, Power, Clock, CheckCircle, XCircle, Eye, Building2, Server, Trash2 } from 'lucide-react';
import { gatewaysApi, getErrorMessage } from '@/api';
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
import type { GatewayConfig, GatewayType, ChangeRequestType, ChangeRequestStatus } from '@/types';

const PAGE_SIZE = 5;

// Custom hook for pagination
function usePagination<T>(items: T[], pageSize: number = PAGE_SIZE) {
  const [currentPage, setCurrentPage] = useState(1);

  const totalPages = Math.ceil(items.length / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const paginatedItems = items.slice(startIndex, startIndex + pageSize);

  // Reset to page 1 if current page exceeds total pages
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

export function GatewaysPage() {
  const toast = useToast();
  const queryClient = useQueryClient();

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isRequestsModalOpen, setIsRequestsModalOpen] = useState(false);
  const [isDeleteConfirmModalOpen, setIsDeleteConfirmModalOpen] = useState(false);
  const [selectedGateway, setSelectedGateway] = useState<GatewayConfig | null>(null);
  const [gatewayToDelete, setGatewayToDelete] = useState<GatewayConfig | null>(null);
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null);
  const [dropdownPosition, setDropdownPosition] = useState<{ top: number; left: number } | null>(null);
  const dropdownButtonRefs = useRef<Record<string, HTMLButtonElement | null>>({});

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    gateway_type: 'external' as GatewayType,
    display_name: '',
    country: '',
    currency: '',
    date_format: 'YYYY-MM-DD',
    charge_keywords: '',
  });

  const { data: gateways, isLoading, error } = useQuery({
    queryKey: ['gateway-configs', { include_inactive: true }],
    queryFn: () => gatewaysApi.list({ include_inactive: true }),
  });

  const { data: gatewayOptions } = useQuery({
    queryKey: ['gateway-options'],
    queryFn: () => gatewaysApi.getOptions(),
  });

  const { data: myRequestsData } = useQuery({
    queryKey: ['my-gateway-requests'],
    queryFn: () => gatewaysApi.getMyChangeRequests(),
    staleTime: 0, // Always refetch to get latest status
  });

  // Create change request mutation
  const createRequestMutation = useMutation({
    mutationFn: gatewaysApi.createChangeRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-gateway-requests'] });
      toast.success('Change request submitted for approval');
      setIsCreateModalOpen(false);
      resetForm();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  // Update change request mutation
  const updateRequestMutation = useMutation({
    mutationFn: gatewaysApi.createChangeRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-gateway-requests'] });
      toast.success('Update request submitted for approval');
      setIsEditModalOpen(false);
      setSelectedGateway(null);
      resetForm();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  // Delete/Deactivate change request mutation
  const deleteRequestMutation = useMutation({
    mutationFn: gatewaysApi.createChangeRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-gateway-requests'] });
      toast.success('Deactivation request submitted for approval');
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  // Activate change request mutation
  const activateRequestMutation = useMutation({
    mutationFn: gatewaysApi.createChangeRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-gateway-requests'] });
      toast.success('Activation request submitted for approval');
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const resetForm = () => {
    setFormData({
      name: '',
      gateway_type: 'external',
      display_name: '',
      country: '',
      currency: '',
      date_format: 'YYYY-MM-DD',
      charge_keywords: '',
    });
  };

  const handleCreateRequest = () => {
    // Validate required fields
    if (!formData.name || !formData.display_name || !formData.country || !formData.currency) {
      toast.error('Please fill in all required fields');
      return;
    }

    const keywords = formData.charge_keywords
      .split(',')
      .map((k) => k.trim().toLowerCase())
      .filter((k) => k);

    createRequestMutation.mutate({
      request_type: 'create' as ChangeRequestType,
      gateway_name: formData.name,
      proposed_changes: {
        gateway_type: formData.gateway_type,
        display_name: formData.display_name,
        country: formData.country,
        currency: formData.currency,
        date_format: formData.date_format,
        charge_keywords: keywords,
      },
    });
  };

  const handleUpdateRequest = () => {
    if (!selectedGateway) return;

    const keywords = formData.charge_keywords
      .split(',')
      .map((k) => k.trim().toLowerCase())
      .filter((k) => k);

    updateRequestMutation.mutate({
      request_type: 'update' as ChangeRequestType,
      gateway_name: selectedGateway.name,
      proposed_changes: {
        display_name: formData.display_name,
        country: formData.country,
        currency: formData.currency,
        date_format: formData.date_format,
        charge_keywords: keywords,
      },
    });
  };

  const handleDeactivateRequest = (gateway: GatewayConfig) => {
    deleteRequestMutation.mutate({
      request_type: 'delete' as ChangeRequestType,
      gateway_name: gateway.name,
      proposed_changes: {},
    });
    setActiveDropdown(null);
  };

  const handleActivateRequest = (gateway: GatewayConfig) => {
    activateRequestMutation.mutate({
      request_type: 'activate' as ChangeRequestType,
      gateway_name: gateway.name,
      proposed_changes: {},
    });
    setActiveDropdown(null);
  };

  const handlePermanentDeleteRequest = (gateway: GatewayConfig) => {
    setGatewayToDelete(gateway);
    setIsDeleteConfirmModalOpen(true);
    setActiveDropdown(null);
  };

  const confirmPermanentDelete = () => {
    if (!gatewayToDelete) return;
    deleteRequestMutation.mutate({
      request_type: 'permanent_delete' as ChangeRequestType,
      gateway_name: gatewayToDelete.name,
      proposed_changes: {},
    });
    setIsDeleteConfirmModalOpen(false);
    setGatewayToDelete(null);
  };

  const openEditModal = (gateway: GatewayConfig) => {
    setSelectedGateway(gateway);
    setFormData({
      name: gateway.name,
      gateway_type: gateway.gateway_type,
      display_name: gateway.display_name,
      country: gateway.country,
      currency: gateway.currency,
      date_format: gateway.date_format,
      charge_keywords: gateway.charge_keywords.join(', '),
    });
    setIsEditModalOpen(true);
    setActiveDropdown(null);
  };

  const gatewayTypeOptions = [
    { value: 'external', label: 'External (Bank)' },
    { value: 'internal', label: 'Internal (Workpay)' },
  ];

  const pendingRequests = myRequestsData?.requests.filter(r => r.status === 'pending') || [];

  const handleDropdownToggle = (gatewayName: string) => {
    if (activeDropdown === gatewayName) {
      setActiveDropdown(null);
      setDropdownPosition(null);
    } else {
      const buttonEl = dropdownButtonRefs.current[gatewayName];
      if (buttonEl) {
        const rect = buttonEl.getBoundingClientRect();
        // Position dropdown above the button, aligned to the right
        setDropdownPosition({
          top: rect.top - 8, // 8px above the button
          left: rect.right - 192, // 192px = w-48 (12rem)
        });
      }
      setActiveDropdown(gatewayName);
    }
  };

  const closeDropdown = () => {
    setActiveDropdown(null);
    setDropdownPosition(null);
  };

  // Render the dropdown menu using a portal
  const renderDropdownMenu = (gateway: GatewayConfig) => {
    if (activeDropdown !== gateway.name || !dropdownPosition) return null;

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
          <div className="border-t border-gray-100 my-1" />
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
                onClick={() => {
                  handlePermanentDeleteRequest(gateway);
                }}
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

  // Split gateways by type with memoization
  const externalGateways = useMemo(
    () => gateways?.filter((g) => g.gateway_type === 'external') || [],
    [gateways]
  );
  const internalGateways = useMemo(
    () => gateways?.filter((g) => g.gateway_type === 'internal') || [],
    [gateways]
  );

  // Pagination for each table
  const externalPagination = usePagination(externalGateways);
  const internalPagination = usePagination(internalGateways);

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
          <p className="text-gray-500 mt-1">Manage payment gateway settings</p>
        </div>
        <div className="flex gap-3">
          {pendingRequests.length > 0 && (
            <Button variant="outline" onClick={() => setIsRequestsModalOpen(true)}>
              <Clock className="h-4 w-4 mr-2" />
              Pending ({pendingRequests.length})
            </Button>
          )}
          <Button onClick={() => setIsCreateModalOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Add Gateway
          </Button>
        </div>
      </div>

      {/* Pending requests banner */}
      {pendingRequests.length > 0 && (
        <div className="flex items-center gap-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <Clock className="h-6 w-6 text-amber-600" />
          <div className="flex-1">
            <p className="font-medium text-amber-800">
              You have {pendingRequests.length} pending change request{pendingRequests.length !== 1 ? 's' : ''}
            </p>
            <p className="text-sm text-amber-600">
              Waiting for admin approval
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => setIsRequestsModalOpen(true)}>
            <Eye className="h-4 w-4 mr-1" />
            View Requests
          </Button>
        </div>
      )}

      {/* Side-by-side Gateway Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* External Gateways */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Building2 className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <CardTitle className="text-lg">External Gateways</CardTitle>
                <CardDescription>Bank statement sources ({externalGateways.length})</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Gateway</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="w-10"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {externalPagination.paginatedItems.length === 0 ? (
                  <TableEmpty message="No external gateways configured" colSpan={4} />
                ) : (
                  externalPagination.paginatedItems.map((gateway) => (
                    <TableRow key={gateway.id}>
                      <TableCell>
                        <div>
                          <div className="font-medium">{gateway.display_name}</div>
                          <code className="text-xs text-gray-500">{gateway.name}</code>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          <div>{gateway.country}</div>
                          <div className="text-gray-500">{gateway.currency}</div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={gateway.is_active ? 'success' : 'danger'} className="text-xs">
                          {gateway.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <button
                          ref={(el) => { dropdownButtonRefs.current[gateway.name] = el; }}
                          onClick={() => handleDropdownToggle(gateway.name)}
                          className="p-1 rounded hover:bg-gray-100"
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
              currentPage={externalPagination.currentPage}
              totalPages={externalPagination.totalPages}
              onPageChange={externalPagination.setCurrentPage}
            />
          </CardContent>
        </Card>

        {/* Internal Gateways */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Server className="h-5 w-5 text-purple-600" />
              </div>
              <div>
                <CardTitle className="text-lg">Internal Gateways</CardTitle>
                <CardDescription>Internal record sources ({internalGateways.length})</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Gateway</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="w-10"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {internalPagination.paginatedItems.length === 0 ? (
                  <TableEmpty message="No internal gateways configured" colSpan={4} />
                ) : (
                  internalPagination.paginatedItems.map((gateway) => (
                    <TableRow key={gateway.id}>
                      <TableCell>
                        <div>
                          <div className="font-medium">{gateway.display_name}</div>
                          <code className="text-xs text-gray-500">{gateway.name}</code>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          <div>{gateway.country}</div>
                          <div className="text-gray-500">{gateway.currency}</div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={gateway.is_active ? 'success' : 'danger'} className="text-xs">
                          {gateway.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <button
                          ref={(el) => { dropdownButtonRefs.current[gateway.name] = el; }}
                          onClick={() => handleDropdownToggle(gateway.name)}
                          className="p-1 rounded hover:bg-gray-100"
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
              currentPage={internalPagination.currentPage}
              totalPages={internalPagination.totalPages}
              onPageChange={internalPagination.setCurrentPage}
            />
          </CardContent>
        </Card>
      </div>

      {/* Create Request Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => {
          setIsCreateModalOpen(false);
          resetForm();
        }}
        title="Request New Gateway"
        description="Submit a request to create a new payment gateway (requires admin approval)"
        size="lg"
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Gateway Name <span className="text-red-500">*</span>
              </label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value.toLowerCase() })}
                placeholder="e.g., coop, ncba"
                helperText="Lowercase, no spaces"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Gateway Type <span className="text-red-500">*</span>
              </label>
              <Select
                value={formData.gateway_type}
                onChange={(e) => setFormData({ ...formData, gateway_type: e.target.value as GatewayType })}
                options={gatewayTypeOptions}
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Display Name <span className="text-red-500">*</span>
            </label>
            <Input
              value={formData.display_name}
              onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
              placeholder="e.g., Co-operative Bank"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Country <span className="text-red-500">*</span>
              </label>
              <Select
                value={formData.country}
                onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                options={[
                  { value: '', label: 'Select country...' },
                  ...(gatewayOptions?.countries.map(c => ({ value: c.code, label: `${c.name} (${c.code})` })) || [])
                ]}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Currency <span className="text-red-500">*</span>
              </label>
              <Select
                value={formData.currency}
                onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
                options={[
                  { value: '', label: 'Select currency...' },
                  ...(gatewayOptions?.currencies.map(c => ({ value: c.code, label: `${c.code} - ${c.name}` })) || [])
                ]}
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Date Format <span className="text-red-500">*</span>
            </label>
            <Select
              value={formData.date_format}
              onChange={(e) => setFormData({ ...formData, date_format: e.target.value })}
              options={gatewayOptions?.date_formats.map(f => ({ value: f.format, label: `${f.format} (e.g., ${f.example})` })) || []}
            />
          </div>
          <Input
            label="Charge Keywords (comma-separated)"
            value={formData.charge_keywords}
            onChange={(e) => setFormData({ ...formData, charge_keywords: e.target.value })}
            placeholder="charge, fee, commission"
            helperText="Keywords to identify bank charges in narrations (will be lowercased)"
          />
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
        description={`Submit a request to update: ${selectedGateway?.name} (requires admin approval)`}
        size="lg"
      >
        <div className="space-y-4">
          <Input
            label="Display Name"
            value={formData.display_name}
            onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
            placeholder="e.g., Co-operative Bank"
          />
          <div className="grid grid-cols-2 gap-4">
            <Select
              label="Country"
              value={formData.country}
              onChange={(e) => setFormData({ ...formData, country: e.target.value })}
              options={[
                { value: '', label: 'Select country...' },
                ...(gatewayOptions?.countries.map(c => ({ value: c.code, label: `${c.name} (${c.code})` })) || [])
              ]}
            />
            <Select
              label="Currency"
              value={formData.currency}
              onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
              options={[
                { value: '', label: 'Select currency...' },
                ...(gatewayOptions?.currencies.map(c => ({ value: c.code, label: `${c.code} - ${c.name}` })) || [])
              ]}
            />
          </div>
          <Select
            label="Date Format"
            value={formData.date_format}
            onChange={(e) => setFormData({ ...formData, date_format: e.target.value })}
            options={gatewayOptions?.date_formats.map(f => ({ value: f.format, label: `${f.format} (e.g., ${f.example})` })) || []}
          />
          <Input
            label="Charge Keywords (comma-separated)"
            value={formData.charge_keywords}
            onChange={(e) => setFormData({ ...formData, charge_keywords: e.target.value })}
            placeholder="charge, fee, commission"
            helperText="Keywords to identify bank charges in narrations (will be lowercased)"
          />
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
            <div className="text-center py-8 text-gray-500">
              No change requests submitted yet
            </div>
          ) : (
            <div className="space-y-3">
              {myRequestsData?.requests.map((request) => (
                <div
                  key={request.id}
                  className="p-4 border border-gray-200 rounded-lg space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-medium capitalize">{request.request_type}</span>
                      <code className="text-sm bg-gray-100 px-2 py-0.5 rounded">
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
                        <div className="text-sm text-red-600 pl-6">
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
          <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
            <Trash2 className="h-6 w-6 text-red-600 shrink-0" />
            <div>
              <p className="font-medium text-red-800">
                Are you sure you want to request permanent deletion?
              </p>
              <p className="text-sm text-red-600 mt-1">
                This action cannot be undone once approved by an admin.
              </p>
            </div>
          </div>
          {gatewayToDelete && (
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-600">Gateway to delete:</p>
              <p className="font-medium">{gatewayToDelete.display_name}</p>
              <code className="text-xs text-gray-500">{gatewayToDelete.name}</code>
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
