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
  File,
  CheckCircle,
  XCircle,
  AlertTriangle,
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
import type { Batch, BatchStatus, BatchDeleteRequest } from '@/types';

const statusOptions = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'completed', label: 'Completed' },
];

const pageSizeOptions = [
  { value: '10', label: '10 per page' },
  { value: '25', label: '25 per page' },
  { value: '50', label: '50 per page' },
];

export function BatchesPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const currentUser = useUser();
  const isAdminOnly = useIsAdminOnly();
  const isUserRole = useIsUserRole();
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

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

  const { data, isLoading, error } = useQuery({
    queryKey: ['batches', statusFilter, page, pageSize],
    queryFn: () =>
      batchesApi.list({
        status: statusFilter ? (statusFilter as BatchStatus) : undefined,
        page,
        page_size: pageSize,
      }),
  });

  // Fetch pending delete requests (for admins)
  const { data: deleteRequestsData } = useQuery({
    queryKey: ['batchDeleteRequests', 'pending'],
    queryFn: () => batchesApi.getDeleteRequests('pending'),
    enabled: isAdminOnly, // Only fetch for admins
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
      queryClient.invalidateQueries({ queryKey: ['batches'] });
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
      queryClient.invalidateQueries({ queryKey: ['batches'] });
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
      queryClient.invalidateQueries({ queryKey: ['batches'] });
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batches'] });
      queryClient.invalidateQueries({ queryKey: ['batchDeleteRequests'] });
      toast.success('Delete request approved. Batch has been deleted.');
      setApproveModalOpen(false);
      setSelectedDeleteRequest(null);
    },
    onError: (err) => {
      toast.error(getErrorMessage(err));
    },
  });

  // Admin: Reject delete request
  const rejectDeleteMutation = useMutation({
    mutationFn: ({ requestId, reason }: { requestId: number; reason: string }) =>
      batchesApi.reviewDeleteRequest(requestId, { approved: false, rejection_reason: reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batches'] });
      queryClient.invalidateQueries({ queryKey: ['batchDeleteRequests'] });
      toast.success('Delete request rejected.');
      setRejectModalOpen(false);
      setSelectedDeleteRequest(null);
      setRejectionReason('');
    },
    onError: (err) => {
      toast.error(getErrorMessage(err));
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

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
  };

  const handlePageSizeChange = (newSize: string) => {
    setPageSize(parseInt(newSize, 10));
    setPage(1);
  };

  const handleStatusFilterChange = (newStatus: string) => {
    setStatusFilter(newStatus);
    setPage(1);
  };

  if (isLoading) return <PageLoading />;

  if (error) {
    return (
      <Alert variant="error" title="Error loading batches">
        {getErrorMessage(error)}
      </Alert>
    );
  }

  const batches = data?.batches || [];
  const pagination = data?.pagination;

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

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>All Batches</CardTitle>
          <div className="flex gap-3">
            <div className="w-32">
              <Select
                options={pageSizeOptions}
                value={pageSize.toString()}
                onChange={(e) => handlePageSizeChange(e.target.value)}
              />
            </div>
            <div className="w-48">
              <Select
                options={statusOptions}
                value={statusFilter}
                onChange={(e) => handleStatusFilterChange(e.target.value)}
                placeholder="Filter by status"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Batch ID</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created By</TableHead>
                <TableHead>Files</TableHead>
                <TableHead>Created At</TableHead>
                <TableHead>Closed At</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {batches.length === 0 ? (
                <TableEmpty message="No batches found. Create one to get started." colSpan={7} />
              ) : (
                batches.map((batch) => {
                  const isCreator = currentUser?.id === batch.created_by_id;
                  const isPending = batch.status === 'pending';
                  const pendingDeleteRequest = pendingDeleteRequestsMap.get(batch.batch_id);
                  const hasPendingDelete = !!pendingDeleteRequest;

                  return (
                    <TableRow
                      key={batch.id}
                      className={cn(hasPendingDelete && 'bg-red-50')}
                    >
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className={cn(
                            'p-2 rounded-lg',
                            hasPendingDelete ? 'bg-red-100' : 'bg-gray-100'
                          )}>
                            {hasPendingDelete ? (
                              <AlertTriangle className="h-5 w-5 text-red-600" />
                            ) : (
                              <FolderOpen className="h-5 w-5 text-gray-600" />
                            )}
                          </div>
                          <div>
                            <span className={cn(
                              'font-mono font-medium',
                              hasPendingDelete && 'text-red-700'
                            )}>
                              {batch.batch_id}
                            </span>
                            {hasPendingDelete && (
                              <p className="text-xs text-red-600 mt-0.5 font-medium">
                                Pending deletion by {pendingDeleteRequest.requested_by}
                              </p>
                            )}
                            {batch.description && !hasPendingDelete && (
                              <p className="text-xs text-gray-500 mt-0.5 max-w-50 truncate">
                                {batch.description}
                              </p>
                            )}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        {hasPendingDelete ? (
                          <Badge variant="error">Delete Pending</Badge>
                        ) : (
                          <Badge variant={getStatusBadgeVariant(batch.status)}>{batch.status}</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className={cn(
                          'flex items-center gap-2',
                          hasPendingDelete ? 'text-red-600' : 'text-gray-500'
                        )}>
                          <User className="h-4 w-4" />
                          {batch.created_by || '-'}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className={cn(
                          'flex items-center gap-2',
                          hasPendingDelete ? 'text-red-600' : 'text-gray-500'
                        )}>
                          <File className="h-4 w-4" />
                          {batch.file_count ?? 0}
                        </div>
                      </TableCell>
                      <TableCell className={hasPendingDelete ? 'text-red-600' : 'text-gray-500'}>
                        {formatDateTime(batch.created_at)}
                      </TableCell>
                      <TableCell className={hasPendingDelete ? 'text-red-600' : 'text-gray-500'}>
                        {batch.closed_at ? formatDateTime(batch.closed_at) : '-'}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center justify-end gap-2">
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
                                Approve Delete
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleRejectClick(pendingDeleteRequest)}
                                className="text-red-600 hover:text-red-700 hover:bg-red-50"
                              >
                                <XCircle className="h-4 w-4 mr-1" />
                                Reject Delete
                              </Button>
                            </>
                          )}

                          {/* User view: Show close and request delete buttons */}
                          {isUserRole && (
                            <>
                              {isPending && isCreator && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleCloseClick(batch)}
                                  className="text-green-600 hover:text-green-700 hover:bg-green-50"
                                >
                                  <Lock className="h-4 w-4 mr-1" />
                                  Close
                                </Button>
                              )}
                              {!hasPendingDelete && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleDeleteClick(batch)}
                                  className="text-danger-600 hover:text-danger-700 hover:bg-danger-50"
                                >
                                  <Trash2 className="h-4 w-4 mr-1" />
                                  Request Delete
                                </Button>
                              )}
                              {hasPendingDelete && (
                                <span className="text-xs text-red-600 italic">
                                  Awaiting approval
                                </span>
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

          {/* Pagination Controls */}
          {pagination && pagination.total_pages > 0 && (
            <div className="flex items-center justify-between px-6 py-4 border-t">
              <div className="text-sm text-gray-500">
                Showing {(pagination.page - 1) * pagination.page_size + 1} to{' '}
                {Math.min(pagination.page * pagination.page_size, pagination.total_count)} of{' '}
                {pagination.total_count} batches
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(page - 1)}
                  disabled={!pagination.has_previous}
                >
                  <ChevronLeft className="h-4 w-4 mr-1" />
                  Previous
                </Button>
                <div className="flex items-center gap-1">
                  {Array.from({ length: Math.min(5, pagination.total_pages) }, (_, i) => {
                    let pageNum: number;
                    if (pagination.total_pages <= 5) {
                      pageNum = i + 1;
                    } else if (page <= 3) {
                      pageNum = i + 1;
                    } else if (page >= pagination.total_pages - 2) {
                      pageNum = pagination.total_pages - 4 + i;
                    } else {
                      pageNum = page - 2 + i;
                    }
                    return (
                      <Button
                        key={pageNum}
                        variant={pageNum === page ? 'primary' : 'outline'}
                        size="sm"
                        onClick={() => handlePageChange(pageNum)}
                        className="min-w-[40px]"
                      >
                        {pageNum}
                      </Button>
                    );
                  })}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(page + 1)}
                  disabled={!pagination.has_next}
                >
                  Next
                  <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

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
            <p>Requested by: <span className="font-medium">{selectedDeleteRequest?.requested_by}</span></p>
            <p>Requested at: <span className="font-medium">{selectedDeleteRequest?.created_at ? formatDateTime(selectedDeleteRequest.created_at) : '-'}</span></p>
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
