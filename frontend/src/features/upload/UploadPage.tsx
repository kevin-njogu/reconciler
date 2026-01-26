import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Download,
  Upload,
  CheckCircle,
  XCircle,
  Trash2,
  FileSpreadsheet,
  FolderOpen,
  Info,
} from 'lucide-react';
import { gatewaysApi, uploadApi, getErrorMessage } from '@/api';
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Select,
  SearchableSelect,
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

export function UploadPage() {
  const [searchParams] = useSearchParams();
  const toast = useToast();
  const queryClient = useQueryClient();

  const [selectedBatch, setSelectedBatch] = useState(searchParams.get('batch_id') || '');
  const [selectedGateway, setSelectedGateway] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<{ valid: boolean; message: string } | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ filename: string; gateway: string } | null>(null);
  const [showTemplatePopup, setShowTemplatePopup] = useState(false);
  const [templateFormat, setTemplateFormat] = useState<'xlsx' | 'csv'>('xlsx');
  const [isDownloadingTemplate, setIsDownloadingTemplate] = useState(false);

  // Fetch user's pending batches
  const { data: pendingBatchesData, isLoading: batchesLoading } = useQuery({
    queryKey: ['pending-batches'],
    queryFn: () => uploadApi.getPendingBatches(),
  });

  // Fetch gateways for dropdown
  const { data: gateways, isLoading: gatewaysLoading } = useQuery({
    queryKey: ['gateways'],
    queryFn: () => gatewaysApi.getGateways(),
  });

  // Fetch files for selected batch
  const { data: filesData, isLoading: filesLoading } = useQuery({
    queryKey: ['batch-files', selectedBatch],
    queryFn: () => uploadApi.listFiles(selectedBatch),
    enabled: !!selectedBatch,
  });

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: async ({ batchId, gateway, file }: { batchId: string; gateway: string; file: File }) => {
      return uploadApi.uploadFile(batchId, gateway, file);
    },
    onSuccess: (data) => {
      toast.success(`File uploaded: ${data.filename}`);
      setSelectedFile(null);
      setValidationResult(null);
      queryClient.invalidateQueries({ queryKey: ['batch-files', selectedBatch] });
      queryClient.invalidateQueries({ queryKey: ['batches'] });
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async ({ batchId, filename, gateway }: { batchId: string; filename: string; gateway: string }) => {
      return uploadApi.deleteFile(batchId, filename, gateway);
    },
    onSuccess: (data) => {
      toast.success(data.message);
      setDeleteTarget(null);
      queryClient.invalidateQueries({ queryKey: ['batch-files', selectedBatch] });
      queryClient.invalidateQueries({ queryKey: ['batches'] });
    },
    onError: (err) => {
      toast.error(getErrorMessage(err));
      setDeleteTarget(null);
    },
  });

  // Validate file on selection
  const handleFileSelect = async (files: File[]) => {
    const file = files[0] || null;
    setSelectedFile(file);
    setValidationResult(null);

    if (file) {
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
  };

  const handleUpload = () => {
    if (!selectedBatch || !selectedGateway || !selectedFile) {
      toast.error('Please select a batch, gateway, and file');
      return;
    }

    uploadMutation.mutate({
      batchId: selectedBatch,
      gateway: selectedGateway,
      file: selectedFile,
    });
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
      const blob = await uploadApi.downloadFile(selectedBatch, filename, gateway);
      downloadFile(blob, filename);
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  const handleConfirmDelete = () => {
    if (deleteTarget && selectedBatch) {
      deleteMutation.mutate({
        batchId: selectedBatch,
        filename: deleteTarget.filename,
        gateway: deleteTarget.gateway,
      });
    }
  };

  // Build gateway options
  const gatewayOptions = gateways?.flatMap((g) => [
    { value: g.upload_name, label: `${g.display_name} (External)` },
    { value: g.internal_upload_name, label: `${g.display_name} (Internal)` },
  ]) || [];

  // Build batch options
  const batchOptions = pendingBatchesData?.batches?.map((b) => ({
    value: b.batch_id,
    label: b.batch_id,
  })) || [];

  const isUploading = uploadMutation.isPending;
  const files = filesData?.files || [];

  if (batchesLoading || gatewaysLoading) return <PageLoading />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Upload Files</h1>
        <p className="text-gray-500 mt-1">Upload transaction files for reconciliation</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Form */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Upload Transaction File</CardTitle>
              <CardDescription>
                Select a batch and gateway, then upload your file. Max 2 files per gateway (one external, one internal).
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {batchOptions.length === 0 ? (
                <Alert variant="warning" title="No pending batches">
                  Create a batch first before uploading files.
                </Alert>
              ) : (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <SearchableSelect
                      label="Batch"
                      options={batchOptions}
                      value={selectedBatch}
                      onChange={(val) => {
                        setSelectedBatch(val);
                        setSelectedFile(null);
                        setValidationResult(null);
                      }}
                      placeholder="Select your batch"
                      searchPlaceholder="Search batch ID..."
                      emptyMessage="No pending batches"
                    />
                    <Select
                      label="Gateway"
                      options={gatewayOptions}
                      value={selectedGateway}
                      onChange={(e) => setSelectedGateway(e.target.value)}
                      placeholder="Select gateway"
                    />
                  </div>

                  <FileUpload
                    onFileSelect={handleFileSelect}
                    selectedFiles={selectedFile ? [selectedFile] : []}
                    onRemoveFile={handleRemoveFile}
                    accept=".xlsx,.csv"
                    disabled={!selectedBatch || !selectedGateway}
                    multiple={false}
                  />

                  {/* Validation Status */}
                  {selectedFile && (
                    <div
                      className={`p-4 rounded-lg border ${
                        isValidating
                          ? 'bg-gray-50 border-gray-200'
                          : validationResult?.valid
                          ? 'bg-green-50 border-green-200'
                          : 'bg-red-50 border-red-200'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        {isValidating ? (
                          <div className="h-5 w-5 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
                        ) : validationResult?.valid ? (
                          <CheckCircle className="h-5 w-5 text-green-600" />
                        ) : (
                          <XCircle className="h-5 w-5 text-red-600" />
                        )}
                        <div>
                          <p className="font-medium text-gray-900">{selectedFile.name}</p>
                          <p className={`text-sm ${
                            isValidating ? 'text-gray-500' :
                            validationResult?.valid ? 'text-green-600' : 'text-red-600'
                          }`}>
                            {isValidating ? 'Validating columns...' : validationResult?.message}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Upload Button */}
                  <Button
                    onClick={handleUpload}
                    disabled={
                      !selectedBatch ||
                      !selectedGateway ||
                      !selectedFile ||
                      isValidating ||
                      !validationResult?.valid
                    }
                    isLoading={isUploading}
                    className="w-full"
                  >
                    <Upload className="h-4 w-4 mr-2" />
                    Upload File
                  </Button>
                </>
              )}
            </CardContent>
          </Card>

          {/* Uploaded Files for Selected Batch */}
          {selectedBatch && (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Uploaded Files</CardTitle>
                  <CardDescription>
                    Files in batch {selectedBatch}
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <FolderOpen className="h-4 w-4" />
                  {files.length} file{files.length !== 1 ? 's' : ''}
                </div>
              </CardHeader>
              <CardContent className="p-0">
                {filesLoading ? (
                  <div className="p-6 text-center text-gray-500">Loading files...</div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Filename</TableHead>
                        <TableHead>Gateway</TableHead>
                        <TableHead>Size</TableHead>
                        <TableHead>Uploaded</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {files.length === 0 ? (
                        <TableEmpty
                          message="No files uploaded yet. Select a gateway and upload a file."
                          colSpan={5}
                        />
                      ) : (
                        files.map((file) => (
                          <TableRow key={file.id}>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                <FileSpreadsheet className="h-4 w-4 text-gray-400" />
                                <div>
                                  <p className="font-medium">{file.filename}</p>
                                  {file.original_filename !== file.filename && (
                                    <p className="text-xs text-gray-500">
                                      Original: {file.original_filename}
                                    </p>
                                  )}
                                </div>
                              </div>
                            </TableCell>
                            <TableCell>
                              <Badge variant="default">{file.gateway}</Badge>
                            </TableCell>
                            <TableCell className="text-gray-500">
                              {file.file_size ? formatBytes(file.file_size) : '-'}
                            </TableCell>
                            <TableCell className="text-gray-500">
                              <div>
                                <p className="text-sm">{file.uploaded_by || '-'}</p>
                                <p className="text-xs">{formatDateTime(file.uploaded_at)}</p>
                              </div>
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center justify-end gap-2">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleDownloadFile(file.filename, file.gateway)}
                                  className="text-blue-600 hover:text-blue-700"
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
                                  className="text-danger-600 hover:text-danger-700"
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
                )}
              </CardContent>
            </Card>
          )}
        </div>

        {/* Template Download & Column Guide */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Download Template</CardTitle>
              <CardDescription>
                Use this template to format your data correctly
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                variant="outline"
                className="w-full"
                onClick={() => setShowTemplatePopup(true)}
              >
                <Info className="h-4 w-4 mr-2" />
                View Format & Download Template
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Required Columns</CardTitle>
              <CardDescription>
                Your file must contain these columns
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-start gap-3 p-2 bg-gray-50 rounded">
                  <Badge variant="info" className="mt-0.5 shrink-0">Date</Badge>
                  <div className="text-sm">
                    <p className="text-gray-700">Transaction date</p>
                    <p className="text-gray-500 text-xs">Format: YYYY-DD-MM (mandatory)</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-2 bg-gray-50 rounded">
                  <Badge variant="info" className="mt-0.5 shrink-0">Reference</Badge>
                  <div className="text-sm">
                    <p className="text-gray-700">Transaction ID</p>
                    <p className="text-gray-500 text-xs">Unique identifier (mandatory)</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-2 bg-gray-50 rounded">
                  <Badge variant="info" className="mt-0.5 shrink-0">Details</Badge>
                  <div className="text-sm">
                    <p className="text-gray-700">Transaction narration</p>
                    <p className="text-gray-500 text-xs">Description (mandatory)</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-2 bg-gray-50 rounded">
                  <Badge variant="info" className="mt-0.5 shrink-0">Debit</Badge>
                  <div className="text-sm">
                    <p className="text-gray-700">Outgoing amount</p>
                    <p className="text-gray-500 text-xs">Number (can be empty)</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-2 bg-gray-50 rounded">
                  <Badge variant="info" className="mt-0.5 shrink-0">Credit</Badge>
                  <div className="text-sm">
                    <p className="text-gray-700">Incoming amount</p>
                    <p className="text-gray-500 text-xs">Number (can be empty)</p>
                  </div>
                </div>
              </div>

              <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
                <p className="text-sm text-blue-800">
                  <strong>File naming:</strong> Files are automatically renamed to{' '}
                  <code className="bg-blue-100 px-1 rounded">{'{gateway}.ext'}</code> and stored in
                  a gateway subdirectory within your batch.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
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
              <div className="flex items-center justify-between py-2">
                <div>
                  <p className="text-sm font-medium text-gray-900">Date</p>
                  <p className="text-xs text-gray-500">Transaction date</p>
                </div>
                <div className="text-right">
                  <Badge variant="warning" className="text-xs">Mandatory</Badge>
                  <p className="text-xs text-gray-500 mt-0.5">YYYY-DD-MM</p>
                </div>
              </div>
              <div className="flex items-center justify-between py-2">
                <div>
                  <p className="text-sm font-medium text-gray-900">Reference</p>
                  <p className="text-xs text-gray-500">Transaction ID / unique identifier</p>
                </div>
                <div className="text-right">
                  <Badge variant="warning" className="text-xs">Mandatory</Badge>
                  <p className="text-xs text-gray-500 mt-0.5">Text/Number</p>
                </div>
              </div>
              <div className="flex items-center justify-between py-2">
                <div>
                  <p className="text-sm font-medium text-gray-900">Details</p>
                  <p className="text-xs text-gray-500">Transaction narration / description</p>
                </div>
                <div className="text-right">
                  <Badge variant="warning" className="text-xs">Mandatory</Badge>
                  <p className="text-xs text-gray-500 mt-0.5">Text</p>
                </div>
              </div>
              <div className="flex items-center justify-between py-2">
                <div>
                  <p className="text-sm font-medium text-gray-900">Debit</p>
                  <p className="text-xs text-gray-500">Outgoing amount</p>
                </div>
                <div className="text-right">
                  <Badge variant="default" className="text-xs">Optional</Badge>
                  <p className="text-xs text-gray-500 mt-0.5">Number</p>
                </div>
              </div>
              <div className="flex items-center justify-between py-2">
                <div>
                  <p className="text-sm font-medium text-gray-900">Credit</p>
                  <p className="text-xs text-gray-500">Incoming amount</p>
                </div>
                <div className="text-right">
                  <Badge variant="default" className="text-xs">Optional</Badge>
                  <p className="text-xs text-gray-500 mt-0.5">Number</p>
                </div>
              </div>
            </div>
          </div>

          <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
            <p className="text-xs text-blue-800">
              The template includes a sample row with the current date in the expected format (YYYY-DD-MM) as guidance. Column names are case-insensitive.
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
          <Button
            onClick={handleDownloadTemplate}
            isLoading={isDownloadingTemplate}
          >
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
