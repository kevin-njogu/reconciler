import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { CheckCircle2, Clock, AlertCircle } from 'lucide-react';
import { operationsApi, getErrorMessage } from '@/api';
import type { UnreconciledTransaction } from '@/api/operations';
import {
  Button,
  PageLoading,
  Alert,
  Modal,
  ModalFooter,
} from '@/components/ui';
import { useToast } from '@/hooks/useToast';
import { formatCurrency } from '@/lib/utils';
import { SimpleSideBySideView } from './SimpleSideBySideView';

// Transaction type options by gateway side
const EXTERNAL_TRANSACTION_TYPES = [
  { value: '', label: 'Select type...' },
  { value: 'deposit', label: 'Deposit' },
  { value: 'debit', label: 'Debit' },
  { value: 'charge', label: 'Charge' },
];

const INTERNAL_TRANSACTION_TYPES = [
  { value: '', label: 'Select type...' },
  { value: 'payout', label: 'Payout' },
  { value: 'refund', label: 'Refund' },
];

function getTransactionTypeOptions(gateway: string) {
  if (gateway.endsWith('_internal')) return INTERNAL_TRANSACTION_TYPES;
  return EXTERNAL_TRANSACTION_TYPES;
}

export function OperationsPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();

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
  const [selectedTxnType, setSelectedTxnType] = useState('');
  const [comment, setComment] = useState('');

  // Bulk modal state
  const [bulkModalOpen, setBulkModalOpen] = useState(false);
  const [bulkTxnType, setBulkTxnType] = useState('');
  const [bulkComment, setBulkComment] = useState('');

  // Fetch unreconciled transactions
  const {
    data: unreconciledData,
    isLoading: unreconciledLoading,
    error: unreconciledError,
  } = useQuery({
    queryKey: ['unreconciled', selectedGateway],
    queryFn: () => operationsApi.getUnreconciled(selectedGateway || undefined),
  });

  // Manual reconciliation mutation
  const manualReconcileMutation = useMutation({
    mutationFn: ({ transactionId, transactionType, note }: { transactionId: number; transactionType: string; note: string }) =>
      operationsApi.manualReconcile(transactionId, transactionType, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['unreconciled'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['pending-authorization'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['transactions'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'], refetchType: 'all' });
      toast.success('Transaction submitted for authorization');
      closeReconcileModal();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  // Bulk manual reconciliation mutation
  const bulkReconcileMutation = useMutation({
    mutationFn: ({ transactionIds, transactionType, note }: { transactionIds: number[]; transactionType: string; note: string }) =>
      operationsApi.manualReconcileBulk(transactionIds, transactionType, note),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['unreconciled'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['pending-authorization'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['transactions'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'], refetchType: 'all' });
      toast.success(data.message);
      closeBulkModal();
      setSelectedIds(new Set());
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const handleGatewayChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const gateway = e.target.value;
    setSelectedGateway(gateway);
    setSelectedIds(new Set());
    setSearchParams(gateway ? { gateway } : {});
  };

  const openReconcileModal = (transaction: UnreconciledTransaction) => {
    setSelectedTransaction(transaction);
    setSelectedTxnType('');
    setComment('');
    setReconcileModalOpen(true);
  };

  const closeReconcileModal = () => {
    setReconcileModalOpen(false);
    setSelectedTransaction(null);
    setSelectedTxnType('');
    setComment('');
  };

  const handleSubmitReconcile = () => {
    if (!selectedTransaction || !selectedTxnType) {
      toast.error('Please select a transaction type');
      return;
    }
    if (!comment.trim()) {
      toast.error('Please enter a comment');
      return;
    }
    manualReconcileMutation.mutate({
      transactionId: selectedTransaction.id,
      transactionType: selectedTxnType,
      note: comment.trim(),
    });
  };

  // Bulk modal functions
  const openBulkModal = () => {
    if (selectedIds.size === 0) {
      toast.error('Please select at least one transaction');
      return;
    }
    setBulkTxnType('');
    setBulkComment('');
    setBulkModalOpen(true);
  };

  const closeBulkModal = () => {
    setBulkModalOpen(false);
    setBulkTxnType('');
    setBulkComment('');
  };

  const handleBulkReconcile = () => {
    if (!bulkTxnType) {
      toast.error('Please select a transaction type');
      return;
    }
    if (!bulkComment.trim()) {
      toast.error('Please enter a comment');
      return;
    }
    bulkReconcileMutation.mutate({
      transactionIds: Array.from(selectedIds),
      transactionType: bulkTxnType,
      note: bulkComment.trim(),
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
    { value: '', label: 'All gateways' },
    ...uniqueBaseGateways.map((g) => ({
      value: g,
      label: g.charAt(0).toUpperCase() + g.slice(1),
    })),
  ];

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
        <div className="flex items-center gap-3">
          <select
            className="px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400"
            value={selectedGateway}
            onChange={handleGatewayChange}
          >
            {gatewayOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          {selectedIds.size > 0 && (
            <>
              <span className="text-sm text-gray-600">{selectedIds.size} selected</span>
              <Button variant="primary" onClick={openBulkModal}>
                <CheckCircle2 className="h-4 w-4 mr-2" />
                Reconcile Selected
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Content */}
      {unreconciledLoading ? (
        <PageLoading />
      ) : unreconciledError ? (
        <Alert variant="error" title="Error loading transactions">
          {getErrorMessage(unreconciledError)}
        </Alert>
      ) : unreconciledData?.total_count === 0 ? (
        <Alert variant="success" title="All transactions reconciled">
          There are no unreconciled transactions{selectedGateway ? ` for ${selectedGateway}` : ''}.
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
        description="Classify and reconcile this transaction"
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

            {/* Transaction Type Selection */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Transaction Type <span className="text-danger-500">*</span>
              </label>
              <select
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400"
                value={selectedTxnType}
                onChange={(e) => setSelectedTxnType(e.target.value)}
              >
                {getTransactionTypeOptions(selectedTransaction.gateway).map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            {/* Comment */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Comment <span className="text-danger-500">*</span>
              </label>
              <textarea
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400"
                rows={3}
                placeholder="Reason for manual reconciliation..."
                value={comment}
                onChange={(e) => setComment(e.target.value)}
              />
            </div>

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
            disabled={!selectedTxnType || !comment.trim()}
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

          {/* Transaction Type Selection */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Transaction Type <span className="text-danger-500">*</span>
            </label>
            <select
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400"
              value={bulkTxnType}
              onChange={(e) => setBulkTxnType(e.target.value)}
            >
              <option value="">Select type...</option>
              <option value="deposit">Deposit</option>
              <option value="debit">Debit</option>
              <option value="charge">Charge</option>
              <option value="payout">Payout</option>
              <option value="refund">Refund</option>
            </select>
          </div>

          {/* Comment */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Comment <span className="text-danger-500">*</span>
            </label>
            <textarea
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400"
              rows={3}
              placeholder="Reason for manual reconciliation..."
              value={bulkComment}
              onChange={(e) => setBulkComment(e.target.value)}
            />
          </div>

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
            disabled={!bulkTxnType || !bulkComment.trim()}
          >
            Submit {selectedIds.size} for Authorization
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  );
}
