import { useQuery } from '@tanstack/react-query';
import {
  TrendingUp,
  Clock,
  XCircle,
  Building2,
  AlertCircle,
} from 'lucide-react';
import { dashboardApi } from '@/api';
import {
  Card,
  CardContent,
  PageLoading,
  Alert,
} from '@/components/ui';
import { formatCurrency, formatNumber, cn } from '@/lib/utils';

function rateColor(rate: number) {
  if (rate >= 90) return { bg: 'bg-green-500', text: 'text-green-600' };
  if (rate >= 70) return { bg: 'bg-amber-500', text: 'text-amber-600' };
  return { bg: 'bg-red-500', text: 'text-red-600' };
}

export function DashboardPage() {
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => dashboardApi.getStats(),
    staleTime: 0,
    refetchOnMount: 'always',
  });

  if (isLoading && !stats) return <PageLoading />;

  const summary = stats?.summary;
  const tiles = stats?.gateway_tiles || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-neutral-900">Dashboard</h1>
        <p className="text-neutral-500 mt-1">Reconciliation overview</p>
      </div>

      {error ? (
        <Alert variant="error" title="Error loading dashboard">
          Failed to load dashboard statistics. Please try again.
        </Alert>
      ) : (
        <>
          {/* Summary Bar */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card>
              <CardContent className="py-4 flex items-center gap-3">
                <div className={cn(
                  'p-2 rounded-lg',
                  (summary?.reconciliation_rate ?? 0) >= 90 ? 'bg-green-100' :
                  (summary?.reconciliation_rate ?? 0) >= 70 ? 'bg-amber-100' : 'bg-red-100'
                )}>
                  <TrendingUp className={cn(
                    'h-5 w-5',
                    (summary?.reconciliation_rate ?? 0) >= 90 ? 'text-green-600' :
                    (summary?.reconciliation_rate ?? 0) >= 70 ? 'text-amber-600' : 'text-red-600'
                  )} />
                </div>
                <div>
                  <p className="text-xs text-neutral-500">Reconciliation Rate</p>
                  <p className={cn(
                    'text-xl font-bold',
                    (summary?.reconciliation_rate ?? 0) >= 90 ? 'text-green-600' :
                    (summary?.reconciliation_rate ?? 0) >= 70 ? 'text-amber-600' : 'text-red-600'
                  )}>
                    {summary?.reconciliation_rate ?? 0}%
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="py-4 flex items-center gap-3">
                <div className={cn(
                  'p-2 rounded-lg',
                  (summary?.pending_authorizations ?? 0) > 0 ? 'bg-amber-100' : 'bg-neutral-100'
                )}>
                  <Clock className={cn(
                    'h-5 w-5',
                    (summary?.pending_authorizations ?? 0) > 0 ? 'text-amber-600' : 'text-neutral-400'
                  )} />
                </div>
                <div>
                  <p className="text-xs text-neutral-500">Pending Approvals</p>
                  <p className={cn(
                    'text-xl font-bold',
                    (summary?.pending_authorizations ?? 0) > 0 ? 'text-amber-600' : 'text-neutral-900'
                  )}>
                    {formatNumber(summary?.pending_authorizations ?? 0)}
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="py-4 flex items-center gap-3">
                <div className={cn(
                  'p-2 rounded-lg',
                  (summary?.unreconciled_count ?? 0) > 0 ? 'bg-red-100' : 'bg-neutral-100'
                )}>
                  <XCircle className={cn(
                    'h-5 w-5',
                    (summary?.unreconciled_count ?? 0) > 0 ? 'text-red-600' : 'text-neutral-400'
                  )} />
                </div>
                <div>
                  <p className="text-xs text-neutral-500">Total Unreconciled Items</p>
                  <p className={cn(
                    'text-xl font-bold',
                    (summary?.unreconciled_count ?? 0) > 0 ? 'text-red-600' : 'text-neutral-900'
                  )}>
                    {formatNumber(summary?.unreconciled_count ?? 0)}
                  </p>
                  <p className="text-xs text-neutral-400">
                    {formatCurrency(summary?.unreconciled_amount ?? 0)}
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Gateway Cards */}
          {tiles.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
              {tiles.map((tile) => (
                <Card key={tile.base_gateway}>
                  <CardContent className="pt-5 pb-5">
                    <div className="space-y-4">
                      {/* Gateway name + unreconciled badge */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Building2 className="h-5 w-5 text-primary-600" />
                          <h3 className="font-semibold text-neutral-800">
                            {tile.display_name}
                          </h3>
                        </div>
                        <span className={cn(
                          'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
                          tile.unreconciled_count > 0
                            ? 'bg-red-50 text-red-700'
                            : 'bg-green-50 text-green-700'
                        )}>
                          {tile.unreconciled_count > 0 && (
                            <AlertCircle className="h-3 w-3" />
                          )}
                          {tile.unreconciled_count} unreconciled
                        </span>
                      </div>

                      {/* Counts */}
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div className="p-3 bg-blue-50 rounded-lg text-center">
                          <p className="text-2xl font-bold text-blue-700">
                            {formatNumber(tile.external_debit_count)}
                          </p>
                          <p className="text-xs text-blue-600 mt-0.5">External Debits</p>
                        </div>
                        <div className="p-3 bg-purple-50 rounded-lg text-center">
                          <p className="text-2xl font-bold text-purple-700">
                            {formatNumber(tile.internal_payout_count)}
                          </p>
                          <p className="text-xs text-purple-600 mt-0.5">Internal Payouts</p>
                        </div>
                      </div>

                      {/* Match rate */}
                      <div>
                        <div className="flex justify-between items-center mb-1.5">
                          <span className="text-xs text-neutral-500">Match Rate</span>
                          <span className={cn('text-sm font-bold', rateColor(tile.matching_percentage).text)}>
                            {tile.matching_percentage}%
                          </span>
                        </div>
                        <div className="w-full bg-neutral-200 rounded-full h-2">
                          <div
                            className={cn('h-2 rounded-full transition-all', rateColor(tile.matching_percentage).bg)}
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
              No transactions found. Run reconciliation to see gateway insights.
            </Alert>
          )}
        </>
      )}
    </div>
  );
}
