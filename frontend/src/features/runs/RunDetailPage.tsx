import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  Hash,
  Calendar,
  User,
  FileSpreadsheet,
  CheckCircle2,
  XCircle,
  RefreshCw,
} from 'lucide-react';
import { runsApi, getErrorMessage } from '@/api';
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Badge,
  PageLoading,
  Alert,
} from '@/components/ui';
import { formatDateTime, formatNumber } from '@/lib/utils';

export function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>();

  const { data: run, isLoading, error } = useQuery({
    queryKey: ['run', runId],
    queryFn: () => runsApi.getById(runId!),
    enabled: !!runId,
  });

  if (isLoading) return <PageLoading />;

  if (error) {
    return (
      <Alert variant="error" title="Error loading run">
        {getErrorMessage(error)}
      </Alert>
    );
  }

  if (!run) {
    return (
      <Alert variant="error" title="Run not found">
        The requested reconciliation run could not be found.
      </Alert>
    );
  }

  const total = run.total_external + run.total_internal;
  const matchRate = total > 0 ? Math.round((run.matched / Math.max(run.total_external, 1)) * 100) : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/runs">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Run Details</h1>
          <p className="text-gray-500 mt-1">View reconciliation run summary</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Run Info */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Run Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Hash className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Run ID</p>
                  <p className="font-mono text-sm">{run.run_id}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <Calendar className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Created At</p>
                  <p>{run.created_at ? formatDateTime(run.created_at) : '-'}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <User className="h-5 w-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Created By</p>
                  <p>{run.created_by || 'System'}</p>
                </div>
              </div>
              <div>
                <p className="text-sm text-gray-500 mb-2">Gateway</p>
                <Badge variant="default" className="capitalize text-sm">{run.gateway}</Badge>
              </div>
              <div>
                <p className="text-sm text-gray-500 mb-2">Status</p>
                <Badge variant="success" className="text-sm">{run.status}</Badge>
              </div>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-cyan-100 rounded-lg">
                  <FileSpreadsheet className="h-5 w-5 text-cyan-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Transaction Count</p>
                  <p>{formatNumber(run.transaction_count)}</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Quick Links */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Links</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Link to={`/transactions?run_id=${run.run_id}&gateway=${run.gateway}`} className="block">
              <Button variant="outline" className="w-full justify-start">
                <FileSpreadsheet className="h-4 w-4 mr-2" />
                View Transactions
              </Button>
            </Link>
            <Link to={`/reports?gateway=${run.gateway}`} className="block">
              <Button variant="outline" className="w-full justify-start">
                <FileSpreadsheet className="h-4 w-4 mr-2" />
                Download Report
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-3xl font-bold text-blue-700">{formatNumber(run.total_external)}</p>
            <p className="text-sm text-blue-600 mt-1">External Records</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-3xl font-bold text-purple-700">{formatNumber(run.total_internal)}</p>
            <p className="text-sm text-purple-600 mt-1">Internal Records</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <div className="flex items-center justify-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-green-600" />
              <p className="text-3xl font-bold text-green-700">{formatNumber(run.matched)}</p>
            </div>
            <p className="text-sm text-green-600 mt-1">Matched ({matchRate}%)</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <div className="flex items-center justify-center gap-2">
              <RefreshCw className="h-5 w-5 text-blue-600" />
              <p className="text-3xl font-bold text-blue-700">{formatNumber(run.carry_forward_matched)}</p>
            </div>
            <p className="text-sm text-blue-600 mt-1">Carry-Forward Matched</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardContent className="pt-6 text-center">
            <div className="flex items-center justify-center gap-2">
              <XCircle className="h-5 w-5 text-orange-600" />
              <p className="text-3xl font-bold text-orange-700">{formatNumber(run.unmatched_external)}</p>
            </div>
            <p className="text-sm text-orange-600 mt-1">Unmatched External</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <div className="flex items-center justify-center gap-2">
              <XCircle className="h-5 w-5 text-red-600" />
              <p className="text-3xl font-bold text-red-700">{formatNumber(run.unmatched_internal)}</p>
            </div>
            <p className="text-sm text-red-600 mt-1">Unmatched Internal</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
