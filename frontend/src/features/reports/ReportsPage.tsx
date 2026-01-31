import { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FileSpreadsheet, FileText, Download, FileDown } from 'lucide-react';
import { reportsApi, getErrorMessage } from '@/api';
import type { ReportFormat } from '@/api/reports';
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Alert,
  PageLoading,
  Badge,
} from '@/components/ui';
import { useToast } from '@/hooks/useToast';
import { downloadFile, cn } from '@/lib/utils';

export function ReportsPage() {
  const [searchParams] = useSearchParams();
  const toast = useToast();

  // State
  const [selectedBatch, setSelectedBatch] = useState(searchParams.get('batch_id') || '');
  const [selectedGateway, setSelectedGateway] = useState(searchParams.get('gateway') || '');
  const [selectedFormat, setSelectedFormat] = useState<ReportFormat>('xlsx');
  const [batchSearch, setBatchSearch] = useState('');
  const [isDownloading, setIsDownloading] = useState(false);
  const [batchDropdownOpen, setBatchDropdownOpen] = useState(false);

  // Fetch batches (latest 5 or search results)
  const {
    data: batchesData,
    isLoading: batchesLoading,
  } = useQuery({
    queryKey: ['reportBatches', batchSearch],
    queryFn: () => reportsApi.getBatches(batchSearch || undefined, batchSearch ? 50 : 5),
  });

  // Fetch available gateways when batch is selected
  const { data: gatewaysData, isLoading: gatewaysLoading } = useQuery({
    queryKey: ['availableGateways', selectedBatch],
    queryFn: () => reportsApi.getAvailableGateways(selectedBatch),
    enabled: !!selectedBatch,
  });

  const batches = batchesData?.batches || [];
  const availableGateways = gatewaysData?.gateways || [];

  // Reset gateway when batch changes
  useEffect(() => {
    setSelectedGateway('');
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
    setBatchDropdownOpen(false);
    setBatchSearch('');
  };

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

  // Build unified gateway options
  const getBaseGateway = (gateway: string) => {
    return gateway.replace(/_internal$/, '').replace(/_external$/, '');
  };

  const uniqueBaseGateways = useMemo(() => {
    const gateways = availableGateways.map((g) => getBaseGateway(g.gateway));
    return Array.from(new Set(gateways));
  }, [availableGateways]);

  if (batchesLoading) return <PageLoading />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
        <p className="text-gray-500 mt-1">Download reconciliation reports for any batch</p>
      </div>

      {/* Centered Half-Page Card */}
      <div className="flex justify-center">
        <Card className="w-full max-w-xl">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2">
              <FileDown className="h-5 w-5 text-primary-600" />
              Generate Report
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            {batches.length === 0 && !batchSearch ? (
              <Alert variant="warning" title="No batches">
                Create a batch and run reconciliation first to generate reports.
              </Alert>
            ) : (
              <>
                {/* Batch Selection with Search */}
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Batch
                  </label>
                  <div className="relative batch-dropdown">
                    <button
                      type="button"
                      onClick={() => setBatchDropdownOpen(!batchDropdownOpen)}
                      className={cn(
                        'w-full px-3 py-2 text-left border rounded-lg bg-white',
                        'focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400',
                        'flex items-center justify-between',
                        batchDropdownOpen && 'ring-2 ring-primary-400 border-primary-400'
                      )}
                    >
                      <span className={selectedBatch ? 'text-gray-900 font-mono' : 'text-gray-500'}>
                        {selectedBatch || 'Select a batch...'}
                      </span>
                      <svg
                        className={cn('h-4 w-4 text-gray-400 transition-transform', batchDropdownOpen && 'rotate-180')}
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

                {/* Gateway Selection */}
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Gateway
                  </label>
                  <select
                    value={selectedGateway}
                    onChange={(e) => setSelectedGateway(e.target.value)}
                    disabled={!selectedBatch || gatewaysLoading}
                    className={cn(
                      'w-full px-3 py-2 border rounded-lg bg-white',
                      'focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400',
                      'disabled:bg-gray-100 disabled:cursor-not-allowed'
                    )}
                  >
                    <option value="">
                      {!selectedBatch
                        ? 'Select batch first'
                        : gatewaysLoading
                          ? 'Loading gateways...'
                          : 'Select gateway...'}
                    </option>
                    {uniqueBaseGateways.map((gw) => (
                      <option key={gw} value={gw}>
                        {gw.charAt(0).toUpperCase() + gw.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Format Selection (Radio Buttons) */}
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Format
                  </label>
                  <div className="flex gap-4">
                    <label
                      className={cn(
                        'flex items-center gap-2 px-4 py-2 border rounded-lg cursor-pointer transition-colors',
                        selectedFormat === 'xlsx'
                          ? 'bg-primary-50 border-primary-500 text-primary-700'
                          : 'bg-white hover:bg-gray-50'
                      )}
                    >
                      <input
                        type="radio"
                        name="format"
                        value="xlsx"
                        checked={selectedFormat === 'xlsx'}
                        onChange={() => setSelectedFormat('xlsx')}
                        className="sr-only"
                      />
                      <FileSpreadsheet className="h-4 w-4" />
                      <span className="text-sm font-medium">Excel (.xlsx)</span>
                    </label>
                    <label
                      className={cn(
                        'flex items-center gap-2 px-4 py-2 border rounded-lg cursor-pointer transition-colors',
                        selectedFormat === 'csv'
                          ? 'bg-primary-50 border-primary-500 text-primary-700'
                          : 'bg-white hover:bg-gray-50'
                      )}
                    >
                      <input
                        type="radio"
                        name="format"
                        value="csv"
                        checked={selectedFormat === 'csv'}
                        onChange={() => setSelectedFormat('csv')}
                        className="sr-only"
                      />
                      <FileText className="h-4 w-4" />
                      <span className="text-sm font-medium">CSV (.csv)</span>
                    </label>
                  </div>
                </div>

                {/* Report Columns Info */}
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-xs font-medium text-blue-800 mb-1">Report Columns</p>
                  <p className="text-xs text-blue-700">
                    Date, Transaction Reference, Details, Debit, Credit, Reconciliation Status, Reconciliation Note, Reconciliation Key, Batch ID
                  </p>
                  {selectedFormat === 'xlsx' && (
                    <p className="text-xs text-blue-600 mt-1">
                      Excel report includes separate sheets for external debits, internal debits, credits/deposits, and charges.
                    </p>
                  )}
                </div>

                {/* Download Button */}
                <Button
                  onClick={handleDownload}
                  disabled={!canDownload || isDownloading}
                  isLoading={isDownloading}
                  className="w-full"
                  size="lg"
                >
                  <Download className="h-5 w-5 mr-2" />
                  Download Report
                </Button>

                {!canDownload && (
                  <p className="text-xs text-gray-500 text-center">
                    Select both a batch and gateway to enable download
                  </p>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
