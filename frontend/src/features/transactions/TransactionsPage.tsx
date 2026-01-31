import { useState, useEffect, useRef, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { Search, ChevronLeft, ChevronRight, FileSpreadsheet } from 'lucide-react';
import { transactionsApi, reportsApi, getErrorMessage } from '@/api';
import type { TransactionFilters } from '@/api/transactions';
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
  Select,
} from '@/components/ui';
import { formatDate, formatCurrency, cn } from '@/lib/utils';

export function TransactionsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const prevBatchRef = useRef<string | null>(null);

  // State
  const [selectedBatch, setSelectedBatch] = useState(searchParams.get('batch_id') || '');
  const [selectedGateway, setSelectedGateway] = useState(searchParams.get('gateway') || '');
  const [searchInput, setSearchInput] = useState(searchParams.get('search') || '');
  const [batchSearch, setBatchSearch] = useState('');
  const [batchDropdownOpen, setBatchDropdownOpen] = useState(false);
  const [page, setPage] = useState(parseInt(searchParams.get('page') || '1'));
  const [pageSize, setPageSize] = useState(parseInt(searchParams.get('page_size') || '25'));

  // Fetch batches (latest 5 or search results) - instant refresh on mount
  const { data: batchesData, isLoading: batchesLoading } = useQuery({
    queryKey: ['transactionBatches', batchSearch],
    queryFn: () => reportsApi.getBatches(batchSearch || undefined, batchSearch ? 50 : 5),
    staleTime: 0,
    refetchOnMount: 'always',
  });

  // Fetch available gateways when batch is selected - instant refresh
  const { data: gatewaysData, isLoading: gatewaysLoading } = useQuery({
    queryKey: ['availableGateways', selectedBatch],
    queryFn: () => reportsApi.getAvailableGateways(selectedBatch),
    enabled: !!selectedBatch,
    staleTime: 0,
    refetchOnMount: 'always',
  });

  const batches = batchesData?.batches || [];
  const availableGateways = gatewaysData?.gateways || [];

  // Auto-select the latest batch when batches load and no batch is selected
  useEffect(() => {
    if (!selectedBatch && batches.length > 0) {
      setSelectedBatch(batches[0].batch_id);
    }
  }, [batches, selectedBatch]);

  // Build filters for transactions API - excluding charges
  const filters: TransactionFilters = useMemo(() => {
    const f: TransactionFilters = {
      page,
      page_size: pageSize,
    };
    if (selectedBatch) f.batch_id = selectedBatch;
    if (selectedGateway) f.gateway = selectedGateway;
    if (searchInput) f.search = searchInput;
    return f;
  }, [page, pageSize, selectedBatch, selectedGateway, searchInput]);

  // Fetch transactions - instant refresh on mount and filter changes
  const {
    data: transactionsData,
    isLoading: transactionsLoading,
    error: transactionsError,
  } = useQuery({
    queryKey: ['transactions', filters],
    queryFn: () => transactionsApi.list(filters),
    enabled: !!selectedBatch && !!selectedGateway,
    staleTime: 0,
    refetchOnMount: 'always',
  });

  // Filter out charges from the transactions
  const filteredTransactions = useMemo(() => {
    if (!transactionsData?.transactions) return [];
    return transactionsData.transactions.filter(
      (txn) => txn.transaction_type !== 'charge'
    );
  }, [transactionsData?.transactions]);

  // Get unique base gateways
  const getBaseGateway = (gateway: string) => {
    return gateway.replace(/_internal$/, '').replace(/_external$/, '');
  };

  const uniqueBaseGateways = useMemo(() => {
    const gateways = availableGateways.map((g) => getBaseGateway(g.gateway));
    return Array.from(new Set(gateways));
  }, [availableGateways]);

  // Auto-select first gateway when gateways load, or reset when batch changes
  useEffect(() => {
    if (!selectedBatch) return;

    // If batch changed (user picked a different one), reset gateway
    if (prevBatchRef.current !== null && prevBatchRef.current !== selectedBatch) {
      setSelectedGateway('');
      setPage(1);
    }
    prevBatchRef.current = selectedBatch;

    // Auto-select the first gateway if none selected and gateways are available
    if (!selectedGateway && uniqueBaseGateways.length > 0) {
      setSelectedGateway(uniqueBaseGateways[0]);
    }
  }, [selectedBatch, uniqueBaseGateways, selectedGateway]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest('.batch-dropdown')) {
        setBatchDropdownOpen(false);
      }
    };
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);

  // Update URL params
  useEffect(() => {
    const params: Record<string, string> = {};
    if (selectedBatch) params.batch_id = selectedBatch;
    if (selectedGateway) params.gateway = selectedGateway;
    if (searchInput) params.search = searchInput;
    if (page > 1) params.page = String(page);
    if (pageSize !== 25) params.page_size = String(pageSize);
    setSearchParams(params);
  }, [selectedBatch, selectedGateway, searchInput, page, pageSize, setSearchParams]);

  const handleBatchSelect = (batchId: string) => {
    setSelectedBatch(batchId);
    setSelectedGateway('');
    setPage(1);
    setBatchDropdownOpen(false);
    setBatchSearch('');
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1); // Reset to page 1 on new search
  };

  // Pagination helpers
  const pagination = transactionsData?.pagination;
  const goToPage = (newPage: number) => setPage(newPage);

  const pageSizeOptions = [
    { value: '10', label: '10 per page' },
    { value: '25', label: '25 per page' },
    { value: '50', label: '50 per page' },
    { value: '100', label: '100 per page' },
  ];

  // Get badge variant based on status
  const getStatusBadge = (status: string | null) => {
    if (!status) return <Badge variant="info">-</Badge>;
    switch (status.toLowerCase()) {
      case 'reconciled':
        return <Badge variant="success">Reconciled</Badge>;
      case 'unreconciled':
        return <Badge variant="danger">Unreconciled</Badge>;
      default:
        return <Badge variant="info">{status}</Badge>;
    }
  };

  // Get badge for transaction type
  const getTypeBadge = (type: string | null) => {
    if (!type) return <Badge variant="info">-</Badge>;
    switch (type.toLowerCase()) {
      case 'debit':
        return <Badge variant="warning">Debit</Badge>;
      case 'credit':
        return <Badge variant="success">Credit</Badge>;
      default:
        return <Badge variant="info">{type}</Badge>;
    }
  };

  if (batchesLoading) return <PageLoading />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Transactions</h1>
        <p className="text-gray-500 mt-1">
          Browse and search all transactions across gateways and batches
        </p>
      </div>

      {/* Top Controls: Batch & Gateway on left, Search on right */}
      <div className="flex items-end justify-between gap-4">
        {/* Left: Batch and Gateway selectors */}
        <div className="flex items-end gap-4">
          {/* Batch Selector with Search */}
          <div className="space-y-1">
            <label className="block text-sm font-medium text-gray-700">Batch</label>
            <div className="relative batch-dropdown">
              <button
                type="button"
                onClick={() => setBatchDropdownOpen(!batchDropdownOpen)}
                className={cn(
                  'w-64 px-3 py-2 text-left border rounded-lg bg-white',
                  'focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400',
                  'flex items-center justify-between',
                  batchDropdownOpen && 'ring-2 ring-primary-400 border-primary-400'
                )}
              >
                <span className={selectedBatch ? 'text-gray-900 font-mono text-sm' : 'text-gray-500'}>
                  {selectedBatch || 'Select a batch...'}
                </span>
                <svg
                  className={cn(
                    'h-4 w-4 text-gray-400 transition-transform',
                    batchDropdownOpen && 'rotate-180'
                  )}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {batchDropdownOpen && (
                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg">
                  {/* Search Input */}
                  <div className="p-2 border-b">
                    <input
                      type="text"
                      placeholder="Search batch ID..."
                      value={batchSearch}
                      onChange={(e) => setBatchSearch(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-400"
                      onClick={(e) => e.stopPropagation()}
                    />
                  </div>

                  {/* Batch List */}
                  <div className="max-h-48 overflow-y-auto">
                    {batches.length === 0 ? (
                      <div className="px-4 py-3 text-sm text-gray-500 text-center">
                        No batches found
                      </div>
                    ) : (
                      batches.map((batch) => (
                        <button
                          key={batch.batch_id}
                          type="button"
                          onClick={() => handleBatchSelect(batch.batch_id)}
                          className={cn(
                            'w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center justify-between',
                            selectedBatch === batch.batch_id && 'bg-primary-50 text-primary-700'
                          )}
                        >
                          <span className="font-mono">{batch.batch_id}</span>
                          <Badge
                            variant={batch.status === 'completed' ? 'success' : 'warning'}
                            className="text-xs ml-2"
                          >
                            {batch.status === 'completed' ? 'Closed' : 'Pending'}
                          </Badge>
                        </button>
                      ))
                    )}
                  </div>

                  {!batchSearch && batches.length === 5 && (
                    <div className="px-4 py-2 text-xs text-gray-500 border-t bg-gray-50">
                      Showing latest 5 batches. Search to find more.
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Gateway Selector */}
          <div className="space-y-1">
            <label className="block text-sm font-medium text-gray-700">Gateway</label>
            <select
              value={selectedGateway}
              onChange={(e) => {
                setSelectedGateway(e.target.value);
                setPage(1);
              }}
              disabled={!selectedBatch || gatewaysLoading}
              className={cn(
                'w-48 px-3 py-2 border rounded-lg bg-white',
                'focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400',
                'disabled:bg-gray-100 disabled:cursor-not-allowed'
              )}
            >
              <option value="">
                {!selectedBatch
                  ? 'Select batch first'
                  : gatewaysLoading
                    ? 'Loading...'
                    : 'Select gateway...'}
              </option>
              {uniqueBaseGateways.map((gw) => (
                <option key={gw} value={gw}>
                  {gw.charAt(0).toUpperCase() + gw.slice(1)}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Right: Search */}
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search by Reference..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="w-64 pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400"
            />
          </div>
          <Button type="submit" variant="primary">
            Search
          </Button>
        </form>
      </div>

      {/* Content */}
      {!selectedBatch ? (
        <Alert variant="info" title="Select a batch">
          Please select a batch to view transactions.
        </Alert>
      ) : !selectedGateway ? (
        <Alert variant="info" title="Select a gateway">
          Please select a gateway to view transactions.
        </Alert>
      ) : transactionsLoading ? (
        <PageLoading />
      ) : transactionsError ? (
        <Alert variant="error" title="Error loading transactions">
          {getErrorMessage(transactionsError)}
        </Alert>
      ) : (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <FileSpreadsheet className="h-5 w-5" />
                Transactions
                {pagination && (
                  <span className="text-sm font-normal text-gray-500">
                    ({filteredTransactions.length} shown, {pagination.total_count.toLocaleString()} total)
                  </span>
                )}
              </CardTitle>
              <Select
                options={pageSizeOptions}
                value={String(pageSize)}
                onChange={(e) => {
                  setPageSize(parseInt(e.target.value));
                  setPage(1);
                }}
                className="w-32"
              />
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Reference</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Type</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {!filteredTransactions.length ? (
                    <TableEmpty
                      message={
                        searchInput
                          ? 'No transactions match your search'
                          : 'No transactions found for this batch and gateway'
                      }
                      colSpan={5}
                    />
                  ) : (
                    filteredTransactions.map((txn) => (
                      <TableRow key={txn.id}>
                        <TableCell className="text-gray-500 whitespace-nowrap">
                          {txn.date ? formatDate(txn.date) : '-'}
                        </TableCell>
                        <TableCell>
                          <span className="font-mono text-sm">{txn.transaction_id || '-'}</span>
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {txn.amount ? formatCurrency(txn.amount) : '-'}
                        </TableCell>
                        <TableCell>{getStatusBadge(txn.reconciliation_status)}</TableCell>
                        <TableCell>{getTypeBadge(txn.transaction_type)}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>

            {/* Pagination */}
            {pagination && pagination.total_pages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
                <div className="text-sm text-gray-500">
                  Page {pagination.page} of {pagination.total_pages}
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => goToPage(pagination.page - 1)}
                    disabled={!pagination.has_previous}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Previous
                  </Button>
                  <div className="flex items-center gap-1">
                    {Array.from({ length: Math.min(5, pagination.total_pages) }, (_, i) => {
                      let pageNum: number;
                      if (pagination.total_pages <= 5) {
                        pageNum = i + 1;
                      } else if (pagination.page <= 3) {
                        pageNum = i + 1;
                      } else if (pagination.page >= pagination.total_pages - 2) {
                        pageNum = pagination.total_pages - 4 + i;
                      } else {
                        pageNum = pagination.page - 2 + i;
                      }
                      return (
                        <Button
                          key={pageNum}
                          variant={pageNum === pagination.page ? 'primary' : 'outline'}
                          size="sm"
                          onClick={() => goToPage(pageNum)}
                          className="w-8 px-0"
                        >
                          {pageNum}
                        </Button>
                      );
                    })}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => goToPage(pagination.page + 1)}
                    disabled={!pagination.has_next}
                  >
                    Next
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
