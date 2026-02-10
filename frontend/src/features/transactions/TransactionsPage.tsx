import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { Search, ChevronLeft, ChevronRight, FileSpreadsheet } from 'lucide-react';
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
import { formatDate, formatCurrency, cn } from '@/lib/utils';

export function TransactionsPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  // State
  const [selectedGateway, setSelectedGateway] = useState(searchParams.get('gateway') || '');
  const [dateFrom, setDateFrom] = useState(searchParams.get('date_from') || '');
  const [dateTo, setDateTo] = useState(searchParams.get('date_to') || '');
  const [searchInput, setSearchInput] = useState(searchParams.get('search') || '');
  const [page, setPage] = useState(parseInt(searchParams.get('page') || '1'));
  const [pageSize, setPageSize] = useState(parseInt(searchParams.get('page_size') || '25'));

  // Fetch filter options (gateways, run_ids, statuses, types)
  const { data: filterOptions } = useQuery({
    queryKey: ['transaction-filters'],
    queryFn: () => transactionsApi.getFilterOptions(),
    staleTime: 30000,
  });

  // Build unique base gateways from filter options
  const getBaseGateway = (gateway: string) => {
    return gateway.replace(/_internal$/, '').replace(/_external$/, '');
  };

  const uniqueBaseGateways = useMemo(() => {
    if (!filterOptions?.gateways) return [];
    const gateways = filterOptions.gateways.map((g) => getBaseGateway(g));
    return Array.from(new Set(gateways));
  }, [filterOptions?.gateways]);

  // Build filters for transactions API - excluding charges
  const filters: TransactionFilters = useMemo(() => {
    const f: TransactionFilters = {
      page,
      page_size: pageSize,
    };
    if (selectedGateway) f.gateway = selectedGateway;
    if (dateFrom) f.date_from = dateFrom;
    if (dateTo) f.date_to = dateTo;
    if (searchInput) f.search = searchInput;
    return f;
  }, [page, pageSize, selectedGateway, dateFrom, dateTo, searchInput]);

  // Fetch transactions
  const {
    data: transactionsData,
    isLoading: transactionsLoading,
    error: transactionsError,
  } = useQuery({
    queryKey: ['transactions', filters],
    queryFn: () => transactionsApi.list(filters),
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

  // Update URL params when filters change
  const updateUrlParams = (overrides: Record<string, string>) => {
    const params: Record<string, string> = {};
    const merged = {
      gateway: selectedGateway,
      date_from: dateFrom,
      date_to: dateTo,
      search: searchInput,
      page: String(page),
      page_size: String(pageSize),
      ...overrides,
    };
    if (merged.gateway) params.gateway = merged.gateway;
    if (merged.date_from) params.date_from = merged.date_from;
    if (merged.date_to) params.date_to = merged.date_to;
    if (merged.search) params.search = merged.search;
    if (merged.page && merged.page !== '1') params.page = merged.page;
    if (merged.page_size && merged.page_size !== '25') params.page_size = merged.page_size;
    setSearchParams(params);
  };

  const handleGatewayChange = (value: string) => {
    setSelectedGateway(value);
    setPage(1);
    updateUrlParams({ gateway: value, page: '1' });
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    updateUrlParams({ page: '1' });
  };

  // Pagination helpers
  const pagination = transactionsData?.pagination;
  const goToPage = (newPage: number) => {
    setPage(newPage);
    updateUrlParams({ page: String(newPage) });
  };

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Transactions</h1>
        <p className="text-gray-500 mt-1">
          Browse and search all transactions across gateways
        </p>
      </div>

      {/* Top Controls */}
      <div className="flex items-end justify-between gap-4 flex-wrap">
        {/* Left: Gateway and Date selectors */}
        <div className="flex items-end gap-4 flex-wrap">
          {/* Gateway Selector */}
          <div className="space-y-1">
            <label className="block text-sm font-medium text-gray-700">Gateway</label>
            <select
              value={selectedGateway}
              onChange={(e) => handleGatewayChange(e.target.value)}
              className={cn(
                'w-48 px-3 py-2 border rounded-lg bg-white',
                'focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400'
              )}
            >
              <option value="">All Gateways</option>
              {uniqueBaseGateways.map((gw) => (
                <option key={gw} value={gw}>
                  {gw.charAt(0).toUpperCase() + gw.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {/* Date Range */}
          <div className="space-y-1">
            <label className="block text-sm font-medium text-gray-700">From</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => {
                setDateFrom(e.target.value);
                setPage(1);
              }}
              className="w-40 px-3 py-2 border rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400"
            />
          </div>
          <div className="space-y-1">
            <label className="block text-sm font-medium text-gray-700">To</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => {
                setDateTo(e.target.value);
                setPage(1);
              }}
              className="w-40 px-3 py-2 border rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400"
            />
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
                          : 'No transactions found'
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
