import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  Upload,
  GitCompare,
  FileText,
  Calendar,
  Hash,
  User,
  File,
  FileSpreadsheet,
} from 'lucide-react';
import { batchesApi, getErrorMessage } from '@/api';
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Badge,
  getStatusBadgeVariant,
  PageLoading,
  Alert,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  TableEmpty,
} from '@/components/ui';
import { formatDateTime, formatBytes } from '@/lib/utils';

export function BatchDetailPage() {
  const { batchId } = useParams<{ batchId: string }>();

  const { data: batch, isLoading, error } = useQuery({
    queryKey: ['batch', batchId],
    queryFn: () => batchesApi.getById(batchId!),
    enabled: !!batchId,
  });

  const {
    data: filesData,
    isLoading: filesLoading,
    error: filesError,
  } = useQuery({
    queryKey: ['batch-files', batchId],
    queryFn: () => batchesApi.getFiles(batchId!),
    enabled: !!batchId,
  });

  if (isLoading) return <PageLoading />;

  if (error) {
    return (
      <Alert variant="error" title="Error loading batch">
        {getErrorMessage(error)}
      </Alert>
    );
  }

  if (!batch) {
    return (
      <Alert variant="error" title="Batch not found">
        The requested batch could not be found.
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/batches">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Batch Details</h1>
          <p className="text-gray-500 mt-1">View batch information and files</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Batch Info */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Batch Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Hash className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Batch ID</p>
                  <p className="font-mono">{batch.batch_id}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <Calendar className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Created At</p>
                  <p>{formatDateTime(batch.created_at)}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <User className="h-5 w-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Created By</p>
                  <p>{batch.created_by || 'Unknown'}</p>
                </div>
              </div>
              <div>
                <p className="text-sm text-gray-500 mb-2">Status</p>
                <Badge variant={getStatusBadgeVariant(batch.status)} className="text-sm">
                  {batch.status}
                </Badge>
              </div>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-orange-100 rounded-lg">
                  <File className="h-5 w-5 text-orange-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Files</p>
                  <p>{batch.file_count ?? 0}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-cyan-100 rounded-lg">
                  <FileSpreadsheet className="h-5 w-5 text-cyan-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Transactions</p>
                  <p>{batch.transaction_count ?? 0}</p>
                </div>
              </div>
              {batch.closed_at && (
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-gray-100 rounded-lg">
                    <Calendar className="h-5 w-5 text-gray-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Closed At</p>
                    <p>{formatDateTime(batch.closed_at)}</p>
                  </div>
                </div>
              )}
              {batch.unreconciled_count !== undefined && batch.unreconciled_count > 0 && (
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-red-100 rounded-lg">
                    <FileSpreadsheet className="h-5 w-5 text-red-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Unreconciled</p>
                    <p className="text-red-600">{batch.unreconciled_count}</p>
                  </div>
                </div>
              )}
            </div>
            {batch.description && (
              <div className="mt-4 pt-4 border-t">
                <p className="text-sm text-gray-500 mb-1">Description</p>
                <p className="text-gray-700">{batch.description}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {batch.status === 'pending' && (
              <>
                <Link to={`/upload?batch_id=${batch.batch_id}`} className="block">
                  <Button variant="outline" className="w-full justify-start">
                    <Upload className="h-4 w-4 mr-2" />
                    Upload Files
                  </Button>
                </Link>
                <Link to={`/reconciliation?batch_id=${batch.batch_id}`} className="block">
                  <Button variant="outline" className="w-full justify-start">
                    <GitCompare className="h-4 w-4 mr-2" />
                    Run Reconciliation
                  </Button>
                </Link>
              </>
            )}
            {batch.status === 'completed' && (
              <Link to={`/reports?batch_id=${batch.batch_id}`} className="block">
                <Button variant="outline" className="w-full justify-start">
                  <FileText className="h-4 w-4 mr-2" />
                  Download Report
                </Button>
              </Link>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Files Section */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Uploaded Files</CardTitle>
          {batch.status === 'pending' && (
            <Link to={`/upload?batch_id=${batch.batch_id}`}>
              <Button variant="outline" size="sm">
                <Upload className="h-4 w-4 mr-2" />
                Upload More
              </Button>
            </Link>
          )}
        </CardHeader>
        <CardContent className="p-0">
          {filesLoading ? (
            <div className="p-6 text-center text-gray-500">Loading files...</div>
          ) : filesError ? (
            <div className="p-6">
              <Alert variant="error" title="Error loading files">
                {getErrorMessage(filesError)}
              </Alert>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Filename</TableHead>
                  <TableHead>Gateway</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead>Uploaded By</TableHead>
                  <TableHead>Uploaded At</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {!filesData?.files?.length ? (
                  <TableEmpty
                    message="No files uploaded yet. Upload files to start reconciliation."
                    colSpan={5}
                  />
                ) : (
                  filesData.files.map((file) => (
                    <TableRow key={file.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <FileSpreadsheet className="h-4 w-4 text-gray-400" />
                          <div>
                            <p>{file.filename}</p>
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
                      <TableCell className="text-gray-500">{file.uploaded_by || '-'}</TableCell>
                      <TableCell className="text-gray-500">
                        {formatDateTime(file.uploaded_at)}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Workflow Guide */}
      <Card>
        <CardHeader>
          <CardTitle>Reconciliation Workflow</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="flex flex-col items-center text-green-600">
              <div className="w-10 h-10 rounded-full flex items-center justify-center bg-green-100">
                <span className="font-bold">1</span>
              </div>
              <p className="text-sm mt-2 font-medium">Create Batch</p>
              <p className="text-xs text-gray-500">Done</p>
            </div>
            <div className="flex-1 h-1 bg-gray-200 mx-4">
              <div className={`h-full ${(batch.file_count ?? 0) > 0 ? 'bg-green-500' : 'bg-gray-200'}`} />
            </div>
            <div
              className={`flex flex-col items-center ${(batch.file_count ?? 0) > 0 ? 'text-green-600' : 'text-gray-400'}`}
            >
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center ${(batch.file_count ?? 0) > 0 ? 'bg-green-100' : 'bg-gray-100'}`}
              >
                <span className="font-bold">2</span>
              </div>
              <p className="text-sm mt-2 font-medium">Upload Files</p>
              <p className="text-xs text-gray-500">{(batch.file_count ?? 0) > 0 ? 'Done' : 'Pending'}</p>
            </div>
            <div className="flex-1 h-1 bg-gray-200 mx-4">
              <div className={`h-full ${(batch.transaction_count ?? 0) > 0 ? 'bg-green-500' : 'bg-gray-200'}`} />
            </div>
            <div
              className={`flex flex-col items-center ${(batch.transaction_count ?? 0) > 0 ? 'text-green-600' : 'text-gray-400'}`}
            >
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center ${(batch.transaction_count ?? 0) > 0 ? 'bg-green-100' : 'bg-gray-100'}`}
              >
                <span className="font-bold">3</span>
              </div>
              <p className="text-sm mt-2 font-medium">Reconcile</p>
              <p className="text-xs text-gray-500">{(batch.transaction_count ?? 0) > 0 ? 'Done' : 'Pending'}</p>
            </div>
            <div className="flex-1 h-1 bg-gray-200 mx-4">
              <div className={`h-full ${batch.status === 'completed' ? 'bg-green-500' : 'bg-gray-200'}`} />
            </div>
            <div
              className={`flex flex-col items-center ${batch.status === 'completed' ? 'text-green-600' : 'text-gray-400'}`}
            >
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center ${batch.status === 'completed' ? 'bg-green-100' : 'bg-gray-100'}`}
              >
                <span className="font-bold">4</span>
              </div>
              <p className="text-sm mt-2 font-medium">Close Batch</p>
              <p className="text-xs text-gray-500">{batch.status === 'completed' ? 'Closed' : 'Pending'}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
