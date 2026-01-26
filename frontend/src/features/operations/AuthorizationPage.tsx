import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Shield,
  CheckCircle,
  XCircle,
  Clock,
  User,
  MessageSquare,
  LayoutGrid,
  List,
} from 'lucide-react';
import { operationsApi, getErrorMessage } from '@/api';
import type { UnreconciledTransaction, PendingAuthorizationGroup } from '@/api/operations';
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
  PageLoading,
  Alert,
  Modal,
  ModalFooter,
} from '@/components/ui';
import { useToast } from '@/hooks/useToast';
import { formatDateTime, formatCurrency } from '@/lib/utils';
import { SideBySideAuthorizationView } from './SideBySideAuthorizationView';

export function AuthorizationPage() {
  const toast = useToast();
  const queryClient = useQueryClient();

  // Modal state
  const [actionModalOpen, setActionModalOpen] = useState(false);
  const [selectedTransaction, setSelectedTransaction] = useState<UnreconciledTransaction | null>(
    null
  );
  const [actionType, setActionType] = useState<'authorize' | 'reject'>('authorize');
  const [actionNote, setActionNote] = useState('');

  // Bulk action state
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [bulkModalOpen, setBulkModalOpen] = useState(false);
  const [bulkActionType, setBulkActionType] = useState<'authorize' | 'reject'>('authorize');
  const [bulkNote, setBulkNote] = useState('');

  // View mode: 'list' (grouped by batch/gateway) or 'side-by-side' (internal vs external)
  const [viewMode, setViewMode] = useState<'list' | 'side-by-side'>('side-by-side');

  // Fetch pending authorizations
  const {
    data: pendingData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['pending-authorization'],
    queryFn: () => operationsApi.getPendingAuthorization(),
    staleTime: 0, // Always refetch to get latest status
  });

  // Single authorization mutation
  const authorizeMutation = useMutation({
    mutationFn: ({
      transactionId,
      action,
      note,
    }: {
      transactionId: number;
      action: 'authorize' | 'reject';
      note?: string;
    }) => operationsApi.authorize(transactionId, action, note),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['pending-authorization'] });
      toast.success(
        variables.action === 'authorize'
          ? 'Transaction authorized successfully'
          : 'Transaction rejected'
      );
      closeActionModal();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  // Bulk authorization mutation
  const bulkAuthorizeMutation = useMutation({
    mutationFn: ({
      ids,
      action,
      note,
    }: {
      ids: number[];
      action: 'authorize' | 'reject';
      note?: string;
    }) => operationsApi.authorizeBulk(ids, action, note),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['pending-authorization'] });
      toast.success(data.message);
      closeBulkModal();
      setSelectedIds(new Set());
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const openActionModal = (
    transaction: UnreconciledTransaction,
    action: 'authorize' | 'reject'
  ) => {
    setSelectedTransaction(transaction);
    setActionType(action);
    setActionNote('');
    setActionModalOpen(true);
  };

  const closeActionModal = () => {
    setActionModalOpen(false);
    setSelectedTransaction(null);
    setActionNote('');
  };

  const handleSubmitAction = () => {
    if (!selectedTransaction) return;
    authorizeMutation.mutate({
      transactionId: selectedTransaction.id,
      action: actionType,
      note: actionNote.trim() || undefined,
    });
  };

  const openBulkModal = (action: 'authorize' | 'reject') => {
    if (selectedIds.size === 0) {
      toast.error('Please select at least one transaction');
      return;
    }
    setBulkActionType(action);
    setBulkNote('');
    setBulkModalOpen(true);
  };

  const closeBulkModal = () => {
    setBulkModalOpen(false);
    setBulkNote('');
  };

  const handleBulkAction = () => {
    bulkAuthorizeMutation.mutate({
      ids: Array.from(selectedIds),
      action: bulkActionType,
      note: bulkNote.trim() || undefined,
    });
  };

  const toggleSelection = (id: number) => {
    const newSelection = new Set(selectedIds);
    if (newSelection.has(id)) {
      newSelection.delete(id);
    } else {
      newSelection.add(id);
    }
    setSelectedIds(newSelection);
  };

  const toggleAllInGroup = (group: PendingAuthorizationGroup) => {
    const groupIds = group.transactions.map((t) => t.id);
    const allSelected = groupIds.every((id) => selectedIds.has(id));

    const newSelection = new Set(selectedIds);
    if (allSelected) {
      groupIds.forEach((id) => newSelection.delete(id));
    } else {
      groupIds.forEach((id) => newSelection.add(id));
    }
    setSelectedIds(newSelection);
  };

  const toggleAllTransactions = (transactions: UnreconciledTransaction[]) => {
    const ids = transactions.map((t) => t.id);
    const allSelected = ids.every((id) => selectedIds.has(id));

    const newSelection = new Set(selectedIds);
    if (allSelected) {
      ids.forEach((id) => newSelection.delete(id));
    } else {
      ids.forEach((id) => newSelection.add(id));
    }
    setSelectedIds(newSelection);
  };

  if (isLoading) return <PageLoading />;

  if (error) {
    return (
      <Alert variant="error" title="Error loading pending authorizations">
        {getErrorMessage(error)}
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Authorization</h1>
          <p className="text-gray-500 mt-1">
            Review and authorize manually reconciled transactions
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* View Mode Toggle */}
          <div className="flex items-center border border-gray-300 rounded-lg overflow-hidden">
            <button
              onClick={() => setViewMode('side-by-side')}
              className={`flex items-center gap-1 px-3 py-2 text-sm ${
                viewMode === 'side-by-side'
                  ? 'bg-primary-500 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              <LayoutGrid className="h-4 w-4" />
              Side by Side
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`flex items-center gap-1 px-3 py-2 text-sm ${
                viewMode === 'list'
                  ? 'bg-primary-500 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              <List className="h-4 w-4" />
              List View
            </button>
          </div>

          {selectedIds.size > 0 && (
            <>
              <span className="text-sm text-neutral-600">{selectedIds.size} selected</span>
              <Button variant="primary" size="sm" onClick={() => openBulkModal('authorize')}>
                <CheckCircle className="h-4 w-4 mr-1" />
                Authorize All
              </Button>
              <Button variant="danger" size="sm" onClick={() => openBulkModal('reject')}>
                <XCircle className="h-4 w-4 mr-1" />
                Reject All
              </Button>
            </>
          )}
        </div>
      </div>

      {pendingData?.total_count === 0 ? (
        <Alert variant="success" title="No pending authorizations">
          All manually reconciled transactions have been processed.
        </Alert>
      ) : viewMode === 'side-by-side' ? (
        /* Side-by-Side View */
        <SideBySideAuthorizationView
          groups={pendingData?.groups || []}
          selectedIds={selectedIds}
          onToggleSelection={toggleSelection}
          onToggleAllInternal={toggleAllTransactions}
          onToggleAllExternal={toggleAllTransactions}
          onAuthorize={(txn) => openActionModal(txn, 'authorize')}
          onReject={(txn) => openActionModal(txn, 'reject')}
        />
      ) : (
        /* List View (Grouped by Batch/Gateway) */
        <div className="space-y-6">
          {/* Summary */}
          <div className="flex items-center gap-4 p-4 bg-secondary-50 border border-secondary-200 rounded-lg">
            <Shield className="h-6 w-6 text-secondary-600" />
            <div>
              <p className="font-medium text-secondary-800">
                {pendingData?.total_count} transaction
                {pendingData?.total_count !== 1 ? 's' : ''} pending authorization
              </p>
              <p className="text-sm text-secondary-600">
                Review the reconciliation notes and authorize or reject each transaction
              </p>
            </div>
          </div>

          {/* Groups */}
          {pendingData?.groups.map((group) => {
            const allSelected = group.transactions.every((t) => selectedIds.has(t.id));
            const someSelected = group.transactions.some((t) => selectedIds.has(t.id));

            return (
              <Card key={`${group.batch_id}-${group.gateway}`}>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={allSelected}
                        ref={(el) => {
                          if (el) el.indeterminate = someSelected && !allSelected;
                        }}
                        onChange={() => toggleAllInGroup(group)}
                        className="h-4 w-4 rounded border-neutral-300 text-primary-500 focus:ring-primary-400"
                      />
                      <div>
                        <span className="capitalize">{group.gateway}</span>
                        <span className="text-neutral-400 mx-2">|</span>
                        <span className="font-mono text-sm text-neutral-600">
                          {group.batch_id}
                        </span>
                      </div>
                    </div>
                    <Badge variant="warning">{group.transactions.length} pending</Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-12"></TableHead>
                        <TableHead>Transaction</TableHead>
                        <TableHead>Reconciled By</TableHead>
                        <TableHead>Note</TableHead>
                        <TableHead className="text-right">Amount</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {group.transactions.length === 0 ? (
                        <TableEmpty message="No pending transactions" colSpan={6} />
                      ) : (
                        group.transactions.map((txn) => (
                          <TableRow key={txn.id}>
                            <TableCell>
                              <input
                                type="checkbox"
                                checked={selectedIds.has(txn.id)}
                                onChange={() => toggleSelection(txn.id)}
                                className="h-4 w-4 rounded border-neutral-300 text-primary-500 focus:ring-primary-400"
                              />
                            </TableCell>
                            <TableCell>
                              <div className="space-y-1">
                                <div className="font-mono text-sm">{txn.transaction_id}</div>
                                <div className="text-xs text-neutral-500 max-w-xs truncate">
                                  {txn.narrative}
                                </div>
                              </div>
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                <User className="h-4 w-4 text-neutral-400" />
                                <div>
                                  <div className="text-sm">
                                    {txn.manual_recon_by_username || 'Unknown'}
                                  </div>
                                  <div className="text-xs text-neutral-500">
                                    {txn.manual_recon_at
                                      ? formatDateTime(txn.manual_recon_at)
                                      : '-'}
                                  </div>
                                </div>
                              </div>
                            </TableCell>
                            <TableCell>
                              <div className="flex items-start gap-2 max-w-xs">
                                <MessageSquare className="h-4 w-4 text-neutral-400 mt-0.5 flex-shrink-0" />
                                <span className="text-sm text-neutral-600 line-clamp-2">
                                  {txn.manual_recon_note || '-'}
                                </span>
                              </div>
                            </TableCell>
                            <TableCell className="text-right font-mono">
                              {txn.debit
                                ? formatCurrency(txn.debit)
                                : txn.credit
                                  ? formatCurrency(txn.credit)
                                  : txn.amount
                                    ? formatCurrency(txn.amount)
                                    : '-'}
                            </TableCell>
                            <TableCell className="text-right">
                              <div className="flex items-center justify-end gap-2">
                                <Button
                                  variant="primary"
                                  size="sm"
                                  onClick={() => openActionModal(txn, 'authorize')}
                                >
                                  <CheckCircle className="h-4 w-4 mr-1" />
                                  Authorize
                                </Button>
                                <Button
                                  variant="danger"
                                  size="sm"
                                  onClick={() => openActionModal(txn, 'reject')}
                                >
                                  <XCircle className="h-4 w-4 mr-1" />
                                  Reject
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Single Action Modal */}
      <Modal
        isOpen={actionModalOpen}
        onClose={closeActionModal}
        title={actionType === 'authorize' ? 'Authorize Transaction' : 'Reject Transaction'}
        description={
          actionType === 'authorize'
            ? 'Confirm authorization of this manually reconciled transaction'
            : 'Provide a reason for rejecting this transaction'
        }
        size="md"
      >
        {selectedTransaction && (
          <div className="space-y-4">
            {/* Transaction Details */}
            <div className="bg-neutral-50 p-4 rounded-lg space-y-2">
              <div className="flex justify-between">
                <span className="text-sm text-neutral-500">Transaction ID</span>
                <span className="font-mono text-sm">{selectedTransaction.transaction_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-neutral-500">Reconciled By</span>
                <span>{selectedTransaction.manual_recon_by_username}</span>
              </div>
              <div className="flex justify-between items-start">
                <span className="text-sm text-neutral-500">Reconciliation Note</span>
                <span className="text-sm max-w-[60%] text-right">
                  {selectedTransaction.manual_recon_note}
                </span>
              </div>
            </div>

            {/* Note Input */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                {actionType === 'authorize' ? 'Authorization Note (optional)' : 'Rejection Reason'}
                {actionType === 'reject' && <span className="text-danger-500">*</span>}
              </label>
              <textarea
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400"
                rows={3}
                placeholder={
                  actionType === 'authorize'
                    ? 'Add a note (optional)...'
                    : 'Explain why this transaction is being rejected...'
                }
                value={actionNote}
                onChange={(e) => setActionNote(e.target.value)}
              />
            </div>
          </div>
        )}
        <ModalFooter>
          <Button variant="outline" onClick={closeActionModal}>
            Cancel
          </Button>
          <Button
            variant={actionType === 'authorize' ? 'primary' : 'danger'}
            onClick={handleSubmitAction}
            isLoading={authorizeMutation.isPending}
            disabled={actionType === 'reject' && !actionNote.trim()}
          >
            {actionType === 'authorize' ? 'Authorize' : 'Reject'}
          </Button>
        </ModalFooter>
      </Modal>

      {/* Bulk Action Modal */}
      <Modal
        isOpen={bulkModalOpen}
        onClose={closeBulkModal}
        title={bulkActionType === 'authorize' ? 'Bulk Authorize' : 'Bulk Reject'}
        description={`${selectedIds.size} transaction${selectedIds.size !== 1 ? 's' : ''} will be ${bulkActionType === 'authorize' ? 'authorized' : 'rejected'}`}
        size="sm"
      >
        <div className="space-y-4">
          <div className="flex items-center gap-3 p-3 bg-neutral-50 rounded-lg">
            <Clock className="h-5 w-5 text-neutral-500" />
            <span className="text-sm text-neutral-600">
              {selectedIds.size} transaction{selectedIds.size !== 1 ? 's' : ''} selected
            </span>
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Note {bulkActionType === 'reject' && <span className="text-danger-500">*</span>}
            </label>
            <textarea
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400"
              rows={3}
              placeholder={
                bulkActionType === 'authorize'
                  ? 'Add a note for all transactions (optional)...'
                  : 'Explain the rejection reason...'
              }
              value={bulkNote}
              onChange={(e) => setBulkNote(e.target.value)}
            />
          </div>
        </div>
        <ModalFooter>
          <Button variant="outline" onClick={closeBulkModal}>
            Cancel
          </Button>
          <Button
            variant={bulkActionType === 'authorize' ? 'primary' : 'danger'}
            onClick={handleBulkAction}
            isLoading={bulkAuthorizeMutation.isPending}
            disabled={bulkActionType === 'reject' && !bulkNote.trim()}
          >
            {bulkActionType === 'authorize' ? 'Authorize All' : 'Reject All'}
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  );
}
