import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Wallet,
  ArrowUpDown,
  AlertTriangle,
  TrendingUp,
  Receipt,
  Clock,
  FileCheck,
  Filter,
} from 'lucide-react';
import { dashboardApi } from '@/api';
import { Card, CardContent, PageLoading, Alert, Button, Select } from '@/components/ui';
import type { SelectOption } from '@/components/ui/Select';

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-KE', {
    style: 'currency',
    currency: 'KES',
    minimumFractionDigits: 2,
  }).format(amount);
}

export function DashboardPage() {
  const [selectedBatch, setSelectedBatch] = useState<string>('');
  const [selectedGateway, setSelectedGateway] = useState<string>('');

  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['dashboard-stats', selectedBatch, selectedGateway],
    queryFn: () => dashboardApi.getStats(
      selectedBatch || undefined,
      selectedGateway || undefined
    ),
    staleTime: 0,
    gcTime: 0,
  });

  const handleClearFilters = () => {
    setSelectedBatch('');
    setSelectedGateway('');
  };

  if (isLoading) {
    return <PageLoading />;
  }

  if (error) {
    return (
      <Alert variant="error" title="Error loading dashboard">
        Failed to load dashboard statistics. Please try again.
      </Alert>
    );
  }

  const hasFilters = selectedBatch || selectedGateway;

  // Build batch options from available batches
  const batchOptions: SelectOption[] = [
    { value: '', label: 'All Batches' },
    ...(stats?.filters.available_batches || []).map((b) => ({
      value: b.batch_id,
      label: `${b.batch_id} (${b.status})`,
    })),
  ];

  // Build gateway options from available gateways
  const gatewayOptions: SelectOption[] = [
    { value: '', label: 'All Gateways' },
    ...(stats?.filters.available_gateways || []).map((g) => ({
      value: g,
      label: g.charAt(0).toUpperCase() + g.slice(1),
    })),
  ];

  // Calculate total gateway payouts (reconciled external + internal)
  const gatewayPayoutsCount = (stats?.reconciled.external.count || 0) + (stats?.reconciled.internal.count || 0);
  const gatewayPayoutsAmount = (stats?.reconciled.external.amount || 0) + (stats?.reconciled.internal.amount || 0);

  // Calculate total unreconciled payouts
  const unreconciledCount = (stats?.unreconciled.external.count || 0) + (stats?.unreconciled.internal.count || 0);
  const unreconciledAmount = (stats?.unreconciled.external.amount || 0) + (stats?.unreconciled.internal.amount || 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Dashboard</h1>
          <p className="text-neutral-500 mt-1">Transaction insights and reconciliation overview</p>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <Filter className="h-5 w-5 text-neutral-400" />
              <span className="text-sm font-medium text-neutral-700">Filters:</span>
            </div>
            <div className="w-64">
              <Select
                options={batchOptions}
                value={selectedBatch}
                onChange={(e) => setSelectedBatch(e.target.value)}
              />
            </div>
            <div className="w-48">
              <Select
                options={gatewayOptions}
                value={selectedGateway}
                onChange={(e) => setSelectedGateway(e.target.value)}
              />
            </div>
            {hasFilters && (
              <Button variant="outline" size="sm" onClick={handleClearFilters}>
                Clear Filters
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Main Stats Grid - 3 columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Wallet Top-Ups Tile */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-start gap-4">
              <div className="p-3 rounded-xl bg-purple-500">
                <Wallet className="h-6 w-6 text-white" />
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-medium text-neutral-500 mb-2">Wallet Top-Ups</h3>
                <p className="text-3xl font-bold text-neutral-900">
                  {stats?.wallet_topups.count.toLocaleString() || 0}
                </p>
                <p className="text-lg text-neutral-600 mt-1">
                  {formatCurrency(stats?.wallet_topups.total_amount || 0)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Gateway Payouts Tile (Reconciled) */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-start gap-4">
              <div className="p-3 rounded-xl bg-success-500">
                <ArrowUpDown className="h-6 w-6 text-white" />
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-medium text-neutral-500 mb-2">Gateway Payouts</h3>
                <p className="text-3xl font-bold text-neutral-900">
                  {gatewayPayoutsCount.toLocaleString()}
                </p>
                <p className="text-lg text-neutral-600 mt-1">
                  {formatCurrency(gatewayPayoutsAmount)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Unreconciled Payouts Tile */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-start gap-4">
              <div className="p-3 rounded-xl bg-error-500">
                <AlertTriangle className="h-6 w-6 text-white" />
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-medium text-neutral-500 mb-2">Unreconciled Payouts</h3>
                <p className="text-3xl font-bold text-neutral-900">
                  {unreconciledCount.toLocaleString()}
                </p>
                <p className="text-lg text-neutral-600 mt-1">
                  {formatCurrency(unreconciledAmount)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Secondary Stats Row - 4 columns */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Reconciliation Rate */}
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-success-100 rounded-lg">
                <TrendingUp className="h-5 w-5 text-success-600" />
              </div>
              <div>
                <p className="text-xs text-neutral-500">Reconciliation Rate</p>
                <p className="text-xl font-bold text-success-600">
                  {stats?.additional_insights.reconciliation_rate || 0}%
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Bank Charges */}
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-orange-100 rounded-lg">
                <Receipt className="h-5 w-5 text-orange-600" />
              </div>
              <div>
                <p className="text-xs text-neutral-500">Bank Charges</p>
                <p className="text-xl font-bold text-neutral-900">
                  {stats?.additional_insights.charges.count.toLocaleString() || 0}
                </p>
                <p className="text-xs text-neutral-500">
                  {formatCurrency(stats?.additional_insights.charges.amount || 0)}
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
                  {stats?.additional_insights.manually_reconciled.toLocaleString() || 0}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Pending Approvals */}
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-100 rounded-lg">
                <Clock className="h-5 w-5 text-amber-600" />
              </div>
              <div>
                <p className="text-xs text-neutral-500">Pending Approvals</p>
                <p className="text-xl font-bold text-amber-600">
                  {stats?.additional_insights.pending_authorizations.toLocaleString() || 0}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
