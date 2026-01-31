import { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  TrendingUp,
  Receipt,
  Clock,
  FileCheck,
  Building2,
  Layers,
} from 'lucide-react';
import { dashboardApi, reportsApi } from '@/api';
import {
  Card,
  CardContent,
  PageLoading,
  Alert,
  Button,
  Badge,
} from '@/components/ui';
import { formatCurrency, formatNumber, cn, capitalizeFirst } from '@/lib/utils';

export function DashboardPage() {
  const prevBatchRef = useRef<string | null>(null);

  const [selectedBatch, setSelectedBatch] = useState('');
  const [selectedGateway, setSelectedGateway] = useState('');
  const [batchSearch, setBatchSearch] = useState('');
  const [batchDropdownOpen, setBatchDropdownOpen] = useState(false);

  // Fetch batches (latest 5 or search results) - instant refresh
  const { data: batchesData, isLoading: batchesLoading } = useQuery({
    queryKey: ['dashboardBatches', batchSearch],
    queryFn: () => reportsApi.getBatches(batchSearch || undefined, batchSearch ? 50 : 5),
    staleTime: 0,
    refetchOnMount: 'always',
  });

  const batches = batchesData?.batches || [];

  // Auto-select latest batch on load
  useEffect(() => {
    if (!selectedBatch && batches.length > 0) {
      setSelectedBatch(batches[0].batch_id);
    }
  }, [batches, selectedBatch]);

  // Fetch dashboard stats for selected batch - instant refresh
  const { data: stats, isLoading: statsLoading, error } = useQuery({
    queryKey: ['dashboard-stats', selectedBatch, selectedGateway],
    queryFn: () => dashboardApi.getStats(
      selectedBatch || undefined,
      selectedGateway || undefined
    ),
    enabled: !!selectedBatch,
    staleTime: 0,
    refetchOnMount: 'always',
  });

  // Reset gateway when batch changes (only on manual selection, not initial load)
  useEffect(() => {
    if (!selectedBatch) return;
    if (prevBatchRef.current !== null && prevBatchRef.current !== selectedBatch) {
      setSelectedGateway('');
    }
    prevBatchRef.current = selectedBatch;
  }, [selectedBatch]);

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

  const handleBatchSelect = (batchId: string) => {
    setSelectedBatch(batchId);
    setSelectedGateway('');
    setBatchDropdownOpen(false);
    setBatchSearch('');
  };

  const handleClearFilters = () => {
    if (batches.length > 0) {
      setSelectedBatch(batches[0].batch_id);
    }
    setSelectedGateway('');
  };

  // Build gateway filter options from stats
  const gatewayOptions = (stats?.gateway_tiles || []).map((t) => t.base_gateway);

  const hasGatewayFilter = !!selectedGateway;

  if (batchesLoading) return <PageLoading />;

  // Find selected batch status for display
  const selectedBatchInfo = batches.find((b) => b.batch_id === selectedBatch);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-neutral-900">Dashboard</h1>
        <p className="text-neutral-500 mt-1">
          Transaction insights and reconciliation overview
        </p>
      </div>

      {/* Filter Bar */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-end gap-4 flex-wrap">
            {/* Batch Selector with Search */}
            <div className="space-y-1">
              <label className="block text-sm font-medium text-neutral-700">Batch</label>
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
                  <span className={selectedBatch ? 'text-neutral-900 font-mono text-sm' : 'text-neutral-500'}>
                    {selectedBatch || 'Select a batch...'}
                  </span>
                  <svg
                    className={cn(
                      'h-4 w-4 text-neutral-400 transition-transform',
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
                  <div className="absolute z-10 w-full mt-1 bg-white border border-neutral-200 rounded-lg shadow-lg">
                    <div className="p-2 border-b">
                      <input
                        type="text"
                        placeholder="Search batch ID..."
                        value={batchSearch}
                        onChange={(e) => setBatchSearch(e.target.value)}
                        className="w-full px-3 py-2 text-sm border border-neutral-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-400"
                        onClick={(e) => e.stopPropagation()}
                      />
                    </div>
                    <div className="max-h-48 overflow-y-auto">
                      {batches.length === 0 ? (
                        <div className="px-4 py-3 text-sm text-neutral-500 text-center">
                          No batches found
                        </div>
                      ) : (
                        batches.map((batch) => (
                          <button
                            key={batch.batch_id}
                            type="button"
                            onClick={() => handleBatchSelect(batch.batch_id)}
                            className={cn(
                              'w-full px-4 py-2 text-left text-sm hover:bg-neutral-50 flex items-center justify-between',
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
                      <div className="px-4 py-2 text-xs text-neutral-500 border-t bg-neutral-50">
                        Showing latest 5 batches. Search to find more.
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Gateway Filter */}
            <div className="space-y-1">
              <label className="block text-sm font-medium text-neutral-700">Gateway</label>
              <select
                value={selectedGateway}
                onChange={(e) => setSelectedGateway(e.target.value)}
                disabled={!selectedBatch || statsLoading}
                className={cn(
                  'w-48 px-3 py-2 border rounded-lg bg-white',
                  'focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400',
                  'disabled:bg-neutral-100 disabled:cursor-not-allowed'
                )}
              >
                <option value="">All Gateways</option>
                {gatewayOptions.map((gw) => (
                  <option key={gw} value={gw}>
                    {capitalizeFirst(gw)}
                  </option>
                ))}
              </select>
            </div>

            {/* Clear Filters */}
            {hasGatewayFilter && (
              <Button variant="outline" size="sm" onClick={handleClearFilters}>
                Clear Filters
              </Button>
            )}

            {/* Batch status indicator */}
            {selectedBatchInfo && (
              <div className="ml-auto flex items-center gap-2">
                <span className="text-sm text-neutral-500">Status:</span>
                <Badge variant={selectedBatchInfo.status === 'completed' ? 'success' : 'warning'}>
                  {selectedBatchInfo.status === 'completed' ? 'Closed' : 'Pending'}
                </Badge>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Content */}
      {!selectedBatch ? (
        <Alert variant="info" title="No batches available">
          Create a batch to get started with reconciliation.
        </Alert>
      ) : statsLoading ? (
        <PageLoading />
      ) : error ? (
        <Alert variant="error" title="Error loading dashboard">
          Failed to load dashboard statistics. Please try again.
        </Alert>
      ) : (
        <>
          {/* Gateway Tiles Grid */}
          {stats?.gateway_tiles && stats.gateway_tiles.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {stats.gateway_tiles.map((tile) => (
                <Card key={tile.base_gateway}>
                  <CardContent className="pt-6">
                    <div className="space-y-4">
                      {/* Header: Gateway name + unreconciled badge */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className="p-2 bg-primary-100 rounded-lg">
                            <Building2 className="h-5 w-5 text-primary-600" />
                          </div>
                          <h3 className="text-sm font-semibold text-neutral-700">
                            {tile.display_name}
                          </h3>
                        </div>
                        <Badge variant={tile.unreconciled_count > 0 ? 'danger' : 'success'}>
                          {tile.unreconciled_count} unreconciled
                        </Badge>
                      </div>

                      {/* External vs Internal debit counts */}
                      <div className="grid grid-cols-2 gap-3">
                        <div className="p-3 bg-blue-50 rounded-lg">
                          <p className="text-2xl font-bold text-blue-700">
                            {formatNumber(tile.external_debit_count)}
                          </p>
                          <p className="text-xs text-blue-600 mt-1">External (Bank)</p>
                        </div>
                        <div className="p-3 bg-purple-50 rounded-lg">
                          <p className="text-2xl font-bold text-purple-700">
                            {formatNumber(tile.internal_debit_count)}
                          </p>
                          <p className="text-xs text-purple-600 mt-1">Internal (Workpay)</p>
                        </div>
                      </div>

                      {/* Matching percentage with progress bar */}
                      <div>
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-sm text-neutral-500">Match Rate</span>
                          <span className={cn(
                            'text-lg font-bold',
                            tile.matching_percentage >= 90 ? 'text-success-600' :
                            tile.matching_percentage >= 70 ? 'text-warning-600' : 'text-danger-600'
                          )}>
                            {tile.matching_percentage}%
                          </span>
                        </div>
                        <div className="w-full bg-neutral-200 rounded-full h-2.5">
                          <div
                            className={cn(
                              'h-2.5 rounded-full transition-all',
                              tile.matching_percentage >= 90 ? 'bg-success-500' :
                              tile.matching_percentage >= 70 ? 'bg-warning-500' : 'bg-danger-500'
                            )}
                            style={{ width: `${Math.min(tile.matching_percentage, 100)}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Alert variant="info" title="No transactions yet">
              No transactions found in this batch. Run reconciliation to see insights.
            </Alert>
          )}

          {/* Batch-Wide Metrics Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Batch Charges */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-start gap-4">
                  <div className="p-3 rounded-xl bg-orange-100">
                    <Receipt className="h-6 w-6 text-orange-600" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-sm font-medium text-neutral-500 mb-1">
                      Batch Charges (All Gateways)
                    </h3>
                    <p className="text-3xl font-bold text-neutral-900">
                      {formatNumber(stats?.batch_charges.count || 0)}
                    </p>
                    <p className="text-lg text-neutral-600 mt-1">
                      {formatCurrency(stats?.batch_charges.amount || 0)}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Pending Authorizations */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-start gap-4">
                  <div className={cn(
                    'p-3 rounded-xl',
                    (stats?.pending_authorizations || 0) > 0 ? 'bg-amber-100' : 'bg-neutral-100'
                  )}>
                    <Clock className={cn(
                      'h-6 w-6',
                      (stats?.pending_authorizations || 0) > 0 ? 'text-amber-600' : 'text-neutral-400'
                    )} />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-sm font-medium text-neutral-500 mb-1">
                      Pending Authorizations
                    </h3>
                    <p className={cn(
                      'text-3xl font-bold',
                      (stats?.pending_authorizations || 0) > 0 ? 'text-amber-600' : 'text-neutral-900'
                    )}>
                      {formatNumber(stats?.pending_authorizations || 0)}
                    </p>
                    <p className="text-sm text-neutral-500 mt-1">
                      {(stats?.pending_authorizations || 0) > 0
                        ? 'Awaiting admin review'
                        : 'All clear'}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Summary Row */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Reconciliation Rate */}
            <Card>
              <CardContent className="pt-4 pb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-success-100 rounded-lg">
                    <TrendingUp className="h-5 w-5 text-success-600" />
                  </div>
                  <div>
                    <p className="text-xs text-neutral-500">Reconciliation Rate</p>
                    <p className={cn(
                      'text-xl font-bold',
                      (stats?.summary.reconciliation_rate || 0) >= 90 ? 'text-success-600' :
                      (stats?.summary.reconciliation_rate || 0) >= 70 ? 'text-warning-600' : 'text-danger-600'
                    )}>
                      {stats?.summary.reconciliation_rate || 0}%
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Total Reconciled */}
            <Card>
              <CardContent className="pt-4 pb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-success-100 rounded-lg">
                    <Layers className="h-5 w-5 text-success-600" />
                  </div>
                  <div>
                    <p className="text-xs text-neutral-500">Total Reconciled</p>
                    <p className="text-xl font-bold text-neutral-900">
                      {formatNumber(stats?.summary.total_reconciled || 0)}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Manually Reconciled */}
            <Card>
              <CardContent className="pt-4 pb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-teal-100 rounded-lg">
                    <FileCheck className="h-5 w-5 text-teal-600" />
                  </div>
                  <div>
                    <p className="text-xs text-neutral-500">Manually Reconciled</p>
                    <p className="text-xl font-bold text-neutral-900">
                      {formatNumber(stats?.summary.manually_reconciled || 0)}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

          </div>
        </>
      )}
    </div>
  );
}
