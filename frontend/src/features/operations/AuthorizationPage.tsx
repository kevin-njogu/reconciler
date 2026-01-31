import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { Shield, CheckCircle, XCircle, Clock, ArrowLeftRight } from 'lucide-react';
import { operationsApi, batchesApi, getErrorMessage } from '@/api';
import type { UnreconciledTransaction } from '@/api/operations';
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  PageLoading,
  Alert,
  Select,
  Modal,
  ModalFooter,
} from '@/components/ui';
import { useToast } from '@/hooks/useToast';
import { formatCurrency } from '@/lib/utils';
import { SimpleAuthorizationView } from './SimpleAuthorizationView';

export function AuthorizationPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();

  const [selectedBatchId, setSelectedBatchId] = useState<string>(
    searchParams.get('batch_id') || ''
  );
  const [selectedGateway, setSelectedGateway] = useState<string>(
    searchParams.get('gateway') || ''
  );

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

  // Fetch only pending batches
  const { data: batchesData, isLoading: batchesLoading } = useQuery({
    queryKey: ['batches', 'pending'],
    queryFn: () => batchesApi.list({ status: 'pending' }),
  });

  const batches = batchesData?.batches;

  // Fetch pending authorizations (optionally filtered by batch)
  const {
    data: pendingData,
    isLoading: pendingLoading,
    error: pendingError,
  } = useQuery({
    queryKey: ['pending-authorization', selectedBatchId, selectedGateway],
    queryFn: () =>
      operationsApi.getPendingAuthorization(
        selectedBatchId || undefined,
        selectedGateway || undefined
      ),
    enabled: !!selectedBatchId,
    staleTime: 0,
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
      queryClient.invalidateQueries({ queryKey: ['pending-authorization'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['unreconciled'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['batches'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['transactions'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'], refetchType: 'all' });
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
      queryClient.invalidateQueries({ queryKey: ['pending-authorization'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['unreconciled'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['batches'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['transactions'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'], refetchType: 'all' });
      toast.success(data.message);
      closeBulkModal();
      setSelectedIds(new Set());
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const handleBatchChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const batchId = e.target.value;
    setSelectedBatchId(batchId);
    setSelectedGateway('');
    setSelectedIds(new Set());
    setSearchParams(batchId ? { batch_id: batchId } : {});
  };

  const handleGatewayChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const gateway = e.target.value;
    setSelectedGateway(gateway);
    setSelectedIds(new Set());
    const params: Record<string, string> = { batch_id: selectedBatchId };
    if (gateway) {
      params.gateway = gateway;
    }
    setSearchParams(params);
  };

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

  const batchOptions = [
    { value: '', label: 'Select a pending batch...' },
    ...(batches?.map((b) => ({
      value: b.batch_id,
      label: b.batch_id,
    })) || []),
  ];

  // Build unified gateway options (extract base gateway names from pending data)
  const getBaseGateway = (gateway: string) => {
    return gateway.replace(/_internal$/, '').replace(/_external$/, '');
  };

  // Get unique base gateways from pending authorization groups
  const uniqueBaseGateways = useMemo(() => {
    if (!pendingData?.groups) return [];
    const gateways = pendingData.groups.map((g) => getBaseGateway(g.gateway));
    return Array.from(new Set(gateways));
  }, [pendingData?.groups]);

  const gatewayOptions = [
    { value: '', label: 'Select gateway...' },
    ...uniqueBaseGateways.map((g) => ({
      value: g,
      label: g.charAt(0).toUpperCase() + g.slice(1),
    })),
  ];

  if (batchesLoading) return <PageLoading />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Authorization</h1>
          <p className="text-gray-500 mt-1">
            Review and authorize manually reconciled transactions
          </p>
        </div>
        {selectedIds.size > 0 && (
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-600">{selectedIds.size} selected</span>
            <Button variant="primary" size="sm" onClick={() => openBulkModal('authorize')}>
              <CheckCircle className="h-4 w-4 mr-1" />
              Authorize All
            </Button>
            <Button variant="danger" size="sm" onClick={() => openBulkModal('reject')}>
              <XCircle className="h-4 w-4 mr-1" />
              Reject All
            </Button>
          </div>
        )}
      </div>

      {/* Centered Half-Page Selection Card */}
      <div className="flex justify-center">
        <Card className="w-full max-w-xl">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2">
              <ArrowLeftRight className="h-5 w-5 text-primary-600" />
              Select Batch and Gateway
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Select
              label="Batch"
              options={batchOptions}
              value={selectedBatchId}
              onChange={handleBatchChange}
              placeholder="Select a pending batch..."
            />
            <Select
              label="Gateway"
              options={gatewayOptions}
              value={selectedGateway}
              onChange={handleGatewayChange}
              placeholder={selectedBatchId ? 'Select gateway...' : 'Select batch first'}
              disabled={!selectedBatchId || pendingLoading}
            />
          </CardContent>
        </Card>
      </div>

      {/* Content */}
      {!selectedBatchId ? (
        <Alert variant="info" title="Select a batch">
          Please select a pending batch to view transactions awaiting authorization.
        </Alert>
      ) : !selectedGateway ? (
        <Alert variant="info" title="Select a gateway">
          Please select a gateway to view transactions awaiting authorization.
        </Alert>
      ) : pendingLoading ? (
        <PageLoading />
      ) : pendingError ? (
        <Alert variant="error" title="Error loading pending authorizations">
          {getErrorMessage(pendingError)}
        </Alert>
      ) : pendingData?.total_count === 0 ? (
        <Alert variant="success" title="No pending authorizations">
          All manually reconciled transactions have been processed for this batch and gateway.
        </Alert>
      ) : (
        <>
          {/* Summary Banner */}
          <div className="flex items-center gap-4 p-4 bg-secondary-50 border border-secondary-200 rounded-lg">
            <Shield className="h-6 w-6 text-secondary-600" />
            <div>
              <p className="font-medium text-secondary-800">
                {pendingData?.total_count} transaction
                {pendingData?.total_count !== 1 ? 's' : ''} pending authorization
              </p>
              <p className="text-sm text-secondary-600">
                Review the transactions and authorize or reject each one
              </p>
            </div>
          </div>

          {/* Side-by-Side View */}
          <SimpleAuthorizationView
            groups={pendingData?.groups || []}
            selectedGateway={selectedGateway}
            selectedIds={selectedIds}
            onToggleSelection={toggleSelection}
            onToggleAllInternal={toggleAllTransactions}
            onToggleAllExternal={toggleAllTransactions}
            onAuthorize={(txn) => openActionModal(txn, 'authorize')}
            onReject={(txn) => openActionModal(txn, 'reject')}
          />
        </>
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
                <span className="text-sm text-neutral-500">Reference</span>
                <span className="font-mono text-sm">{selectedTransaction.transaction_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-neutral-500">Gateway</span>
                <span className="capitalize">{getBaseGateway(selectedTransaction.gateway)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-neutral-500">Amount</span>
                <span className="font-mono">
                  {selectedTransaction.debit
                    ? formatCurrency(selectedTransaction.debit)
                    : selectedTransaction.credit
                      ? formatCurrency(selectedTransaction.credit)
                      : selectedTransaction.amount
                        ? formatCurrency(selectedTransaction.amount)
                        : '-'}
                </span>
              </div>
              <div className="flex justify-between items-start">
                <span className="text-sm text-neutral-500">Reconciliation Note</span>
                <span className="text-sm max-w-[60%] text-right">
                  {selectedTransaction.manual_recon_note || '-'}
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
