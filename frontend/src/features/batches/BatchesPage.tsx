import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plus,
  FolderOpen,
  Lock,
  Trash2,
  ChevronLeft,
  ChevronRight,
  User,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  CheckCircle2,
} from 'lucide-react';
import { batchesApi, getErrorMessage } from '@/api';
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
  getStatusBadgeVariant,
  PageLoading,
  Alert,
  Select,
  Modal,
  ModalFooter,
} from '@/components/ui';
import { useToast } from '@/hooks/useToast';
import { useUser, useIsAdminOnly, useIsUserRole } from '@/stores';
import { formatDateTime, cn } from '@/lib/utils';
import type { Batch, BatchDeleteRequest } from '@/types';

const pageSizeOptions = [
  { value: '5', label: '5 per page' },
  { value: '10', label: '10 per page' },
  { value: '25', label: '25 per page' },
];

export function BatchesPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const currentUser = useUser();
  const isAdminOnly = useIsAdminOnly();
  const isUserRole = useIsUserRole();

  // Separate pagination states for each table
  const [pendingPage, setPendingPage] = useState(1);
  const [pendingPageSize, setPendingPageSize] = useState(10);
  const [closedPage, setClosedPage] = useState(1);
  const [closedPageSize, setClosedPageSize] = useState(10);

  // Modal states
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [closeModalOpen, setCloseModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [approveModalOpen, setApproveModalOpen] = useState(false);
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [selectedBatch, setSelectedBatch] = useState<Batch | null>(null);
  const [selectedDeleteRequest, setSelectedDeleteRequest] = useState<BatchDeleteRequest | null>(null);
  const [deleteReason, setDeleteReason] = useState('');
  const [rejectionReason, setRejectionReason] = useState('');

  // Fetch pending batches
  const { data: pendingData, isLoading: pendingLoading, error: pendingError } = useQuery({
    queryKey: ['batches', 'pending', pendingPage, pendingPageSize],
    queryFn: () =>
      batchesApi.list({
        status: 'pending',
        page: pendingPage,
        page_size: pendingPageSize,
      }),
  });

  // Fetch closed batches
  const { data: closedData, isLoading: closedLoading, error: closedError } = useQuery({
    queryKey: ['batches', 'completed', closedPage, closedPageSize],
    queryFn: () =>
      batchesApi.list({
        status: 'completed',
        page: closedPage,
        page_size: closedPageSize,
      }),
  });

  // Fetch pending delete requests (for admins)
  const { data: deleteRequestsData } = useQuery({
    queryKey: ['batchDeleteRequests', 'pending'],
    queryFn: () => batchesApi.getDeleteRequests('pending'),
    enabled: isAdminOnly,
  });

  // Create a map of batch_id -> pending delete request for quick lookup
  const pendingDeleteRequestsMap = useMemo(() => {
    const map = new Map<string, BatchDeleteRequest>();
    if (deleteRequestsData?.requests) {
      for (const req of deleteRequestsData.requests) {
        map.set(req.batch_id, req);
      }
    }
    return map;
  }, [deleteRequestsData]);

  const createBatchMutation = useMutation({
    mutationFn: () => batchesApi.create(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['batches'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['reportBatches'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['transactionBatches'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['dashboardBatches'], refetchType: 'all' });
      toast.success(`Batch ${data.batch_id} created successfully`);
      setCreateModalOpen(false);
    },
    onError: (err) => {
      toast.error(getErrorMessage(err));
      setCreateModalOpen(false);
    },
  });

  const closeBatchMutation = useMutation({
    mutationFn: (batchId: string) => batchesApi.close(batchId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['batches'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['reportBatches'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['transactionBatches'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['dashboardBatches'], refetchType: 'all' });
      toast.success(`Batch ${data.batch_id} closed successfully`);
      setCloseModalOpen(false);
      setSelectedBatch(null);
    },
    onError: (err) => {
      toast.error(getErrorMessage(err));
      setCloseModalOpen(false);
    },
  });

  const requestDeleteMutation = useMutation({
    mutationFn: ({ batchId, reason }: { batchId: string; reason?: string }) =>
      batchesApi.requestDelete(batchId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batches'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['batchDeleteRequests'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['reportBatches'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['transactionBatches'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['dashboardBatches'], refetchType: 'all' });
      toast.success('Delete request submitted. Awaiting admin approval.');
      setDeleteModalOpen(false);
      setSelectedBatch(null);
      setDeleteReason('');
    },
    onError: (err) => {
      toast.error(getErrorMessage(err));
    },
  });

  // Admin: Approve delete request
  const approveDeleteMutation = useMutation({
    mutationFn: (requestId: number) =>
      batchesApi.reviewDeleteRequest(requestId, { approved: true }),
    onSuccess: async () => {
      setApproveModalOpen(false);
      setSelectedDeleteRequest(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['batches'], refetchType: 'all' }),
        queryClient.invalidateQueries({ queryKey: ['batchDeleteRequests'], refetchType: 'all' }),
        queryClient.invalidateQueries({ queryKey: ['transactionBatches'], refetchType: 'all' }),
        queryClient.invalidateQueries({ queryKey: ['transactions'], refetchType: 'all' }),
        queryClient.invalidateQueries({ queryKey: ['dashboard-stats'], refetchType: 'all' }),
        queryClient.invalidateQueries({ queryKey: ['dashboardBatches'], refetchType: 'all' }),
      ]);
      toast.success('Delete request approved. Batch has been deleted.');
    },
    onError: (err) => {
      toast.error(getErrorMessage(err));
      setApproveModalOpen(false);
    },
  });

  // Admin: Reject delete request
  const rejectDeleteMutation = useMutation({
    mutationFn: ({ requestId, reason }: { requestId: number; reason: string }) =>
      batchesApi.reviewDeleteRequest(requestId, { approved: false, rejection_reason: reason }),
    onSuccess: async () => {
      setRejectModalOpen(false);
      setSelectedDeleteRequest(null);
      setRejectionReason('');
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['batches'], refetchType: 'all' }),
        queryClient.invalidateQueries({ queryKey: ['batchDeleteRequests'], refetchType: 'all' }),
        queryClient.invalidateQueries({ queryKey: ['transactionBatches'], refetchType: 'all' }),
        queryClient.invalidateQueries({ queryKey: ['dashboardBatches'], refetchType: 'all' }),
      ]);
      toast.success('Delete request rejected.');
    },
    onError: (err) => {
      toast.error(getErrorMessage(err));
      setRejectModalOpen(false);
    },
  });

  const handleCreateClick = () => {
    setCreateModalOpen(true);
  };

  const handleConfirmCreate = () => {
    createBatchMutation.mutate();
  };

  const handleCloseClick = (batch: Batch) => {
    setSelectedBatch(batch);
    setCloseModalOpen(true);
  };

  const handleConfirmClose = () => {
    if (selectedBatch) {
      closeBatchMutation.mutate(selectedBatch.batch_id);
    }
  };

  const handleDeleteClick = (batch: Batch) => {
    setSelectedBatch(batch);
    setDeleteModalOpen(true);
  };

  const handleConfirmDelete = () => {
    if (selectedBatch) {
      requestDeleteMutation.mutate({
        batchId: selectedBatch.batch_id,
        reason: deleteReason || undefined,
      });
    }
  };

  // Admin: Handle approve delete click
  const handleApproveClick = (deleteRequest: BatchDeleteRequest) => {
    setSelectedDeleteRequest(deleteRequest);
    setApproveModalOpen(true);
  };

  const handleConfirmApprove = () => {
    if (selectedDeleteRequest) {
      approveDeleteMutation.mutate(selectedDeleteRequest.id);
    }
  };

  // Admin: Handle reject delete click
  const handleRejectClick = (deleteRequest: BatchDeleteRequest) => {
    setSelectedDeleteRequest(deleteRequest);
    setRejectModalOpen(true);
  };

  const handleConfirmReject = () => {
    if (selectedDeleteRequest && rejectionReason.trim()) {
      rejectDeleteMutation.mutate({
        requestId: selectedDeleteRequest.id,
        reason: rejectionReason.trim(),
      });
    }
  };

  if (pendingLoading && closedLoading) return <PageLoading />;

  if (pendingError && closedError) {
    return (
      <Alert variant="error" title="Error loading batches">
        {getErrorMessage(pendingError)}
      </Alert>
    );
  }

  const pendingBatches = pendingData?.batches || [];
  const pendingPagination = pendingData?.pagination;
  const closedBatches = closedData?.batches || [];
  const closedPagination = closedData?.pagination;

  // Pagination component for reuse
  const PaginationControls = ({
    pagination,
    page,
    onPageChange,
    pageSize,
    onPageSizeChange,
    label,
  }: {
    pagination: typeof pendingPagination;
    page: number;
    onPageChange: (p: number) => void;
    pageSize: number;
    onPageSizeChange: (size: string) => void;
    label: string;
  }) => {
    if (!pagination || pagination.total_pages === 0) return null;

    return (
      <div className="flex flex-col gap-3 px-4 py-3 border-t">
        <div className="flex items-center justify-between">
          <div className="text-xs text-gray-500">
            {pagination.total_count} {label}
          </div>
          <div className="w-28">
            <Select
              options={pageSizeOptions}
              value={pageSize.toString()}
              onChange={(e) => onPageSizeChange(e.target.value)}
            />
          </div>
        </div>
        {pagination.total_pages > 1 && (
          <div className="flex items-center justify-center gap-1">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(page - 1)}
              disabled={!pagination.has_previous}
              className="px-2"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-xs text-gray-600 px-2">
              {page} / {pagination.total_pages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(page + 1)}
              disabled={!pagination.has_next}
              className="px-2"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Batches</h1>
          <p className="text-gray-500 mt-1">
            {isAdminOnly
              ? 'Review batches and approve/reject deletion requests'
              : 'Manage reconciliation batches'}
          </p>
        </div>
        {/* Only users can create batches, not admins */}
        {isUserRole && (
          <Button onClick={handleCreateClick}>
            <Plus className="h-4 w-4 mr-2" />
            Create Batch
          </Button>
        )}
      </div>

      {/* Two-column layout for tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pending Batches Table - Left Side */}
        <Card>
          <CardHeader className="flex flex-row items-center gap-2 pb-3">
            <Clock className="h-5 w-5 text-amber-500" />
            <CardTitle className="text-lg">Pending Batches</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Batch ID</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created By</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pendingLoading ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center py-8 text-gray-500">
                      Loading...
                    </TableCell>
                  </TableRow>
                ) : pendingBatches.length === 0 ? (
                  <TableEmpty message="No pending batches" colSpan={4} />
                ) : (
                  pendingBatches.map((batch) => {
                    const isCreator = currentUser?.id === batch.created_by_id;
                    const pendingDeleteRequest = pendingDeleteRequestsMap.get(batch.batch_id);
                    const hasPendingDelete = !!pendingDeleteRequest;

                    return (
                      <TableRow
                        key={batch.id}
                        className={cn(hasPendingDelete && 'bg-red-50')}
                      >
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <div className={cn(
                              'p-1.5 rounded-lg',
                              hasPendingDelete ? 'bg-red-100' : 'bg-amber-100'
                            )}>
                              {hasPendingDelete ? (
                                <AlertTriangle className="h-4 w-4 text-red-600" />
                              ) : (
                                <FolderOpen className="h-4 w-4 text-amber-600" />
                              )}
                            </div>
                            <div>
                              <span className={cn(
                                'font-mono text-sm',
                                hasPendingDelete && 'text-red-700'
                              )}>
                                {batch.batch_id}
                              </span>
                              {hasPendingDelete && (
                                <p className="text-xs text-red-600 font-medium">
                                  Pending deletion
                                </p>
                              )}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          {hasPendingDelete ? (
                            <Badge variant="danger">Delete Pending</Badge>
                          ) : (
                            <Badge variant={getStatusBadgeVariant(batch.status)}>{batch.status}</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <div className={cn(
                            'flex items-center gap-1.5 text-sm',
                            hasPendingDelete ? 'text-red-600' : 'text-gray-600'
                          )}>
                            <User className="h-3.5 w-3.5" />
                            {batch.created_by || '-'}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center justify-end gap-1">
                            {/* Admin view: Show approve/reject for pending delete requests */}
                            {isAdminOnly && hasPendingDelete && pendingDeleteRequest && (
                              <>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleApproveClick(pendingDeleteRequest)}
                                  className="text-green-600 hover:text-green-700 hover:bg-green-50"
                                >
                                  <CheckCircle className="h-4 w-4 mr-1" />
                                  Approve
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleRejectClick(pendingDeleteRequest)}
                                  className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                >
                                  <XCircle className="h-4 w-4 mr-1" />
                                  Reject
                                </Button>
                              </>
                            )}

                            {/* User view: Show close and request delete buttons */}
                            {isUserRole && (
                              <>
                                {isCreator && (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleCloseClick(batch)}
                                    className="text-green-600 hover:text-green-700 hover:bg-green-50 px-2"
                                    title="Close batch"
                                  >
                                    <Lock className="h-4 w-4" />
                                  </Button>
                                )}
                                {!hasPendingDelete && (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleDeleteClick(batch)}
                                    className="text-danger-600 hover:text-danger-700 hover:bg-danger-50 px-2"
                                    title="Request delete"
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </Button>
                                )}
                              </>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
            <PaginationControls
              pagination={pendingPagination}
              page={pendingPage}
              onPageChange={(p) => setPendingPage(p)}
              pageSize={pendingPageSize}
              onPageSizeChange={(size) => {
                setPendingPageSize(parseInt(size, 10));
                setPendingPage(1);
              }}
              label="pending"
            />
          </CardContent>
        </Card>

        {/* Closed Batches Table - Right Side */}
        <Card>
          <CardHeader className="flex flex-row items-center gap-2 pb-3">
            <CheckCircle2 className="h-5 w-5 text-green-500" />
            <CardTitle className="text-lg">Closed Batches</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Batch ID</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created By</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {closedLoading ? (
                  <TableRow>
                    <TableCell colSpan={3} className="text-center py-8 text-gray-500">
                      Loading...
                    </TableCell>
                  </TableRow>
                ) : closedBatches.length === 0 ? (
                  <TableEmpty message="No closed batches" colSpan={3} />
                ) : (
                  closedBatches.map((batch) => (
                    <TableRow key={batch.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="p-1.5 rounded-lg bg-green-100">
                            <FolderOpen className="h-4 w-4 text-green-600" />
                          </div>
                          <span className="font-mono text-sm">
                            {batch.batch_id}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={getStatusBadgeVariant(batch.status)}>{batch.status}</Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1.5 text-sm text-gray-600">
                          <User className="h-3.5 w-3.5" />
                          {batch.created_by || '-'}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
            <PaginationControls
              pagination={closedPagination}
              page={closedPage}
              onPageChange={(p) => setClosedPage(p)}
              pageSize={closedPageSize}
              onPageSizeChange={(size) => {
                setClosedPageSize(parseInt(size, 10));
                setClosedPage(1);
              }}
              label="closed"
            />
          </CardContent>
        </Card>
      </div>

      {/* Create Batch Confirmation Modal */}
      <Modal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        title="Create Batch"
        description="Confirm batch creation"
        size="sm"
      >
        <div className="space-y-4">
          <p className="text-neutral-700">
            Are you sure you want to create a new reconciliation batch?
          </p>
          <p className="text-sm text-neutral-500">
            A new batch will be created and a storage directory will be provisioned for file uploads.
            You cannot create another batch until this one is closed.
          </p>
        </div>
        <ModalFooter>
          <Button variant="outline" onClick={() => setCreateModalOpen(false)}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleConfirmCreate}
            isLoading={createBatchMutation.isPending}
          >
            Create Batch
          </Button>
        </ModalFooter>
      </Modal>

      {/* Close Batch Confirmation Modal */}
      <Modal
        isOpen={closeModalOpen}
        onClose={() => { setCloseModalOpen(false); setSelectedBatch(null); }}
        title="Close Batch"
        description="Confirm batch closure"
        size="sm"
      >
        <div className="space-y-4">
          <p className="text-neutral-700">
            Are you sure you want to close batch{' '}
            <span className="font-mono font-semibold">{selectedBatch?.batch_id}</span>?
          </p>
          <p className="text-sm text-neutral-500">
            A batch can only be closed if all transactions are reconciled.
            Once closed, the batch status will be marked as completed.
          </p>
        </div>
        <ModalFooter>
          <Button variant="outline" onClick={() => { setCloseModalOpen(false); setSelectedBatch(null); }}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleConfirmClose}
            isLoading={closeBatchMutation.isPending}
          >
            Close Batch
          </Button>
        </ModalFooter>
      </Modal>

      {/* Delete Request Modal (for users) */}
      <Modal
        isOpen={deleteModalOpen}
        onClose={() => { setDeleteModalOpen(false); setSelectedBatch(null); setDeleteReason(''); }}
        title="Request Batch Deletion"
        description="This request requires admin approval."
        size="sm"
      >
        <div className="space-y-4">
          <p className="text-neutral-700">
            Request deletion of batch{' '}
            <span className="font-mono font-semibold">{selectedBatch?.batch_id}</span>?
          </p>
          <p className="text-sm text-neutral-500">
            This will submit a delete request that must be approved by an admin.
            Upon approval, the batch, its files, and all associated transactions will be permanently deleted.
          </p>
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Reason (optional)
            </label>
            <textarea
              className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              rows={3}
              value={deleteReason}
              onChange={(e) => setDeleteReason(e.target.value)}
              placeholder="Provide a reason for deletion..."
            />
          </div>
        </div>
        <ModalFooter>
          <Button variant="outline" onClick={() => { setDeleteModalOpen(false); setSelectedBatch(null); setDeleteReason(''); }}>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={handleConfirmDelete}
            isLoading={requestDeleteMutation.isPending}
          >
            Submit Request
          </Button>
        </ModalFooter>
      </Modal>

      {/* Approve Delete Modal (for admins) */}
      <Modal
        isOpen={approveModalOpen}
        onClose={() => { setApproveModalOpen(false); setSelectedDeleteRequest(null); }}
        title="Approve Batch Deletion"
        description="This action cannot be undone."
        size="sm"
      >
        <div className="space-y-4">
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5" />
              <div>
                <p className="text-red-800 font-medium">
                  Approve deletion of batch{' '}
                  <span className="font-mono">{selectedDeleteRequest?.batch_id}</span>?
                </p>
                <p className="text-sm text-red-600 mt-1">
                  This will permanently delete the batch, all uploaded files, and all associated transactions.
                </p>
              </div>
            </div>
          </div>
          {selectedDeleteRequest?.reason && (
            <div>
              <p className="text-sm font-medium text-neutral-700">Deletion reason:</p>
              <p className="text-sm text-neutral-600 mt-1 p-2 bg-neutral-100 rounded">
                {selectedDeleteRequest.reason}
              </p>
            </div>
          )}
          <div className="text-sm text-neutral-500">
            <p>Requested by: {selectedDeleteRequest?.requested_by}</p>
            <p>Requested at: {selectedDeleteRequest?.created_at ? formatDateTime(selectedDeleteRequest.created_at) : '-'}</p>
          </div>
        </div>
        <ModalFooter>
          <Button variant="outline" onClick={() => { setApproveModalOpen(false); setSelectedDeleteRequest(null); }}>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={handleConfirmApprove}
            isLoading={approveDeleteMutation.isPending}
          >
            <CheckCircle className="h-4 w-4 mr-1" />
            Approve Deletion
          </Button>
        </ModalFooter>
      </Modal>

      {/* Reject Delete Modal (for admins) */}
      <Modal
        isOpen={rejectModalOpen}
        onClose={() => { setRejectModalOpen(false); setSelectedDeleteRequest(null); setRejectionReason(''); }}
        title="Reject Deletion Request"
        description="Provide a reason for rejection."
        size="sm"
      >
        <div className="space-y-4">
          <p className="text-neutral-700">
            Reject deletion request for batch{' '}
            <span className="font-mono font-semibold">{selectedDeleteRequest?.batch_id}</span>?
          </p>
          {selectedDeleteRequest?.reason && (
            <div>
              <p className="text-sm font-medium text-neutral-700">Original deletion reason:</p>
              <p className="text-sm text-neutral-600 mt-1 p-2 bg-neutral-100 rounded">
                {selectedDeleteRequest.reason}
              </p>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Rejection reason <span className="text-red-500">*</span>
            </label>
            <textarea
              className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              rows={3}
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              placeholder="Provide a reason for rejecting this request..."
            />
          </div>
        </div>
        <ModalFooter>
          <Button variant="outline" onClick={() => { setRejectModalOpen(false); setSelectedDeleteRequest(null); setRejectionReason(''); }}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleConfirmReject}
            isLoading={rejectDeleteMutation.isPending}
            disabled={!rejectionReason.trim()}
          >
            <XCircle className="h-4 w-4 mr-1" />
            Reject Request
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  );
}
