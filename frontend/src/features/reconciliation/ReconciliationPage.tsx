import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Play,
  Save,
  FileCheck,
  FileX,
  AlertCircle,
  TrendingUp,
  FileSpreadsheet,
  ArrowLeftRight,
  CheckCircle2,
  XCircle,
  Upload,
  RefreshCw,
} from 'lucide-react';
import { reconciliationApi, getErrorMessage } from '@/api';
import type { ReconciliationPreviewResult } from '@/api/reconciliation';
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Select,
  Alert,
  PageLoading,
  Badge,
} from '@/components/ui';
import { useToast } from '@/hooks/useToast';
import { formatNumber } from '@/lib/utils';
import type { AvailableGateway } from '@/types';

export function ReconciliationPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();

  const [selectedGateway, setSelectedGateway] = useState('');
  const [previewResult, setPreviewResult] = useState<ReconciliationPreviewResult | null>(null);
  const [isSaved, setIsSaved] = useState(false);
  const [savedRunId, setSavedRunId] = useState<string | null>(null);

  // Fetch ready gateways (those with both files uploaded)
  const { data: gatewaysData, isLoading: gatewaysLoading } = useQuery({
    queryKey: ['ready-gateways'],
    queryFn: () => reconciliationApi.getReadyGateways(),
  });

  const availableGateways = gatewaysData?.gateways || [];

  // Reset preview when gateway changes
  useEffect(() => {
    setPreviewResult(null);
    setIsSaved(false);
    setSavedRunId(null);
  }, [selectedGateway]);

  // Preview mutation (dry run)
  const previewMutation = useMutation({
    mutationFn: (gateway: string) => reconciliationApi.preview(gateway),
    onSuccess: (data) => {
      setPreviewResult(data);
      setIsSaved(false);
      setSavedRunId(null);
      toast.success('Reconciliation preview complete. Review insights before saving.');
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  // Save mutation (persist to DB)
  const saveMutation = useMutation({
    mutationFn: (gateway: string) => reconciliationApi.reconcile(gateway),
    onSuccess: (data) => {
      setIsSaved(true);
      setSavedRunId(data.run_id);
      queryClient.invalidateQueries({ queryKey: ['ready-gateways'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['runs'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['unreconciled'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['transactions'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'], refetchType: 'all' });
      toast.success('Reconciliation saved successfully!');
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const handleRunReconciliation = () => {
    if (!selectedGateway) {
      toast.error('Please select a gateway');
      return;
    }
    previewMutation.mutate(selectedGateway);
  };

  const handleSaveReconciliation = () => {
    if (!selectedGateway) {
      toast.error('Please select a gateway');
      return;
    }
    saveMutation.mutate(selectedGateway);
  };

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

  if (gatewaysLoading) return <PageLoading />;

  const insights = previewResult?.insights;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Reconciliation</h1>
        <p className="text-gray-500 mt-1">Match transactions between bank statements and internal records</p>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Side - Reconciliation Workflow */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2">
              <ArrowLeftRight className="h-5 w-5 text-primary-600" />
              Run Reconciliation
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {availableGateways.length === 0 ? (
              <Alert variant="warning" title="No gateways ready">
                Upload files for a gateway to start reconciliation.
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2"
                  onClick={() => navigate('/upload')}
                >
                  <Upload className="h-4 w-4 mr-1.5" />
                  Go to Upload
                </Button>
              </Alert>
            ) : (
              <>
                {/* Gateway Selection */}
                <Select
                  label="Gateway"
                  options={gatewayOptions}
                  value={selectedGateway}
                  onChange={(e) => setSelectedGateway(e.target.value)}
                  placeholder="Select gateway"
                />

                {/* Gateway File Status */}
                {selectedGatewayInfo && (
                  <div className="p-4 bg-gray-50 rounded-lg space-y-3">
                    <h4 className="font-medium text-sm text-gray-700">Files for {selectedGatewayInfo.display_name}</h4>
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-sm">
                        {selectedGatewayInfo.has_external ? (
                          <FileCheck className="h-4 w-4 text-green-600" />
                        ) : (
                          <FileX className="h-4 w-4 text-red-500" />
                        )}
                        <FileSpreadsheet className="h-4 w-4 text-gray-400" />
                        <span className={selectedGatewayInfo.has_external ? 'text-gray-700' : 'text-red-600'}>
                          {selectedGatewayInfo.external_file || 'External file not uploaded'}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        {selectedGatewayInfo.has_internal ? (
                          <FileCheck className="h-4 w-4 text-green-600" />
                        ) : (
                          <FileX className="h-4 w-4 text-red-500" />
                        )}
                        <FileSpreadsheet className="h-4 w-4 text-gray-400" />
                        <span className={selectedGatewayInfo.has_internal ? 'text-gray-700' : 'text-red-600'}>
                          {selectedGatewayInfo.internal_file || 'Internal file not uploaded'}
                        </span>
                      </div>
                    </div>

                    {!selectedGatewayInfo.ready_for_reconciliation && (
                      <div className="pt-2">
                        <Alert variant="warning" title="Missing files">
                          Both files are required for reconciliation.
                        </Alert>
                        <Button
                          variant="outline"
                          size="sm"
                          className="mt-2 w-full"
                          onClick={() => navigate('/upload')}
                        >
                          <Upload className="h-4 w-4 mr-1.5" />
                          Go to Upload
                        </Button>
                      </div>
                    )}
                  </div>
                )}

                {/* Action Buttons */}
                <div className="space-y-2 pt-2">
                  <Button
                    onClick={handleRunReconciliation}
                    disabled={
                      !selectedGateway ||
                      !selectedGatewayInfo?.ready_for_reconciliation ||
                      previewMutation.isPending
                    }
                    isLoading={previewMutation.isPending}
                    className="w-full"
                    variant="outline"
                  >
                    <Play className="h-4 w-4 mr-1.5" />
                    Run Reconciliation
                  </Button>

                  <Button
                    onClick={handleSaveReconciliation}
                    disabled={
                      !previewResult ||
                      isSaved ||
                      saveMutation.isPending
                    }
                    isLoading={saveMutation.isPending}
                    className="w-full"
                  >
                    <Save className="h-4 w-4 mr-1.5" />
                    {isSaved ? 'Saved' : 'Save Reconciliation'}
                  </Button>
                </div>

                {/* Preview warning */}
                {previewResult && !isSaved && (
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                    <div className="flex items-start gap-2">
                      <AlertCircle className="h-4 w-4 text-amber-600 mt-0.5" />
                      <div className="text-sm text-amber-800">
                        <p className="font-medium">Preview Only</p>
                        <p className="text-amber-700">Results are not saved. Click "Save Reconciliation" to persist.</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Saved success */}
                {isSaved && (
                  <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                    <div className="flex items-start gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-600 mt-0.5" />
                      <div className="text-sm text-green-800">
                        <p className="font-medium">Reconciliation Saved</p>
                        {savedRunId && (
                          <p className="text-green-700 font-mono text-xs mt-1">Run: {savedRunId}</p>
                        )}
                        <Button
                          variant="outline"
                          size="sm"
                          className="mt-2"
                          onClick={() => navigate(`/reports?gateway=${selectedGateway}`)}
                        >
                          View Reports
                        </Button>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>

        {/* Right Side - Insights Tiles */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-gray-600" />
              Reconciliation Insights
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!previewResult ? (
              <div className="text-center py-8 text-gray-500 text-sm">
                Run reconciliation to view insights
              </div>
            ) : (
              <div className="space-y-4">
                {/* Match Rate - Hero Tile */}
                <div className="p-4 bg-gradient-to-br from-primary-50 to-primary-100 rounded-lg border border-primary-200 text-center">
                  <p className="text-4xl font-bold text-primary-700">{insights?.match_rate}%</p>
                  <p className="text-sm text-primary-600 font-medium">Match Rate</p>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
                    <p className="text-xl font-bold text-blue-700">{formatNumber(insights?.total_external || 0)}</p>
                    <p className="text-xs text-blue-600">External Records</p>
                  </div>
                  <div className="p-3 bg-purple-50 rounded-lg border border-purple-100">
                    <p className="text-xl font-bold text-purple-700">{formatNumber(insights?.total_internal || 0)}</p>
                    <p className="text-xs text-purple-600">Internal Records</p>
                  </div>
                  <div className="p-3 bg-green-50 rounded-lg border border-green-100">
                    <div className="flex items-center gap-1.5">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      <p className="text-xl font-bold text-green-700">{formatNumber(insights?.matched || 0)}</p>
                    </div>
                    <p className="text-xs text-green-600">Matched</p>
                  </div>
                  <div className="p-3 bg-orange-50 rounded-lg border border-orange-100">
                    <div className="flex items-center gap-1.5">
                      <XCircle className="h-4 w-4 text-orange-600" />
                      <p className="text-xl font-bold text-orange-700">{formatNumber(insights?.unreconciled_external || 0)}</p>
                    </div>
                    <p className="text-xs text-orange-600">Unmatched External</p>
                  </div>
                  <div className="p-3 bg-red-50 rounded-lg border border-red-100">
                    <div className="flex items-center gap-1.5">
                      <XCircle className="h-4 w-4 text-red-600" />
                      <p className="text-xl font-bold text-red-700">{formatNumber(insights?.unreconciled_internal || 0)}</p>
                    </div>
                    <p className="text-xs text-red-600">Unmatched Internal</p>
                  </div>
                  <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-100">
                    <p className="text-xl font-bold text-emerald-700">{formatNumber(insights?.deposits || 0)}</p>
                    <p className="text-xs text-emerald-600">Deposits (Credits)</p>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <p className="text-xl font-bold text-gray-700">{formatNumber(insights?.charges || 0)}</p>
                    <p className="text-xs text-gray-600">Bank Charges</p>
                  </div>

                  {/* Carry-Forward Matched */}
                  {(insights?.carry_forward_matched ?? 0) > 0 && (
                    <div className="p-3 bg-cyan-50 rounded-lg border border-cyan-100">
                      <div className="flex items-center gap-1.5">
                        <RefreshCw className="h-4 w-4 text-cyan-600" />
                        <p className="text-xl font-bold text-cyan-700">{formatNumber(insights?.carry_forward_matched || 0)}</p>
                      </div>
                      <p className="text-xs text-cyan-600">Carry-Forward Matched</p>
                    </div>
                  )}
                </div>

                {/* Carry-forward info banner */}
                {(insights?.carry_forward_matched ?? 0) > 0 && (
                  <div className="p-3 bg-cyan-50 border border-cyan-200 rounded-lg">
                    <div className="flex items-start gap-2">
                      <RefreshCw className="h-4 w-4 text-cyan-600 mt-0.5" />
                      <div className="text-sm text-cyan-800">
                        <p className="font-medium">Carry-Forward</p>
                        <p className="text-cyan-700">
                          {insights?.carry_forward_matched} previously unreconciled items matched in this run.
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Status Badge */}
                <div className="flex justify-center pt-2">
                  {isSaved ? (
                    <Badge variant="success" className="px-3 py-1">
                      <CheckCircle2 className="h-3 w-3 mr-1" />
                      Saved to Database
                    </Badge>
                  ) : (
                    <Badge variant="warning" className="px-3 py-1">
                      <AlertCircle className="h-3 w-3 mr-1" />
                      Preview Only - Not Saved
                    </Badge>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
