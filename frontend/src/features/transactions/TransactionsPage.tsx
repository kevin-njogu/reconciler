import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import {
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  FileSpreadsheet,
} from 'lucide-react';
import { transactionsApi, getErrorMessage } from '@/api';
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
import { formatDateTime, formatCurrency } from '@/lib/utils';

export function TransactionsPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  // Filters from URL
  const [filters, setFilters] = useState<TransactionFilters>({
    page: parseInt(searchParams.get('page') || '1'),
    page_size: parseInt(searchParams.get('page_size') || '25'),
    search: searchParams.get('search') || '',
    gateway: searchParams.get('gateway') || '',
    batch_id: searchParams.get('batch_id') || '',
    reconciliation_status: searchParams.get('reconciliation_status') || '',
    transaction_type: searchParams.get('transaction_type') || '',
  });

  // Search input state (separate from filters to allow typing without immediate API calls)
  const [searchInput, setSearchInput] = useState(filters.search || '');

  // Fetch filter options
  const { data: filterOptions, isLoading: filterOptionsLoading } = useQuery({
    queryKey: ['transaction-filters'],
    queryFn: () => transactionsApi.getFilterOptions(),
  });

  // Fetch transactions
  const {
    data: transactionsData,
    isLoading: transactionsLoading,
    error: transactionsError,
    refetch,
  } = useQuery({
    queryKey: ['transactions', filters],
    queryFn: () => transactionsApi.list(filters),
  });

  // Update URL params and filters
  const updateFilters = (newFilters: Partial<TransactionFilters>) => {
    const updated = { ...filters, ...newFilters };
    // Reset to page 1 when filters change (except when changing page)
    if (!('page' in newFilters)) {
      updated.page = 1;
    }
    setFilters(updated);

    // Update URL
    const params: Record<string, string> = {};
    if (updated.page && updated.page > 1) params.page = String(updated.page);
    if (updated.page_size && updated.page_size !== 25) params.page_size = String(updated.page_size);
    if (updated.search) params.search = updated.search;
    if (updated.gateway) params.gateway = updated.gateway;
    if (updated.batch_id) params.batch_id = updated.batch_id;
    if (updated.reconciliation_status) params.reconciliation_status = updated.reconciliation_status;
    if (updated.transaction_type) params.transaction_type = updated.transaction_type;
    setSearchParams(params);
  };

  // Handle search submit
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    updateFilters({ search: searchInput });
  };

  // Clear all filters
  const clearFilters = () => {
    setSearchInput('');
    setFilters({
      page: 1,
      page_size: 25,
      search: '',
      gateway: '',
      batch_id: '',
      reconciliation_status: '',
      transaction_type: '',
    });
    setSearchParams({});
  };

  // Pagination helpers
  const pagination = transactionsData?.pagination;
  const goToPage = (page: number) => updateFilters({ page });

  // Build filter options for selects
  const gatewayOptions = [
    { value: '', label: 'All Gateways' },
    ...(filterOptions?.gateways.map((g) => ({
      value: g,
      label: g.charAt(0).toUpperCase() + g.slice(1).replace('_', ' '),
    })) || []),
  ];

  const batchOptions = [
    { value: '', label: 'All Batches' },
    ...(filterOptions?.batch_ids.map((b) => ({
      value: b,
      label: b,
    })) || []),
  ];

  const statusOptions = [
    { value: '', label: 'All Statuses' },
    ...(filterOptions?.reconciliation_statuses.map((s) => ({
      value: s,
      label: s.charAt(0).toUpperCase() + s.slice(1),
    })) || []),
  ];

  const typeOptions = [
    { value: '', label: 'All Types' },
    ...(filterOptions?.transaction_types.map((t) => ({
      value: t,
      label: t.charAt(0).toUpperCase() + t.slice(1),
    })) || []),
  ];

  const pageSizeOptions = [
    { value: '10', label: '10 per page' },
    { value: '25', label: '25 per page' },
    { value: '50', label: '50 per page' },
    { value: '100', label: '100 per page' },
  ];

  // Check if any filters are active
  const hasActiveFilters =
    filters.search ||
    filters.gateway ||
    filters.batch_id ||
    filters.reconciliation_status ||
    filters.transaction_type;

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

  // Get badge variant based on transaction type
  const getTypeBadge = (type: string | null) => {
    if (!type) return <Badge variant="info">-</Badge>;
    switch (type.toLowerCase()) {
      case 'debit':
        return <Badge variant="danger">Debit</Badge>;
      case 'credit':
        return <Badge variant="success">Credit</Badge>;
      case 'charge':
        return <Badge variant="warning">Charge</Badge>;
      case 'payout':
        return <Badge variant="info">Payout</Badge>;
      default:
        return <Badge variant="info">{type}</Badge>;
    }
  };

  if (filterOptionsLoading) return <PageLoading />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Transactions</h1>
          <p className="text-gray-500 mt-1">
            Browse and search all transactions across gateways and batches
          </p>
        </div>
        <Button variant="outline" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Filters Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Search Bar */}
            <form onSubmit={handleSearch} className="flex gap-2">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search by Transaction ID..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400"
                />
              </div>
              <Button type="submit" variant="primary">
                Search
              </Button>
            </form>

            {/* Filter Dropdowns */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Select
                label="Gateway"
                options={gatewayOptions}
                value={filters.gateway || ''}
                onChange={(e) => updateFilters({ gateway: e.target.value })}
              />
              <Select
                label="Batch"
                options={batchOptions}
                value={filters.batch_id || ''}
                onChange={(e) => updateFilters({ batch_id: e.target.value })}
              />
              <Select
                label="Status"
                options={statusOptions}
                value={filters.reconciliation_status || ''}
                onChange={(e) => updateFilters({ reconciliation_status: e.target.value })}
              />
              <Select
                label="Type"
                options={typeOptions}
                value={filters.transaction_type || ''}
                onChange={(e) => updateFilters({ transaction_type: e.target.value })}
              />
            </div>

            {/* Clear Filters Button */}
            {hasActiveFilters && (
              <div className="flex justify-end">
                <Button variant="outline" size="sm" onClick={clearFilters}>
                  Clear All Filters
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {transactionsLoading ? (
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
                    ({pagination.total_count.toLocaleString()} total)
                  </span>
                )}
              </CardTitle>
              <Select
                options={pageSizeOptions}
                value={String(filters.page_size || 25)}
                onChange={(e) => updateFilters({ page_size: parseInt(e.target.value) })}
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
                    <TableHead>Details</TableHead>
                    <TableHead>Gateway</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead className="text-right">Debit</TableHead>
                    <TableHead className="text-right">Credit</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Note</TableHead>
                    <TableHead>Batch</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {!transactionsData?.transactions.length ? (
                    <TableEmpty
                      message={
                        hasActiveFilters
                          ? 'No transactions match your filters'
                          : 'No transactions found'
                      }
                      colSpan={10}
                    />
                  ) : (
                    transactionsData.transactions.map((txn) => (
                      <TableRow key={txn.id}>
                        <TableCell className="text-gray-500 whitespace-nowrap">
                          {txn.date ? formatDateTime(txn.date) : '-'}
                        </TableCell>
                        <TableCell>
                          <span className="font-mono text-sm">{txn.transaction_id || '-'}</span>
                        </TableCell>
                        <TableCell
                          className="max-w-xs truncate"
                          title={txn.narrative || undefined}
                        >
                          {txn.narrative || '-'}
                        </TableCell>
                        <TableCell>
                          <span className="capitalize">
                            {txn.gateway?.replace('_', ' ') || '-'}
                          </span>
                        </TableCell>
                        <TableCell>{getTypeBadge(txn.transaction_type)}</TableCell>
                        <TableCell className="text-right font-mono">
                          {txn.debit ? formatCurrency(txn.debit) : '-'}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {txn.credit ? formatCurrency(txn.credit) : '-'}
                        </TableCell>
                        <TableCell>{getStatusBadge(txn.reconciliation_status)}</TableCell>
                        <TableCell
                          className="max-w-[150px] truncate"
                          title={txn.reconciliation_note || undefined}
                        >
                          {txn.reconciliation_note || '-'}
                        </TableCell>
                        <TableCell>
                          <span className="font-mono text-xs">{txn.batch_id || '-'}</span>
                        </TableCell>
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
                  Showing {((pagination.page - 1) * pagination.page_size) + 1} to{' '}
                  {Math.min(pagination.page * pagination.page_size, pagination.total_count)} of{' '}
                  {pagination.total_count.toLocaleString()} transactions
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
                    {/* Page number buttons */}
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
