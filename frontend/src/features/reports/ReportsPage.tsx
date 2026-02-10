import { useState, useMemo } from 'react';
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
} from '@/components/ui';
import { useToast } from '@/hooks/useToast';
import { downloadFile, cn } from '@/lib/utils';

export function ReportsPage() {
  const [searchParams] = useSearchParams();
  const toast = useToast();

  // State
  const [selectedGateway, setSelectedGateway] = useState(searchParams.get('gateway') || '');
  const [dateFrom, setDateFrom] = useState(searchParams.get('date_from') || '');
  const [dateTo, setDateTo] = useState(searchParams.get('date_to') || '');
  const [selectedFormat, setSelectedFormat] = useState<ReportFormat>('xlsx');
  const [isDownloading, setIsDownloading] = useState(false);

  // Fetch available gateways (those with transactions)
  const { data: gatewaysData, isLoading: gatewaysLoading } = useQuery({
    queryKey: ['report-gateways'],
    queryFn: () => reportsApi.getAvailableGateways(),
  });

  const availableGateways = gatewaysData?.gateways || [];

  // Build unique base gateway options
  const getBaseGateway = (gateway: string) => {
    return gateway.replace(/_internal$/, '').replace(/_external$/, '');
  };

  const uniqueBaseGateways = useMemo(() => {
    const gateways = availableGateways.map((g) => getBaseGateway(g.gateway));
    return Array.from(new Set(gateways));
  }, [availableGateways]);

  const handleDownload = async () => {
    if (!selectedGateway) {
      toast.error('Please select a gateway');
      return;
    }

    setIsDownloading(true);
    try {
      const blob = await reportsApi.downloadReport(
        selectedGateway,
        selectedFormat,
        dateFrom || undefined,
        dateTo || undefined
      );
      const dateSuffix = dateFrom || dateTo ? `_${dateFrom || 'start'}_${dateTo || 'end'}` : '';
      const filename = `reconciliation_${selectedGateway}${dateSuffix}.${selectedFormat}`;
      downloadFile(blob, filename);
      toast.success('Report downloaded successfully');
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setIsDownloading(false);
    }
  };

  const canDownload = !!selectedGateway;

  if (gatewaysLoading) return <PageLoading />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
        <p className="text-gray-500 mt-1">Download reconciliation reports by gateway and date range</p>
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
            {availableGateways.length === 0 ? (
              <Alert variant="warning" title="No data available">
                Run reconciliation first to generate reports.
              </Alert>
            ) : (
              <>
                {/* Gateway Selection */}
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Gateway
                  </label>
                  <select
                    value={selectedGateway}
                    onChange={(e) => setSelectedGateway(e.target.value)}
                    className={cn(
                      'w-full px-3 py-2 border rounded-lg bg-white',
                      'focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400'
                    )}
                  >
                    <option value="">Select gateway...</option>
                    {uniqueBaseGateways.map((gw) => (
                      <option key={gw} value={gw}>
                        {gw.charAt(0).toUpperCase() + gw.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Date Range */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-700">
                      From Date
                    </label>
                    <input
                      type="date"
                      value={dateFrom}
                      onChange={(e) => setDateFrom(e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-700">
                      To Date
                    </label>
                    <input
                      type="date"
                      value={dateTo}
                      onChange={(e) => setDateTo(e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400"
                    />
                  </div>
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
                    Date, Transaction Reference, Details, Debit, Credit, Reconciliation Status, Reconciliation Note, Reconciliation Key, Run ID
                  </p>
                  {selectedFormat === 'xlsx' && (
                    <p className="text-xs text-blue-600 mt-1">
                      Excel report includes separate sheets: External, Internal, Deposits, and Charges.
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
                    Select a gateway to enable download
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
