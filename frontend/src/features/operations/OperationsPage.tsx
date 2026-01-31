import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { ArrowLeftRight, CheckCircle2, Clock, AlertCircle } from 'lucide-react';
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
import { SimpleSideBySideView } from './SimpleSideBySideView';

// Predefined reconciliation reasons
const RECONCILIATION_REASONS = [
  { value: '', label: 'Select a reason...' },
  { value: 'MMF Funding', label: 'MMF Funding' },
  { value: 'Utility Funding', label: 'Utility Funding' },
  { value: 'Wallet Refund', label: 'Wallet Refund' },
  { value: 'InterCompany', label: 'InterCompany' },
  { value: 'Bank Funding', label: 'Bank Funding' },
  { value: 'FX Conversion', label: 'FX Conversion' },
  { value: 'Other', label: 'Other (Specify below)' },
];

export function OperationsPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();

  const [selectedBatchId, setSelectedBatchId] = useState<string>(
    searchParams.get('batch_id') || ''
  );
  const [selectedGateway, setSelectedGateway] = useState<string>(
    searchParams.get('gateway') || ''
  );

  // Selection state for bulk operations
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  // Modal state
  const [reconcileModalOpen, setReconcileModalOpen] = useState(false);
  const [selectedTransaction, setSelectedTransaction] = useState<UnreconciledTransaction | null>(
    null
  );
  const [selectedReason, setSelectedReason] = useState('');
  const [customReason, setCustomReason] = useState('');

  // Bulk modal state
  const [bulkModalOpen, setBulkModalOpen] = useState(false);
  const [bulkSelectedReason, setBulkSelectedReason] = useState('');
  const [bulkCustomReason, setBulkCustomReason] = useState('');

  // Fetch only pending batches
  const { data: batchesData, isLoading: batchesLoading } = useQuery({
    queryKey: ['batches', 'pending'],
    queryFn: () => batchesApi.list({ status: 'pending' }),
  });

  const batches = batchesData?.batches;

  // Fetch unreconciled transactions
  const {
    data: unreconciledData,
    isLoading: unreconciledLoading,
    error: unreconciledError,
  } = useQuery({
    queryKey: ['unreconciled', selectedBatchId, selectedGateway],
    queryFn: () => operationsApi.getUnreconciled(selectedBatchId, selectedGateway || undefined),
    enabled: !!selectedBatchId,
  });

  // Manual reconciliation mutation
  const manualReconcileMutation = useMutation({
    mutationFn: ({ transactionId, note }: { transactionId: number; note: string }) =>
      operationsApi.manualReconcile(transactionId, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['unreconciled'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['pending-authorization'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['batches'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['transactions'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'], refetchType: 'all' });
      toast.success('Transaction submitted for authorization');
      closeReconcileModal();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  // Bulk manual reconciliation mutation
  const bulkReconcileMutation = useMutation({
    mutationFn: ({ transactionIds, note }: { transactionIds: number[]; note: string }) =>
      operationsApi.manualReconcileBulk(transactionIds, note),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['unreconciled'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['pending-authorization'], refetchType: 'all' });
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

  const openReconcileModal = (transaction: UnreconciledTransaction) => {
    setSelectedTransaction(transaction);
    setSelectedReason('');
    setCustomReason('');
    setReconcileModalOpen(true);
  };

  const closeReconcileModal = () => {
    setReconcileModalOpen(false);
    setSelectedTransaction(null);
    setSelectedReason('');
    setCustomReason('');
  };

  const getReconcileNote = (): string => {
    if (selectedReason === 'Other') {
      return customReason.trim();
    }
    return selectedReason;
  };

  const handleSubmitReconcile = () => {
    const note = getReconcileNote();
    if (!selectedTransaction || !note) {
      toast.error('Please select a reason for manual reconciliation');
      return;
    }
    manualReconcileMutation.mutate({
      transactionId: selectedTransaction.id,
      note,
    });
  };

  // Bulk modal functions
  const openBulkModal = () => {
    if (selectedIds.size === 0) {
      toast.error('Please select at least one transaction');
      return;
    }
    setBulkSelectedReason('');
    setBulkCustomReason('');
    setBulkModalOpen(true);
  };

  const closeBulkModal = () => {
    setBulkModalOpen(false);
    setBulkSelectedReason('');
    setBulkCustomReason('');
  };

  const getBulkReconcileNote = (): string => {
    if (bulkSelectedReason === 'Other') {
      return bulkCustomReason.trim();
    }
    return bulkSelectedReason;
  };

  const handleBulkReconcile = () => {
    const note = getBulkReconcileNote();
    if (!note) {
      toast.error('Please select a reason for manual reconciliation');
      return;
    }
    bulkReconcileMutation.mutate({
      transactionIds: Array.from(selectedIds),
      note,
    });
  };

  // Selection handlers
  const toggleSelection = (id: number) => {
    const newSelection = new Set(selectedIds);
    if (newSelection.has(id)) {
      newSelection.delete(id);
    } else {
      newSelection.add(id);
    }
    setSelectedIds(newSelection);
  };

  const toggleAllInGateway = (transactions: UnreconciledTransaction[]) => {
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

  // Build unified gateway options (extract base gateway names)
  const getBaseGateway = (gateway: string) => {
    return gateway.replace(/_internal$/, '').replace(/_external$/, '');
  };

  // Get unique base gateways from available gateways
  const uniqueBaseGateways = Array.from(
    new Set(
      (unreconciledData?.available_gateways || []).map((g) => getBaseGateway(g))
    )
  );

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
          <h1 className="text-2xl font-bold text-gray-900">Manual Reconciliation</h1>
          <p className="text-gray-500 mt-1">
            View and manually reconcile unreconciled transactions
          </p>
        </div>
        {selectedIds.size > 0 && (
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-600">{selectedIds.size} selected</span>
            <Button variant="primary" onClick={openBulkModal}>
              <CheckCircle2 className="h-4 w-4 mr-2" />
              Reconcile Selected
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
              disabled={!selectedBatchId || unreconciledLoading}
            />
          </CardContent>
        </Card>
      </div>

      {/* Content */}
      {!selectedBatchId ? (
        <Alert variant="info" title="Select a batch">
          Please select a pending batch to view unreconciled transactions.
        </Alert>
      ) : !selectedGateway ? (
        <Alert variant="info" title="Select a gateway">
          Please select a gateway to view unreconciled transactions.
        </Alert>
      ) : unreconciledLoading ? (
        <PageLoading />
      ) : unreconciledError ? (
        <Alert variant="error" title="Error loading transactions">
          {getErrorMessage(unreconciledError)}
        </Alert>
      ) : unreconciledData?.total_count === 0 ? (
        <Alert variant="success" title="All transactions reconciled">
          There are no unreconciled transactions for this batch and gateway.
        </Alert>
      ) : (
        <>
          {/* Summary Banner */}
          <div className="flex items-center gap-4 p-4 bg-warning-50 border border-warning-200 rounded-lg">
            <AlertCircle className="h-6 w-6 text-warning-600" />
            <div>
              <p className="font-medium text-warning-800">
                {unreconciledData?.total_count} unreconciled transaction
                {unreconciledData?.total_count !== 1 ? 's' : ''} found
              </p>
              <p className="text-sm text-warning-600">
                Select transactions to manually reconcile them
              </p>
            </div>
          </div>

          {/* Side-by-Side View */}
          <SimpleSideBySideView
            byGateway={unreconciledData?.by_gateway || {}}
            selectedGateway={selectedGateway}
            selectedIds={selectedIds}
            onToggleSelection={toggleSelection}
            onToggleAllInternal={toggleAllInGateway}
            onToggleAllExternal={toggleAllInGateway}
            onReconcileClick={openReconcileModal}
          />
        </>
      )}

      {/* Single Manual Reconciliation Modal */}
      <Modal
        isOpen={reconcileModalOpen}
        onClose={closeReconcileModal}
        title="Manual Reconciliation"
        description="Select a reason for manually reconciling this transaction"
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
            </div>

            {/* Reason Selection */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Reason for Manual Reconciliation <span className="text-danger-500">*</span>
              </label>
              <select
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400"
                value={selectedReason}
                onChange={(e) => setSelectedReason(e.target.value)}
              >
                {RECONCILIATION_REASONS.map((reason) => (
                  <option key={reason.value} value={reason.value}>
                    {reason.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Custom Reason Input (only shown when "Other" is selected) */}
            {selectedReason === 'Other' && (
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">
                  Specify Reason <span className="text-danger-500">*</span>
                </label>
                <textarea
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400"
                  rows={3}
                  placeholder="Enter your custom reason..."
                  value={customReason}
                  onChange={(e) => setCustomReason(e.target.value)}
                />
              </div>
            )}

            {/* Warning */}
            <div className="flex items-start gap-2 p-3 bg-warning-50 border border-warning-200 rounded-lg">
              <Clock className="h-5 w-5 text-warning-600 mt-0.5" />
              <div className="text-sm text-warning-700">
                This transaction will be submitted for admin authorization before being marked as
                reconciled.
              </div>
            </div>
          </div>
        )}
        <ModalFooter>
          <Button variant="outline" onClick={closeReconcileModal}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleSubmitReconcile}
            isLoading={manualReconcileMutation.isPending}
            disabled={!selectedReason || (selectedReason === 'Other' && !customReason.trim())}
          >
            Submit for Authorization
          </Button>
        </ModalFooter>
      </Modal>

      {/* Bulk Manual Reconciliation Modal */}
      <Modal
        isOpen={bulkModalOpen}
        onClose={closeBulkModal}
        title="Bulk Manual Reconciliation"
        description={`Reconcile ${selectedIds.size} selected transaction${selectedIds.size !== 1 ? 's' : ''}`}
        size="md"
      >
        <div className="space-y-4">
          {/* Summary */}
          <div className="bg-neutral-50 p-4 rounded-lg">
            <p className="text-sm text-neutral-600">
              <strong>{selectedIds.size}</strong> transaction{selectedIds.size !== 1 ? 's' : ''}{' '}
              selected for manual reconciliation.
            </p>
          </div>

          {/* Reason Selection */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Reason for Manual Reconciliation <span className="text-danger-500">*</span>
            </label>
            <select
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400"
              value={bulkSelectedReason}
              onChange={(e) => setBulkSelectedReason(e.target.value)}
            >
              {RECONCILIATION_REASONS.map((reason) => (
                <option key={reason.value} value={reason.value}>
                  {reason.label}
                </option>
              ))}
            </select>
          </div>

          {/* Custom Reason Input (only shown when "Other" is selected) */}
          {bulkSelectedReason === 'Other' && (
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Specify Reason <span className="text-danger-500">*</span>
              </label>
              <textarea
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400"
                rows={3}
                placeholder="Enter your custom reason..."
                value={bulkCustomReason}
                onChange={(e) => setBulkCustomReason(e.target.value)}
              />
            </div>
          )}

          {/* Warning */}
          <div className="flex items-start gap-2 p-3 bg-warning-50 border border-warning-200 rounded-lg">
            <Clock className="h-5 w-5 text-warning-600 mt-0.5" />
            <div className="text-sm text-warning-700">
              All selected transactions will be submitted for admin authorization before being
              marked as reconciled.
            </div>
          </div>
        </div>
        <ModalFooter>
          <Button variant="outline" onClick={closeBulkModal}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleBulkReconcile}
            isLoading={bulkReconcileMutation.isPending}
            disabled={
              !bulkSelectedReason || (bulkSelectedReason === 'Other' && !bulkCustomReason.trim())
            }
          >
            Submit {selectedIds.size} for Authorization
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  );
}
