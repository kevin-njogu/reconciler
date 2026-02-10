import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Download,
  Upload,
  CheckCircle,
  XCircle,
  Trash2,
  FileSpreadsheet,
  FolderOpen,
  Wand2,
  FileText,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { gatewaysApi, uploadApi, getErrorMessage } from '@/api';
import type { TransformUploadResponse } from '@/api/upload';
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Select,
  FileUpload,
  Alert,
  PageLoading,
  Badge,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  TableEmpty,
  Modal,
  ModalFooter,
} from '@/components/ui';
import { useToast } from '@/hooks/useToast';
import { downloadFile, formatBytes, formatDateTime } from '@/lib/utils';

type UploadMode = 'template' | 'transform';

const pageSizeOptions = [
  { value: '5', label: '5 per page' },
  { value: '10', label: '10 per page' },
  { value: '25', label: '25 per page' },
];

export function UploadPage() {
  const toast = useToast();
  const queryClient = useQueryClient();

  const [selectedGateway, setSelectedGateway] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<{ valid: boolean; message: string } | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ filename: string; gateway: string } | null>(null);
  const [showTemplatePopup, setShowTemplatePopup] = useState(false);
  const [templateFormat, setTemplateFormat] = useState<'xlsx' | 'csv'>('xlsx');
  const [isDownloadingTemplate, setIsDownloadingTemplate] = useState(false);

  // Transform mode state
  const [uploadMode, setUploadMode] = useState<UploadMode>('template');
  const [transformResult, setTransformResult] = useState<TransformUploadResponse['transformation'] | null>(null);

  // Pagination state for files
  const [filesPage, setFilesPage] = useState(1);
  const [filesPageSize, setFilesPageSize] = useState(10);

  // Fetch unified gateways for dropdown (only active gateways)
  const { data: unifiedGatewaysData, isLoading: gatewaysLoading } = useQuery({
    queryKey: ['unified-gateways', { include_inactive: false }],
    queryFn: () => gatewaysApi.list(false),
    staleTime: 0,
  });

  // Derive base gateway for file listing from selected gateway
  const getBaseGateway = (gw: string) => gw.replace(/^workpay_/, '');
  const baseGateway = selectedGateway ? getBaseGateway(selectedGateway) : '';

  // Fetch files for selected gateway
  const { data: filesData, isLoading: filesLoading } = useQuery({
    queryKey: ['gateway-files', baseGateway],
    queryFn: () => uploadApi.listFiles(baseGateway),
    enabled: !!baseGateway,
  });

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: async ({
      gateway,
      file,
      transform,
    }: {
      gateway: string;
      file: File;
      transform: boolean;
    }) => {
      return uploadApi.uploadFile(gateway, file, transform);
    },
    onSuccess: (data) => {
      if ('transformation' in data) {
        const transformData = data as TransformUploadResponse;
        setTransformResult(transformData.transformation);

        if (transformData.transformation.success) {
          toast.success(
            `File transformed: ${transformData.transformation.row_count} rows processed`
          );
        } else {
          toast.warning('File uploaded but transformation had issues');
        }
      } else {
        toast.success(`File uploaded: ${data.filename}`);
      }

      setSelectedFile(null);
      setValidationResult(null);
      queryClient.invalidateQueries({ queryKey: ['gateway-files'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['available-gateways'], refetchType: 'all' });
    },
    onError: (err) => {
      toast.error(getErrorMessage(err));
      setTransformResult(null);
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async ({ filename, gateway }: { filename: string; gateway: string }) => {
      return uploadApi.deleteFile(filename, gateway);
    },
    onSuccess: (data) => {
      toast.success(data.message);
      setDeleteTarget(null);
      queryClient.invalidateQueries({ queryKey: ['gateway-files'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['available-gateways'], refetchType: 'all' });
    },
    onError: (err) => {
      toast.error(getErrorMessage(err));
      setDeleteTarget(null);
    },
  });

  // Validate file on selection (only in template mode)
  const handleFileSelect = async (files: File[]) => {
    const file = files[0] || null;
    setSelectedFile(file);
    setValidationResult(null);
    setTransformResult(null);

    if (file) {
      if (uploadMode === 'transform') {
        setValidationResult({
          valid: true,
          message: 'Raw file ready for transformation',
        });
        return;
      }

      setIsValidating(true);
      try {
        const result = await uploadApi.validateFile(file);
        setValidationResult({ valid: result.valid, message: result.message });
      } catch (err) {
        setValidationResult({ valid: false, message: getErrorMessage(err) });
      } finally {
        setIsValidating(false);
      }
    }
  };

  const handleRemoveFile = (_index: number) => {
    setSelectedFile(null);
    setValidationResult(null);
    setTransformResult(null);
  };

  const handleUpload = () => {
    if (!selectedGateway || !selectedFile) {
      toast.error('Please select a gateway and file');
      return;
    }

    uploadMutation.mutate({
      gateway: selectedGateway,
      file: selectedFile,
      transform: uploadMode === 'transform',
    });
  };

  const handleModeChange = (mode: UploadMode) => {
    setUploadMode(mode);
    setTransformResult(null);
    if (selectedFile) {
      handleFileSelect([selectedFile]);
    }
  };

  const handleDownloadTemplate = async () => {
    setIsDownloadingTemplate(true);
    try {
      const blob = await uploadApi.downloadTemplate(templateFormat);
      downloadFile(blob, `template.${templateFormat}`);
      toast.success('Template downloaded');
      setShowTemplatePopup(false);
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setIsDownloadingTemplate(false);
    }
  };

  const handleDownloadFile = async (filename: string, gateway: string) => {
    try {
      const blob = await uploadApi.downloadFile(filename, gateway);
      downloadFile(blob, filename);
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  const handleConfirmDelete = () => {
    if (deleteTarget) {
      deleteMutation.mutate({
        filename: deleteTarget.filename,
        gateway: deleteTarget.gateway,
      });
    }
  };

  // Build gateway options from unified gateways
  const gatewayOptions = unifiedGatewaysData?.gateways?.flatMap((g) => {
    const options: { value: string; label: string }[] = [];
    if (g.external_config?.name && g.external_config.is_active) {
      options.push({
        value: g.external_config.name,
        label: `${g.display_name} (External)`,
      });
    }
    if (g.internal_config?.name && g.internal_config.is_active) {
      options.push({
        value: g.internal_config.name,
        label: `${g.display_name} (Internal)`,
      });
    }
    return options;
  }) || [];

  // Get the selected gateway's file config
  const selectedGatewayConfig = selectedGateway
    ? unifiedGatewaysData?.gateways?.flatMap((g) => [g.external_config, g.internal_config])
        .find((config) => config?.name === selectedGateway)
    : null;

  const acceptedFileTypes = selectedGatewayConfig?.expected_filetypes?.length
    ? selectedGatewayConfig.expected_filetypes.map((ext: string) => `.${ext}`).join(',')
    : '.xlsx,.xls,.csv';

  const isUploading = uploadMutation.isPending;
  const allFiles = filesData?.files || [];

  // Client-side pagination for files
  const totalFiles = allFiles.length;
  const totalPages = Math.ceil(totalFiles / filesPageSize);
  const paginatedFiles = allFiles.slice(
    (filesPage - 1) * filesPageSize,
    filesPage * filesPageSize
  );

  if (gatewaysLoading) return <PageLoading />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Upload Files</h1>
        <p className="text-gray-500 mt-1">Upload transaction files for reconciliation</p>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Side - Upload Workflow */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5 text-primary-600" />
              Upload File
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Gateway Selection */}
            <Select
              label="Gateway"
              options={gatewayOptions}
              value={selectedGateway}
              onChange={(e) => {
                setSelectedGateway(e.target.value);
                setSelectedFile(null);
                setValidationResult(null);
                setTransformResult(null);
                setFilesPage(1);
              }}
              placeholder="Select gateway"
            />

            {/* Upload Mode Toggle */}
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">
                Upload Mode
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => handleModeChange('template')}
                  className={`flex items-center justify-center gap-2 rounded-lg border-2 p-2.5 text-sm transition-colors ${
                    uploadMode === 'template'
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-200 text-gray-600 hover:border-gray-300'
                  }`}
                >
                  <FileText className="h-4 w-4" />
                  Template
                </button>
                <button
                  type="button"
                  onClick={() => handleModeChange('transform')}
                  className={`flex items-center justify-center gap-2 rounded-lg border-2 p-2.5 text-sm transition-colors ${
                    uploadMode === 'transform'
                      ? 'border-purple-500 bg-purple-50 text-purple-700'
                      : 'border-gray-200 text-gray-600 hover:border-gray-300'
                  }`}
                >
                  <Wand2 className="h-4 w-4" />
                  Transform
                </button>
              </div>
              <p className="mt-1.5 text-xs text-gray-500">
                {uploadMode === 'template'
                  ? 'Pre-formatted file with template columns'
                  : 'Raw file auto-mapped using gateway config'}
              </p>
            </div>

            {/* Dropzone */}
            <FileUpload
              onFileSelect={handleFileSelect}
              selectedFiles={selectedFile ? [selectedFile] : []}
              onRemoveFile={handleRemoveFile}
              accept={acceptedFileTypes}
              disabled={!selectedGateway}
              multiple={false}
            />

            {/* Validation Status */}
            {selectedFile && (
              <div
                className={`p-3 rounded-lg border text-sm ${
                  isValidating
                    ? 'bg-gray-50 border-gray-200'
                    : validationResult?.valid
                      ? uploadMode === 'transform'
                        ? 'bg-purple-50 border-purple-200'
                        : 'bg-green-50 border-green-200'
                      : 'bg-red-50 border-red-200'
                }`}
              >
                <div className="flex items-center gap-2">
                  {isValidating ? (
                    <div className="h-4 w-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
                  ) : validationResult?.valid ? (
                    uploadMode === 'transform' ? (
                      <Wand2 className="h-4 w-4 text-purple-600" />
                    ) : (
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    )
                  ) : (
                    <XCircle className="h-4 w-4 text-red-600" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-gray-900 truncate">{selectedFile.name}</p>
                    <p
                      className={`text-xs ${
                        isValidating
                          ? 'text-gray-500'
                          : validationResult?.valid
                            ? uploadMode === 'transform'
                              ? 'text-purple-600'
                              : 'text-green-600'
                            : 'text-red-600'
                      }`}
                    >
                      {isValidating ? 'Validating...' : validationResult?.message}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Transformation Results */}
            {transformResult && (
              <div className="space-y-2 rounded-lg border border-purple-200 bg-purple-50 p-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5 font-medium text-purple-900">
                    <Wand2 className="h-4 w-4" />
                    Transformation Results
                  </span>
                  <Badge variant={transformResult.success ? 'success' : 'warning'}>
                    {transformResult.row_count} rows
                  </Badge>
                </div>

                {Object.keys(transformResult.column_mapping_used).length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(transformResult.column_mapping_used).map(
                      ([templateCol, rawCol]) => (
                        <span
                          key={templateCol}
                          className="rounded bg-purple-100 px-1.5 py-0.5 text-xs text-purple-700"
                        >
                          {templateCol} ← {rawCol}
                        </span>
                      )
                    )}
                  </div>
                )}

                {transformResult.warnings.length > 0 && (
                  <div className="rounded border border-amber-200 bg-amber-50 p-2">
                    <div className="flex items-center gap-1 text-xs font-medium text-amber-700">
                      <AlertTriangle className="h-3 w-3" />
                      Warnings
                    </div>
                    <ul className="mt-1 list-inside list-disc text-xs text-amber-600">
                      {transformResult.warnings.map((warning, i) => (
                        <li key={i}>{warning}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Upload Button */}
            <Button
              onClick={handleUpload}
              disabled={
                !selectedGateway ||
                !selectedFile ||
                isValidating ||
                !validationResult?.valid
              }
              isLoading={isUploading}
              size="sm"
              className="w-full"
            >
              <Upload className="h-4 w-4 mr-1.5" />
              Upload File
            </Button>

            {/* Download Template Button */}
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={() => setShowTemplatePopup(true)}
            >
              <Download className="h-4 w-4 mr-1.5" />
              Download Template
            </Button>
          </CardContent>
        </Card>

        {/* Right Side - Uploaded Files */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-4">
            <CardTitle className="flex items-center gap-2">
              <FolderOpen className="h-5 w-5 text-gray-600" />
              Uploaded Files
            </CardTitle>
            {baseGateway && (
              <Badge variant="default">{totalFiles} file{totalFiles !== 1 ? 's' : ''}</Badge>
            )}
          </CardHeader>
          <CardContent className="p-0">
            {!baseGateway ? (
              <div className="p-6 text-center text-gray-500 text-sm">
                Select a gateway to view uploaded files
              </div>
            ) : filesLoading ? (
              <div className="p-6 text-center text-gray-500 text-sm">Loading files...</div>
            ) : (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Filename</TableHead>
                      <TableHead>Gateway</TableHead>
                      <TableHead>Size</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {paginatedFiles.length === 0 ? (
                      <TableEmpty message="No files uploaded yet" colSpan={4} />
                    ) : (
                      paginatedFiles.map((file) => (
                        <TableRow key={file.id}>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <FileSpreadsheet className="h-4 w-4 text-gray-400 shrink-0" />
                              <div className="min-w-0">
                                <p className="text-sm truncate">{file.filename}</p>
                                <p className="text-xs text-gray-500">
                                  {formatDateTime(file.uploaded_at)}
                                </p>
                              </div>
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge variant="default" className="text-xs">{file.gateway}</Badge>
                          </TableCell>
                          <TableCell className="text-gray-500 text-sm">
                            {file.file_size ? formatBytes(file.file_size) : '-'}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDownloadFile(file.filename, file.gateway)}
                                className="text-blue-600 hover:text-blue-700 px-2"
                                title="Download"
                              >
                                <Download className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setDeleteTarget({
                                  filename: file.filename,
                                  gateway: file.gateway,
                                })}
                                className="text-danger-600 hover:text-danger-700 px-2"
                                title="Delete"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>

                {/* Pagination */}
                {totalFiles > 0 && (
                  <div className="flex flex-col gap-3 px-4 py-3 border-t">
                    <div className="flex items-center justify-between">
                      <div className="text-xs text-gray-500">
                        {totalFiles} file{totalFiles !== 1 ? 's' : ''} total
                      </div>
                      <div className="w-28">
                        <Select
                          options={pageSizeOptions}
                          value={filesPageSize.toString()}
                          onChange={(e) => {
                            setFilesPageSize(parseInt(e.target.value, 10));
                            setFilesPage(1);
                          }}
                        />
                      </div>
                    </div>
                    {totalPages > 1 && (
                      <div className="flex items-center justify-center gap-1">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setFilesPage((p) => Math.max(1, p - 1))}
                          disabled={filesPage === 1}
                          className="px-2"
                        >
                          <ChevronLeft className="h-4 w-4" />
                        </Button>
                        <span className="text-xs text-gray-600 px-2">
                          {filesPage} / {totalPages}
                        </span>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setFilesPage((p) => Math.min(totalPages, p + 1))}
                          disabled={filesPage === totalPages}
                          className="px-2"
                        >
                          <ChevronRight className="h-4 w-4" />
                        </Button>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Template Download Popup */}
      <Modal
        isOpen={showTemplatePopup}
        onClose={() => setShowTemplatePopup(false)}
        title="Download Template"
        description="Expected data formats and column requirements"
        size="md"
      >
        <div className="space-y-4">
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-gray-900">Column Requirements</h4>
            <div className="divide-y divide-gray-100">
              {[
                { name: 'Date', desc: 'Transaction date', mandatory: true, fmt: 'YYYY-MM-DD' },
                { name: 'Reference', desc: 'Transaction ID / unique identifier', mandatory: true, fmt: 'Text/Number' },
                { name: 'Details', desc: 'Transaction narration / description', mandatory: true, fmt: 'Text' },
                { name: 'Debit', desc: 'Outgoing amount', mandatory: false, fmt: 'Number' },
                { name: 'Credit', desc: 'Incoming amount', mandatory: false, fmt: 'Number' },
              ].map((col) => (
                <div key={col.name} className="flex items-center justify-between py-2">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{col.name}</p>
                    <p className="text-xs text-gray-500">{col.desc}</p>
                  </div>
                  <div className="text-right">
                    <Badge variant={col.mandatory ? 'warning' : 'default'} className="text-xs">
                      {col.mandatory ? 'Mandatory' : 'Optional'}
                    </Badge>
                    <p className="text-xs text-gray-500 mt-0.5">{col.fmt}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
            <p className="text-xs text-blue-800">
              The template includes a sample row with the current date in the expected format (YYYY-MM-DD) as guidance. Column names are case-insensitive.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Format</label>
            <div className="flex gap-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="templateFormat"
                  value="xlsx"
                  checked={templateFormat === 'xlsx'}
                  onChange={() => setTemplateFormat('xlsx')}
                  className="text-blue-600"
                />
                <span className="text-sm text-gray-700">Excel (.xlsx)</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="templateFormat"
                  value="csv"
                  checked={templateFormat === 'csv'}
                  onChange={() => setTemplateFormat('csv')}
                  className="text-blue-600"
                />
                <span className="text-sm text-gray-700">CSV (.csv)</span>
              </label>
            </div>
          </div>
        </div>
        <ModalFooter>
          <Button variant="outline" onClick={() => setShowTemplatePopup(false)}>
            Cancel
          </Button>
          <Button onClick={handleDownloadTemplate} isLoading={isDownloadingTemplate}>
            <Download className="h-4 w-4 mr-2" />
            Download Template
          </Button>
        </ModalFooter>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Delete File"
        description="Confirm file deletion"
        size="sm"
      >
        <div className="space-y-4">
          <p className="text-neutral-700">
            Are you sure you want to delete{' '}
            <span className="font-mono font-semibold">{deleteTarget?.filename}</span>?
          </p>
          <p className="text-sm text-neutral-500">
            This will permanently remove the file from storage. You can re-upload a new file afterward.
          </p>
        </div>
        <ModalFooter>
          <Button variant="outline" onClick={() => setDeleteTarget(null)}>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={handleConfirmDelete}
            isLoading={deleteMutation.isPending}
          >
            Delete File
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  );
}
