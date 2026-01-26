import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Play, CheckCircle, XCircle, ArrowRight, AlertCircle, FileCheck, FileX, ChevronLeft, ChevronRight } from 'lucide-react';
import { batchesApi, reconciliationApi, transactionsApi, getErrorMessage } from '@/api';
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Select,
  Alert,
  PageLoading,
  Badge,
} from '@/components/ui';
import { useToast } from '@/hooks/useToast';
import { formatNumber, formatCurrency } from '@/lib/utils';
import type { ReconciliationResult, AvailableGateway } from '@/types';
import type { TransactionRecord, TransactionPagination } from '@/api/transactions';

export function ReconciliationPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();

  const [selectedBatch, setSelectedBatch] = useState(searchParams.get('batch_id') || '');
  const [selectedGateway, setSelectedGateway] = useState('');
  const [result, setResult] = useState<ReconciliationResult | null>(null);

  // Unreconciled items state
  const [externalPage, setExternalPage] = useState(1);
  const [internalPage, setInternalPage] = useState(1);
  const PAGE_SIZE = 10;

  // Fetch pending batches
  const { data: batchesData, isLoading: batchesLoading } = useQuery({
    queryKey: ['batches', 'pending'],
    queryFn: () => batchesApi.list({ status: 'pending' }),
  });

  const batches = batchesData?.batches;

  // Fetch available gateways for selected batch
  const { data: availableGatewaysData, isLoading: gatewaysLoading, refetch: refetchGateways } = useQuery({
    queryKey: ['available-gateways', selectedBatch],
    queryFn: () => reconciliationApi.getAvailableGateways(selectedBatch),
    enabled: !!selectedBatch,
  });

  const availableGateways = availableGatewaysData?.available_gateways || [];

  // Fetch unreconciled external transactions
  const { data: unreconciledExternalData, refetch: refetchExternalUnreconciled } = useQuery({
    queryKey: ['unreconciled-external', selectedBatch, selectedGateway, externalPage],
    queryFn: () => transactionsApi.list({
      batch_id: selectedBatch,
      gateway: `${selectedGateway}_external`,
      reconciliation_status: 'unreconciled',
      page: externalPage,
      page_size: PAGE_SIZE,
    }),
    enabled: !!result && !!selectedBatch && !!selectedGateway,
  });

  // Fetch unreconciled internal transactions
  const { data: unreconciledInternalData, refetch: refetchInternalUnreconciled } = useQuery({
    queryKey: ['unreconciled-internal', selectedBatch, selectedGateway, internalPage],
    queryFn: () => transactionsApi.list({
      batch_id: selectedBatch,
      gateway: `${selectedGateway}_internal`,
      reconciliation_status: 'unreconciled',
      page: internalPage,
      page_size: PAGE_SIZE,
    }),
    enabled: !!result && !!selectedBatch && !!selectedGateway,
  });

  // Reset gateway selection when batch changes
  useEffect(() => {
    setSelectedGateway('');
    setResult(null);
    setExternalPage(1);
    setInternalPage(1);
  }, [selectedBatch]);

  // Reconcile mutation
  const reconcileMutation = useMutation({
    mutationFn: (params: { batch_id: string; gateway: string }) =>
      reconciliationApi.reconcile(params),
    onSuccess: (data) => {
      setResult(data);
      queryClient.invalidateQueries({ queryKey: ['batches'] });
      queryClient.invalidateQueries({ queryKey: ['available-gateways', selectedBatch] });
      toast.success('Reconciliation completed and saved successfully');
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const handleReconcile = () => {
    if (!selectedBatch || !selectedGateway) {
      toast.error('Please select a batch and gateway');
      return;
    }
    reconcileMutation.mutate({ batch_id: selectedBatch, gateway: selectedGateway });
  };

  const batchOptions = batches?.map((b) => ({
    value: b.batch_id,
    label: b.batch_id,
  })) || [];

  // Build gateway options with status indicators
  const gatewayOptions = availableGateways.map((g: AvailableGateway) => ({
    value: g.gateway,
    label: g.ready_for_reconciliation
      ? `${g.display_name} (Ready)`
      : `${g.display_name} (${g.has_external ? 'External' : 'No External'}, ${g.has_internal ? 'Internal' : 'No Internal'})`,
  }));

  const selectedGatewayInfo = availableGateways.find(
    (g: AvailableGateway) => g.gateway === selectedGateway
  );

  if (batchesLoading) return <PageLoading />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Reconciliation</h1>
        <p className="text-gray-500 mt-1">Match transactions between bank statements and internal records</p>
      </div>

      <div className="space-y-6">
        {/* Reconciliation Form */}
        <Card>
          <CardHeader>
            <CardTitle>Run Reconciliation</CardTitle>
            <CardDescription>
              Select a pending batch and gateway to reconcile transactions
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {batches?.length === 0 ? (
              <Alert variant="warning" title="No pending batches">
                All batches have been reconciled or there are no batches available.
              </Alert>
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Select
                    label="Batch"
                    options={batchOptions}
                    value={selectedBatch}
                    onChange={(e) => setSelectedBatch(e.target.value)}
                    placeholder="Select a pending batch"
                  />
                  <Select
                    label="Gateway"
                    options={gatewayOptions}
                    value={selectedGateway}
                    onChange={(e) => {
                      setSelectedGateway(e.target.value);
                      setResult(null);
                    }}
                    placeholder={selectedBatch ? (gatewaysLoading ? 'Loading...' : 'Select gateway') : 'Select batch first'}
                    disabled={!selectedBatch || gatewaysLoading}
                  />
                </div>

                {/* Gateway File Status */}
                {selectedBatch && selectedGatewayInfo && (
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <h4 className="font-medium mb-3">File Status for {selectedGatewayInfo.display_name}</h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="flex items-center gap-2">
                        {selectedGatewayInfo.has_external ? (
                          <FileCheck className="h-5 w-5 text-green-600" />
                        ) : (
                          <FileX className="h-5 w-5 text-red-500" />
                        )}
                        <span className={selectedGatewayInfo.has_external ? 'text-green-700' : 'text-red-600'}>
                          External: {selectedGatewayInfo.external_file || 'Not uploaded'}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        {selectedGatewayInfo.has_internal ? (
                          <FileCheck className="h-5 w-5 text-green-600" />
                        ) : (
                          <FileX className="h-5 w-5 text-red-500" />
                        )}
                        <span className={selectedGatewayInfo.has_internal ? 'text-green-700' : 'text-red-600'}>
                          Internal: {selectedGatewayInfo.internal_file || 'Not uploaded'}
                        </span>
                      </div>
                    </div>
                    {!selectedGatewayInfo.ready_for_reconciliation && (
                      <Alert variant="warning" title="Missing files" className="mt-4">
                        Both external and internal files are required for reconciliation.
                        <Button
                          variant="outline"
                          size="sm"
                          className="mt-2"
                          onClick={() => navigate(`/upload?batch_id=${selectedBatch}`)}
                        >
                          Go to Upload
                        </Button>
                      </Alert>
                    )}
                  </div>
                )}

                {/* No gateways with files */}
                {selectedBatch && !gatewaysLoading && availableGateways.length === 0 && (
                  <Alert variant="warning" title="No files uploaded">
                    No files have been uploaded for this batch yet.
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-2"
                      onClick={() => navigate(`/upload?batch_id=${selectedBatch}`)}
                    >
                      Go to Upload
                    </Button>
                  </Alert>
                )}

                <div className="flex justify-end">
                  <Button
                    onClick={handleReconcile}
                    disabled={
                      !selectedBatch ||
                      !selectedGateway ||
                      !selectedGatewayInfo?.ready_for_reconciliation ||
                      reconcileMutation.isPending
                    }
                    isLoading={reconcileMutation.isPending}
                  >
                    <Play className="h-4 w-4 mr-2" />
                    Reconcile
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Results */}
        {result && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Reconciliation Results</CardTitle>
                <CardDescription>
                  Batch: {result.batch_id} | Gateway: {result.gateway}
                </CardDescription>
              </div>
              <Badge variant="success">Saved</Badge>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                <div className="text-center p-4 bg-blue-50 rounded-lg">
                  <p className="text-2xl font-bold text-blue-700">{formatNumber(result.summary.total_external)}</p>
                  <p className="text-sm text-blue-600">External Debits</p>
                </div>
                <div className="text-center p-4 bg-purple-50 rounded-lg">
                  <p className="text-2xl font-bold text-purple-700">{formatNumber(result.summary.total_internal)}</p>
                  <p className="text-sm text-purple-600">Internal Records</p>
                </div>
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <p className="text-2xl font-bold text-green-700">{formatNumber(result.summary.matched)}</p>
                  <p className="text-sm text-green-600">Matched</p>
                </div>
                <div className="text-center p-4 bg-orange-50 rounded-lg">
                  <p className="text-2xl font-bold text-orange-700">{formatNumber(result.summary.unmatched_external)}</p>
                  <p className="text-sm text-orange-600">Unmatched External</p>
                </div>
              </div>

              <div className="mt-6 grid grid-cols-2 gap-4">
                <div className="p-4 border rounded-lg">
                  <div className="flex items-center gap-2 mb-3">
                    <CheckCircle className="h-5 w-5 text-green-600" />
                    <h4 className="font-medium">Matched Transactions</h4>
                  </div>
                  <p className="text-3xl font-bold text-green-700">{formatNumber(result.summary.matched)}</p>
                  <p className="text-sm text-gray-500 mt-1">
                    {result.summary.total_external > 0
                      ? `${((result.summary.matched / result.summary.total_external) * 100).toFixed(1)}% match rate`
                      : '0% match rate'}
                  </p>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="flex items-center gap-2 mb-3">
                    <XCircle className="h-5 w-5 text-orange-600" />
                    <h4 className="font-medium">Unmatched</h4>
                  </div>
                  <p className="text-3xl font-bold text-orange-700">
                    {formatNumber(result.summary.unmatched_external + result.summary.unmatched_internal)}
                  </p>
                  <p className="text-sm text-gray-500 mt-1">
                    External: {result.summary.unmatched_external} | Internal: {result.summary.unmatched_internal}
                  </p>
                </div>
              </div>

              <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                <h4 className="font-medium mb-3">Additional Metrics</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-gray-500">Total Credits</p>
                    <p className="font-medium">{formatNumber(result.summary.credits)}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Total Charges</p>
                    <p className="font-medium">{formatNumber(result.summary.charges)}</p>
                  </div>
                </div>
              </div>

              <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
                <h4 className="font-medium text-green-800 mb-3">Saved Records</h4>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <p className="text-green-600">External Records</p>
                    <p className="font-medium">{result.saved.external_records}</p>
                  </div>
                  <div>
                    <p className="text-green-600">Internal Records</p>
                    <p className="font-medium">{result.saved.internal_records}</p>
                  </div>
                  <div>
                    <p className="text-green-600">Total</p>
                    <p className="font-medium">{result.saved.total}</p>
                  </div>
                </div>
                <Button
                  variant="outline"
                  className="mt-4 w-full"
                  onClick={() => navigate(`/reports?batch_id=${selectedBatch}&gateway=${selectedGateway}`)}
                >
                  <ArrowRight className="h-4 w-4 mr-2" />
                  Go to Reports
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Unreconciled Items Side-by-Side Display */}
        {result && (result.summary.unmatched_external > 0 || result.summary.unmatched_internal > 0) && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <XCircle className="h-5 w-5 text-orange-600" />
                Unreconciled Transactions
              </CardTitle>
              <CardDescription>
                Transactions that could not be matched between external and internal records
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* External Unreconciled */}
                <div className="border rounded-lg">
                  <div className="bg-blue-50 px-4 py-3 border-b rounded-t-lg">
                    <h4 className="font-medium text-blue-900">
                      External (Bank Statement)
                      <Badge variant="secondary" className="ml-2">
                        {unreconciledExternalData?.pagination.total_count || result.summary.unmatched_external}
                      </Badge>
                    </h4>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 border-b">
                        <tr>
                          <th className="px-3 py-2 text-left font-medium text-gray-600">Date</th>
                          <th className="px-3 py-2 text-left font-medium text-gray-600">Details</th>
                          <th className="px-3 py-2 text-left font-medium text-gray-600">Key</th>
                          <th className="px-3 py-2 text-right font-medium text-gray-600">Amount</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {unreconciledExternalData?.transactions.map((txn) => (
                          <tr key={txn.id} className="hover:bg-gray-50">
                            <td className="px-3 py-2 text-gray-600 whitespace-nowrap">
                              {txn.date ? new Date(txn.date).toLocaleDateString() : '-'}
                            </td>
                            <td className="px-3 py-2 text-gray-900 max-w-[150px] truncate" title={txn.narrative || ''}>
                              {txn.narrative || '-'}
                            </td>
                            <td className="px-3 py-2 text-gray-500 font-mono text-xs max-w-[120px] truncate" title={txn.reconciliation_key || ''}>
                              {txn.reconciliation_key || '-'}
                            </td>
                            <td className="px-3 py-2 text-right text-gray-900 whitespace-nowrap">
                              {formatCurrency(txn.debit || txn.credit || 0)}
                            </td>
                          </tr>
                        ))}
                        {(!unreconciledExternalData?.transactions || unreconciledExternalData.transactions.length === 0) && (
                          <tr>
                            <td colSpan={4} className="px-3 py-4 text-center text-gray-500">
                              {result.summary.unmatched_external === 0 ? 'All external transactions matched!' : 'Loading...'}
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                  {/* External Pagination */}
                  {unreconciledExternalData?.pagination && unreconciledExternalData.pagination.total_pages > 1 && (
                    <div className="flex items-center justify-between px-4 py-3 border-t bg-gray-50 rounded-b-lg">
                      <span className="text-sm text-gray-600">
                        Page {externalPage} of {unreconciledExternalData.pagination.total_pages}
                      </span>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setExternalPage(p => Math.max(1, p - 1))}
                          disabled={!unreconciledExternalData.pagination.has_previous}
                        >
                          <ChevronLeft className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setExternalPage(p => p + 1)}
                          disabled={!unreconciledExternalData.pagination.has_next}
                        >
                          <ChevronRight className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  )}
                </div>

                {/* Internal Unreconciled */}
                <div className="border rounded-lg">
                  <div className="bg-purple-50 px-4 py-3 border-b rounded-t-lg">
                    <h4 className="font-medium text-purple-900">
                      Internal (Workpay)
                      <Badge variant="secondary" className="ml-2">
                        {unreconciledInternalData?.pagination.total_count || result.summary.unmatched_internal}
                      </Badge>
                    </h4>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 border-b">
                        <tr>
                          <th className="px-3 py-2 text-left font-medium text-gray-600">Date</th>
                          <th className="px-3 py-2 text-left font-medium text-gray-600">Details</th>
                          <th className="px-3 py-2 text-left font-medium text-gray-600">Key</th>
                          <th className="px-3 py-2 text-right font-medium text-gray-600">Amount</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {unreconciledInternalData?.transactions.map((txn) => (
                          <tr key={txn.id} className="hover:bg-gray-50">
                            <td className="px-3 py-2 text-gray-600 whitespace-nowrap">
                              {txn.date ? new Date(txn.date).toLocaleDateString() : '-'}
                            </td>
                            <td className="px-3 py-2 text-gray-900 max-w-[150px] truncate" title={txn.narrative || ''}>
                              {txn.narrative || '-'}
                            </td>
                            <td className="px-3 py-2 text-gray-500 font-mono text-xs max-w-[120px] truncate" title={txn.reconciliation_key || ''}>
                              {txn.reconciliation_key || '-'}
                            </td>
                            <td className="px-3 py-2 text-right text-gray-900 whitespace-nowrap">
                              {formatCurrency(txn.debit || txn.credit || 0)}
                            </td>
                          </tr>
                        ))}
                        {(!unreconciledInternalData?.transactions || unreconciledInternalData.transactions.length === 0) && (
                          <tr>
                            <td colSpan={4} className="px-3 py-4 text-center text-gray-500">
                              {result.summary.unmatched_internal === 0 ? 'All internal transactions matched!' : 'Loading...'}
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                  {/* Internal Pagination */}
                  {unreconciledInternalData?.pagination && unreconciledInternalData.pagination.total_pages > 1 && (
                    <div className="flex items-center justify-between px-4 py-3 border-t bg-gray-50 rounded-b-lg">
                      <span className="text-sm text-gray-600">
                        Page {internalPage} of {unreconciledInternalData.pagination.total_pages}
                      </span>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setInternalPage(p => Math.max(1, p - 1))}
                          disabled={!unreconciledInternalData.pagination.has_previous}
                        >
                          <ChevronLeft className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setInternalPage(p => p + 1)}
                          disabled={!unreconciledInternalData.pagination.has_next}
                        >
                          <ChevronRight className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
