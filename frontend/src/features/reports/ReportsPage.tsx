import { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FileSpreadsheet, FileText, Search, Download, Info } from 'lucide-react';
import { reportsApi, getErrorMessage } from '@/api';
import type { ReportFormat, ClosedBatch, AvailableGateway } from '@/api/reports';
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Input,
  Alert,
  PageLoading,
  Badge,
} from '@/components/ui';
import { useToast } from '@/hooks/useToast';
import { downloadFile, formatDateTime, cn } from '@/lib/utils';

export function ReportsPage() {
  const [searchParams] = useSearchParams();
  const toast = useToast();

  // State
  const [selectedBatch, setSelectedBatch] = useState(searchParams.get('batch_id') || '');
  const [selectedGateway, setSelectedGateway] = useState(searchParams.get('gateway') || '');
  const [selectedFormat, setSelectedFormat] = useState<ReportFormat>('xlsx');
  const [batchSearch, setBatchSearch] = useState('');
  const [isDownloading, setIsDownloading] = useState(false);
  const [showAllBatches, setShowAllBatches] = useState(false);

  // Fetch closed batches (latest 5 or search results)
  const { data: batchesData, isLoading: batchesLoading, refetch: refetchBatches } = useQuery({
    queryKey: ['closedBatches', batchSearch],
    queryFn: () => reportsApi.getClosedBatches(batchSearch || undefined, showAllBatches ? 50 : 5),
  });

  // Fetch available gateways when batch is selected
  const { data: gatewaysData, isLoading: gatewaysLoading } = useQuery({
    queryKey: ['availableGateways', selectedBatch],
    queryFn: () => reportsApi.getAvailableGateways(selectedBatch),
    enabled: !!selectedBatch,
  });

  const closedBatches = batchesData?.batches || [];
  const availableGateways = gatewaysData?.gateways || [];

  // Find selected batch details
  const selectedBatchData = useMemo(() => {
    return closedBatches.find((b) => b.batch_id === selectedBatch);
  }, [closedBatches, selectedBatch]);

  // Find selected gateway details
  const selectedGatewayData = useMemo(() => {
    return availableGateways.find((g) => g.gateway === selectedGateway);
  }, [availableGateways, selectedGateway]);

  // Reset gateway when batch changes
  useEffect(() => {
    setSelectedGateway('');
  }, [selectedBatch]);

  // Refetch batches when search changes
  useEffect(() => {
    refetchBatches();
  }, [batchSearch, showAllBatches, refetchBatches]);

  const handleDownload = async () => {
    if (!selectedBatch || !selectedGateway) {
      toast.error('Please select both a batch and gateway');
      return;
    }

    setIsDownloading(true);
    try {
      const blob = await reportsApi.downloadReport(selectedBatch, selectedGateway, selectedFormat);
      const filename = `reconciliation_${selectedGateway}_${selectedBatch}.${selectedFormat}`;
      downloadFile(blob, filename);
      toast.success('Report downloaded successfully');
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setIsDownloading(false);
    }
  };

  const canDownload = selectedBatch && selectedGateway;

  if (batchesLoading) return <PageLoading />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
        <p className="text-gray-500 mt-1">Download reconciliation reports for closed batches</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Generate Reconciliation Report</CardTitle>
          <CardDescription>
            Select a closed batch and gateway to download the reconciliation report
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {closedBatches.length === 0 && !batchSearch ? (
            <Alert variant="warning" title="No closed batches">
              Complete a reconciliation and close the batch first to generate reports.
            </Alert>
          ) : (
            <>
              {/* Step 1: Select Batch */}
              <div className="space-y-3">
                <label className="block text-sm font-medium text-gray-700">
                  Step 1: Select Batch
                </label>

                {/* Batch Search */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input
                    placeholder="Search by batch ID..."
                    value={batchSearch}
                    onChange={(e) => setBatchSearch(e.target.value)}
                    className="pl-10"
                  />
                </div>

                {/* Batch List */}
                <div className="border rounded-lg divide-y max-h-64 overflow-y-auto">
                  {closedBatches.length === 0 ? (
                    <div className="p-4 text-center text-gray-500">
                      No batches found matching "{batchSearch}"
                    </div>
                  ) : (
                    closedBatches.map((batch) => (
                      <button
                        key={batch.batch_id}
                        type="button"
                        onClick={() => setSelectedBatch(batch.batch_id)}
                        className={cn(
                          'w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors',
                          selectedBatch === batch.batch_id && 'bg-primary-50 border-l-4 border-l-primary-500'
                        )}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <span className="font-mono font-medium text-gray-900">
                              {batch.batch_id}
                            </span>
                            {batch.description && (
                              <p className="text-xs text-gray-500 mt-0.5 truncate max-w-xs">
                                {batch.description}
                              </p>
                            )}
                          </div>
                          <div className="text-right text-xs text-gray-500">
                            <p>Closed: {batch.closed_at ? formatDateTime(batch.closed_at) : '-'}</p>
                            <p>By: {batch.created_by || '-'}</p>
                          </div>
                        </div>
                      </button>
                    ))
                  )}
                </div>

                {/* Show more batches toggle */}
                {!batchSearch && (
                  <button
                    type="button"
                    onClick={() => setShowAllBatches(!showAllBatches)}
                    className="text-sm text-primary-600 hover:text-primary-700"
                  >
                    {showAllBatches ? 'Show less' : 'Show more batches...'}
                  </button>
                )}
              </div>

              {/* Step 2: Select Gateway */}
              {selectedBatch && (
                <div className="space-y-3">
                  <label className="block text-sm font-medium text-gray-700">
                    Step 2: Select Gateway
                  </label>

                  {gatewaysLoading ? (
                    <div className="p-4 text-center text-gray-500">Loading gateways...</div>
                  ) : availableGateways.length === 0 ? (
                    <Alert variant="warning" title="No gateways found">
                      No transactions found for this batch.
                    </Alert>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                      {availableGateways.map((gw) => (
                        <button
                          key={gw.gateway}
                          type="button"
                          onClick={() => setSelectedGateway(gw.gateway)}
                          className={cn(
                            'p-4 border rounded-lg text-left hover:bg-gray-50 transition-colors',
                            selectedGateway === gw.gateway && 'bg-primary-50 border-primary-500 ring-1 ring-primary-500'
                          )}
                        >
                          <div className="font-medium text-gray-900">{gw.display_name}</div>
                          <div className="text-sm text-gray-500 mt-1">
                            {gw.transaction_count.toLocaleString()} transactions
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Step 3: Select Format */}
              {selectedGateway && (
                <div className="space-y-3">
                  <label className="block text-sm font-medium text-gray-700">
                    Step 3: Select Format
                  </label>
                  <div className="flex gap-3">
                    <button
                      type="button"
                      onClick={() => setSelectedFormat('xlsx')}
                      className={cn(
                        'flex items-center gap-2 px-4 py-2 border rounded-lg transition-colors',
                        selectedFormat === 'xlsx'
                          ? 'bg-primary-50 border-primary-500 text-primary-700'
                          : 'hover:bg-gray-50'
                      )}
                    >
                      <FileSpreadsheet className="h-5 w-5" />
                      <span>Excel (.xlsx)</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setSelectedFormat('csv')}
                      className={cn(
                        'flex items-center gap-2 px-4 py-2 border rounded-lg transition-colors',
                        selectedFormat === 'csv'
                          ? 'bg-primary-50 border-primary-500 text-primary-700'
                          : 'hover:bg-gray-50'
                      )}
                    >
                      <FileText className="h-5 w-5" />
                      <span>CSV (.csv)</span>
                    </button>
                  </div>
                </div>
              )}

              {/* Selection Summary */}
              {(selectedBatch || selectedGateway) && (
                <div className="p-4 bg-gray-50 rounded-lg space-y-2">
                  <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
                    <Info className="h-4 w-4" />
                    Report Summary
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">Batch:</span>{' '}
                      <span className="font-mono font-medium">
                        {selectedBatch || <span className="text-gray-400">Not selected</span>}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500">Gateway:</span>{' '}
                      <span className="font-medium">
                        {selectedGatewayData?.display_name || <span className="text-gray-400">Not selected</span>}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500">Format:</span>{' '}
                      <span className="font-medium uppercase">{selectedFormat}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Report Columns Info */}
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-start gap-3">
                  <Info className="h-5 w-5 text-blue-600 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-blue-800">Report Columns</p>
                    <p className="text-sm text-blue-700 mt-1">
                      Date, Transaction Reference, Details, Debit, Credit, Reconciliation Status, Reconciliation Key, Batch ID
                    </p>
                  </div>
                </div>
              </div>

              {/* Download Button */}
              <div className="pt-4 border-t">
                <Button
                  onClick={handleDownload}
                  disabled={!canDownload || isDownloading}
                  isLoading={isDownloading}
                  className="w-full sm:w-auto"
                  size="lg"
                >
                  <Download className="h-5 w-5 mr-2" />
                  Download Report
                </Button>
                {!canDownload && (
                  <p className="text-sm text-gray-500 mt-2">
                    Select both a batch and gateway to enable download
                  </p>
                )}
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
