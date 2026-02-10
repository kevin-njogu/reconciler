import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Shield, CheckCircle, XCircle, Clock, User, Settings, Plus, Edit2, Trash2, Power } from 'lucide-react';
import { gatewaysApi, getErrorMessage } from '@/api';
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  TableEmpty,
  Badge,
  Pagination,
  PageLoading,
  Alert,
  Modal,
  ModalFooter,
} from '@/components/ui';
import { useToast } from '@/hooks/useToast';
import { formatDateTime } from '@/lib/utils';
import type { GatewayChangeRequest, ChangeRequestStatus } from '@/types';

const REQUEST_TYPE_LABELS: Record<string, { label: string; icon: typeof Plus; color: string }> = {
  create: { label: 'Create Gateway', icon: Plus, color: 'text-green-600' },
  update: { label: 'Update Gateway', icon: Edit2, color: 'text-blue-600' },
  delete: { label: 'Delete Gateway', icon: Trash2, color: 'text-red-600' },
  activate: { label: 'Activate Gateway', icon: Power, color: 'text-purple-600' },
};

const STATUS_VARIANTS: Record<ChangeRequestStatus, 'warning' | 'success' | 'danger'> = {
  pending: 'warning',
  approved: 'success',
  rejected: 'danger',
};

export function GatewayApprovalPage() {
  const toast = useToast();
  const queryClient = useQueryClient();

  // State
  const [selectedRequest, setSelectedRequest] = useState<GatewayChangeRequest | null>(null);
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);
  const [actionType, setActionType] = useState<'approve' | 'reject'>('approve');
  const [rejectionReason, setRejectionReason] = useState('');
  const [statusFilter, setStatusFilter] = useState<ChangeRequestStatus | 'all'>('pending');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Fetch change requests
  const { data: changeRequestsData, isLoading, error } = useQuery({
    queryKey: ['gateway-change-requests', statusFilter, page],
    queryFn: () =>
      statusFilter === 'pending'
        ? gatewaysApi.getPendingChangeRequests(page, pageSize)
        : gatewaysApi.getAllChangeRequests(statusFilter === 'all' ? undefined : statusFilter, page, pageSize),
    staleTime: 0,
  });

  // Review mutation
  const reviewMutation = useMutation({
    mutationFn: ({ requestId, approved, rejectionReason }: { requestId: number; approved: boolean; rejectionReason?: string }) =>
      gatewaysApi.reviewChangeRequest(requestId, { approved, rejection_reason: rejectionReason }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['gateway-change-requests'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['unified-gateways'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['my-gateway-requests'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['available-gateways'], refetchType: 'all' });
      toast.success(variables.approved ? 'Change request approved' : 'Change request rejected');
      closeReviewModal();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const openReviewModal = (request: GatewayChangeRequest, action: 'approve' | 'reject') => {
    setSelectedRequest(request);
    setActionType(action);
    setRejectionReason('');
    setIsReviewModalOpen(true);
  };

  const closeReviewModal = () => {
    setIsReviewModalOpen(false);
    setSelectedRequest(null);
    setRejectionReason('');
  };

  const handleReview = () => {
    if (!selectedRequest) return;
    reviewMutation.mutate({
      requestId: selectedRequest.id,
      approved: actionType === 'approve',
      rejectionReason: actionType === 'reject' ? rejectionReason : undefined,
    });
  };

  const renderProposedChanges = (request: GatewayChangeRequest) => {
    const changes = request.proposed_changes;
    return (
      <div className="space-y-1 text-sm">
        {request.request_type === 'create' && (
          <>
            <div><span className="text-gray-500">Display Name:</span> {String(changes.display_name)}</div>
            {changes.country && (
              <div><span className="text-gray-500">Country:</span> {String(changes.country)}</div>
            )}
            {changes.currency_code && (
              <div><span className="text-gray-500">Currency:</span> {String(changes.currency_code)}</div>
            )}
            {changes.external_config && (
              <div><span className="text-gray-500">External:</span> {String((changes.external_config as Record<string, unknown>).name)}</div>
            )}
            {changes.internal_config && (
              <div><span className="text-gray-500">Internal:</span> {String((changes.internal_config as Record<string, unknown>).name)}</div>
            )}
          </>
        )}
        {request.request_type === 'update' && (
          <>
            {changes.display_name && (
              <div><span className="text-gray-500">Display Name:</span> {String(changes.display_name)}</div>
            )}
            {changes.country && (
              <div><span className="text-gray-500">Country:</span> {String(changes.country)}</div>
            )}
            {changes.currency_code && (
              <div><span className="text-gray-500">Currency:</span> {String(changes.currency_code)}</div>
            )}
            {changes.external_config && (
              <div><span className="text-gray-500">External:</span> {String((changes.external_config as Record<string, unknown>).name)}</div>
            )}
            {changes.internal_config && (
              <div><span className="text-gray-500">Internal:</span> {String((changes.internal_config as Record<string, unknown>).name)}</div>
            )}
          </>
        )}
        {request.request_type === 'delete' && (
          <div className="text-red-600">Gateway will be deactivated</div>
        )}
        {request.request_type === 'activate' && (
          <div className="text-green-600">Gateway will be reactivated</div>
        )}
      </div>
    );
  };

  if (isLoading) return <PageLoading />;

  if (error) {
    return (
      <Alert variant="error" title="Error loading change requests">
        {getErrorMessage(error)}
      </Alert>
    );
  }

  const requests = changeRequestsData?.requests || [];
  const pendingCount = requests.filter(r => r.status === 'pending').length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Gateway Approvals</h1>
          <p className="text-gray-500 mt-1">Review and approve gateway change requests</p>
        </div>
        <div className="flex items-center gap-4">
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value as ChangeRequestStatus | 'all'); setPage(1); }}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          >
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="all">All</option>
          </select>
        </div>
      </div>

      {statusFilter === 'pending' && pendingCount === 0 ? (
        <Alert variant="success" title="No pending approvals">
          All gateway change requests have been processed.
        </Alert>
      ) : requests.length === 0 ? (
        <Alert variant="info" title="No requests found">
          No gateway change requests match your filter.
        </Alert>
      ) : (
        <>
          {/* Summary for pending */}
          {statusFilter === 'pending' && pendingCount > 0 && (
            <div className="flex items-center gap-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
              <Shield className="h-6 w-6 text-amber-600" />
              <div>
                <p className="font-medium text-amber-800">
                  {pendingCount} gateway change request{pendingCount !== 1 ? 's' : ''} pending approval
                </p>
                <p className="text-sm text-amber-600">
                  Review each request and approve or reject
                </p>
              </div>
            </div>
          )}

          {/* Requests Table */}
          <Card>
            <CardHeader>
              <CardTitle>Change Requests</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Request Type</TableHead>
                    <TableHead>Gateway</TableHead>
                    <TableHead>Proposed Changes</TableHead>
                    <TableHead>Requested By</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {requests.length === 0 ? (
                    <TableEmpty message="No change requests" colSpan={6} />
                  ) : (
                    requests.map((request) => {
                      const typeInfo = REQUEST_TYPE_LABELS[request.request_type] || {
                        label: request.request_type,
                        icon: Settings,
                        color: 'text-gray-600',
                      };
                      const Icon = typeInfo.icon;

                      return (
                        <TableRow key={request.id}>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Icon className={`h-4 w-4 ${typeInfo.color}`} />
                              <span>{typeInfo.label}</span>
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-3">
                              <div className="p-2 bg-gray-100 rounded-lg">
                                <Settings className="h-4 w-4 text-gray-600" />
                              </div>
                              <div>
                                <span className="font-medium">{request.gateway_display_name}</span>
                              </div>
                            </div>
                          </TableCell>
                          <TableCell>{renderProposedChanges(request)}</TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <User className="h-4 w-4 text-gray-400" />
                              <div>
                                <div className="text-sm">{request.requested_by_name || 'Unknown'}</div>
                                <div className="text-xs text-gray-500">
                                  {formatDateTime(request.created_at)}
                                </div>
                              </div>
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="space-y-1">
                              <Badge variant={STATUS_VARIANTS[request.status as ChangeRequestStatus]}>
                                {request.status}
                              </Badge>
                              {request.reviewed_by_name && (
                                <div className="text-xs text-gray-500">
                                  by {request.reviewed_by_name}
                                </div>
                              )}
                              {request.rejection_reason && (
                                <div className="text-xs text-red-600 max-w-xs truncate">
                                  {request.rejection_reason}
                                </div>
                              )}
                            </div>
                          </TableCell>
                          <TableCell className="text-right">
                            {request.status === 'pending' ? (
                              <div className="flex items-center justify-end gap-2">
                                <Button
                                  variant="primary"
                                  size="sm"
                                  onClick={() => openReviewModal(request, 'approve')}
                                >
                                  <CheckCircle className="h-4 w-4 mr-1" />
                                  Approve
                                </Button>
                                <Button
                                  variant="danger"
                                  size="sm"
                                  onClick={() => openReviewModal(request, 'reject')}
                                >
                                  <XCircle className="h-4 w-4 mr-1" />
                                  Reject
                                </Button>
                              </div>
                            ) : (
                              <span className="text-gray-400 text-sm">Processed</span>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Pagination */}
          {(changeRequestsData?.total_pages || 1) > 1 && (
            <Pagination
              currentPage={page}
              totalPages={changeRequestsData?.total_pages || 1}
              onPageChange={setPage}
              totalItems={changeRequestsData?.count}
              pageSize={pageSize}
              showItemCount
            />
          )}
        </>
      )}

      {/* Review Modal */}
      <Modal
        isOpen={isReviewModalOpen}
        onClose={closeReviewModal}
        title={actionType === 'approve' ? 'Approve Change Request' : 'Reject Change Request'}
        description={
          actionType === 'approve'
            ? 'This will apply the gateway change immediately'
            : 'Provide a reason for rejecting this request'
        }
        size="md"
      >
        {selectedRequest && (
          <div className="space-y-4">
            {/* Request Details */}
            <div className="bg-gray-50 p-4 rounded-lg space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-500">Request Type</span>
                <span className="font-medium capitalize">{selectedRequest.request_type}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-500">Gateway</span>
                <span className="font-medium">{selectedRequest.gateway_display_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-500">Requested By</span>
                <span>{selectedRequest.requested_by_name}</span>
              </div>
              <div className="border-t pt-3">
                <span className="text-sm text-gray-500 block mb-2">Proposed Changes</span>
                {renderProposedChanges(selectedRequest)}
              </div>
            </div>

            {/* Rejection Reason Input */}
            {actionType === 'reject' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Rejection Reason <span className="text-red-500">*</span>
                </label>
                <textarea
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-blue-400"
                  rows={3}
                  placeholder="Explain why this request is being rejected..."
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                />
              </div>
            )}

            {/* Warning for approve */}
            {actionType === 'approve' && (
              <div className="flex items-center gap-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <Clock className="h-5 w-5 text-blue-500" />
                <span className="text-sm text-blue-700">
                  The gateway change will be applied immediately after approval
                </span>
              </div>
            )}
          </div>
        )}
        <ModalFooter>
          <Button variant="outline" onClick={closeReviewModal}>
            Cancel
          </Button>
          <Button
            variant={actionType === 'approve' ? 'primary' : 'danger'}
            onClick={handleReview}
            isLoading={reviewMutation.isPending}
            disabled={actionType === 'reject' && !rejectionReason.trim()}
          >
            {actionType === 'approve' ? 'Approve' : 'Reject'}
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  );
}
