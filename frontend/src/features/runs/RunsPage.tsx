import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ChevronLeft,
  ChevronRight,
  User,
  History,
} from 'lucide-react';
import { runsApi, getErrorMessage } from '@/api';
import type { RunListParams } from '@/api/runs';
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
import { formatDateTime } from '@/lib/utils';

const pageSizeOptions = [
  { value: '10', label: '10 per page' },
  { value: '25', label: '25 per page' },
  { value: '50', label: '50 per page' },
];

export function RunsPage() {
  const navigate = useNavigate();

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [gatewayFilter, setGatewayFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const params: RunListParams = {
    page,
    page_size: pageSize,
  };
  if (gatewayFilter) params.gateway = gatewayFilter;
  if (dateFrom) params.date_from = dateFrom;
  if (dateTo) params.date_to = dateTo;

  const { data, isLoading, error } = useQuery({
    queryKey: ['runs', params],
    queryFn: () => runsApi.list(params),
  });

  if (isLoading) return <PageLoading />;

  if (error) {
    return (
      <Alert variant="error" title="Error loading runs">
        {getErrorMessage(error)}
      </Alert>
    );
  }

  const runs = data?.runs || [];
  const pagination = data?.pagination;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Reconciliation Runs</h1>
        <p className="text-gray-500 mt-1">View history of reconciliation runs</p>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-end gap-4 flex-wrap">
            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-700">Gateway</label>
              <input
                type="text"
                placeholder="Filter by gateway..."
                value={gatewayFilter}
                onChange={(e) => { setGatewayFilter(e.target.value); setPage(1); }}
                className="w-48 px-3 py-2 border rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400"
              />
            </div>
            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-700">From</label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => { setDateFrom(e.target.value); setPage(1); }}
                className="w-44 px-3 py-2 border rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400"
              />
            </div>
            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-700">To</label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => { setDateTo(e.target.value); setPage(1); }}
                className="w-44 px-3 py-2 border rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400"
              />
            </div>
            {(gatewayFilter || dateFrom || dateTo) && (
              <Button variant="outline" size="sm" onClick={() => { setGatewayFilter(''); setDateFrom(''); setDateTo(''); setPage(1); }}>
                Clear
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Runs Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <CardTitle className="flex items-center gap-2">
            <History className="h-5 w-5 text-primary-600" />
            Runs
            {pagination && (
              <span className="text-sm font-normal text-gray-500">
                ({pagination.total_count} total)
              </span>
            )}
          </CardTitle>
          <Select
            options={pageSizeOptions}
            value={String(pageSize)}
            onChange={(e) => { setPageSize(parseInt(e.target.value)); setPage(1); }}
            className="w-32"
          />
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Run ID</TableHead>
                <TableHead>Gateway</TableHead>
                <TableHead className="text-right">Matched</TableHead>
                <TableHead className="text-right">Unmatched Ext</TableHead>
                <TableHead className="text-right">Unmatched Int</TableHead>
                <TableHead className="text-right">Carry-Forward</TableHead>
                <TableHead>Created By</TableHead>
                <TableHead>Date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {runs.length === 0 ? (
                <TableEmpty message="No reconciliation runs found" colSpan={8} />
              ) : (
                runs.map((run) => (
                  <TableRow
                    key={run.run_id}
                    className="cursor-pointer hover:bg-gray-50"
                    onClick={() => navigate(`/runs/${run.run_id}`)}
                  >
                    <TableCell>
                      <span className="font-mono text-sm">{run.run_id}</span>
                    </TableCell>
                    <TableCell>
                      <Badge variant="default" className="capitalize">{run.gateway}</Badge>
                    </TableCell>
                    <TableCell className="text-right font-mono text-green-700">
                      {run.matched}
                    </TableCell>
                    <TableCell className="text-right font-mono text-orange-700">
                      {run.unmatched_external}
                    </TableCell>
                    <TableCell className="text-right font-mono text-red-700">
                      {run.unmatched_internal}
                    </TableCell>
                    <TableCell className="text-right font-mono text-blue-700">
                      {run.carry_forward_matched}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1.5 text-sm text-gray-600">
                        <User className="h-3.5 w-3.5" />
                        {run.created_by || '-'}
                      </div>
                    </TableCell>
                    <TableCell className="text-gray-500 text-sm whitespace-nowrap">
                      {run.created_at ? formatDateTime(run.created_at) : '-'}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>

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
                  onClick={() => setPage(page - 1)}
                  disabled={!pagination.has_previous}
                >
                  <ChevronLeft className="h-4 w-4" />
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(page + 1)}
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
    </div>
  );
}
