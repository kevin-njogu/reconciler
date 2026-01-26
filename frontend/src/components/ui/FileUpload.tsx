import { useCallback, useState, type DragEvent, type ChangeEvent } from 'react';
import { Upload, X, FileSpreadsheet } from 'lucide-react';
import { cn } from '@/lib/utils';

interface FileUploadProps {
  onFileSelect: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
  maxSize?: number; // in MB
  disabled?: boolean;
  selectedFiles?: File[];
  onRemoveFile?: (index: number) => void;
}

export function FileUpload({
  onFileSelect,
  accept = '.xlsx,.xls,.csv',
  multiple = false,
  maxSize = 10,
  disabled = false,
  selectedFiles = [],
  onRemoveFile,
}: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validateFiles = useCallback(
    (files: FileList | File[]): File[] => {
      const validFiles: File[] = [];
      const maxSizeBytes = maxSize * 1024 * 1024;

      Array.from(files).forEach((file) => {
        if (file.size > maxSizeBytes) {
          setError(`File "${file.name}" exceeds ${maxSize}MB limit`);
          return;
        }

        const extension = '.' + file.name.split('.').pop()?.toLowerCase();
        const acceptedExtensions = accept.split(',').map((ext) => ext.trim().toLowerCase());
        if (!acceptedExtensions.includes(extension)) {
          setError(`File "${file.name}" has invalid format. Accepted: ${accept}`);
          return;
        }

        validFiles.push(file);
      });

      return validFiles;
    },
    [accept, maxSize]
  );

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragging(false);
      setError(null);

      if (disabled) return;

      const files = e.dataTransfer.files;
      const validFiles = validateFiles(files);
      if (validFiles.length > 0) {
        onFileSelect(multiple ? validFiles : [validFiles[0]]);
      }
    },
    [disabled, multiple, onFileSelect, validateFiles]
  );

  const handleChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      setError(null);
      const files = e.target.files;
      if (!files) return;

      const validFiles = validateFiles(files);
      if (validFiles.length > 0) {
        onFileSelect(multiple ? validFiles : [validFiles[0]]);
      }

      // Reset input
      e.target.value = '';
    },
    [multiple, onFileSelect, validateFiles]
  );

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="w-full">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          'relative border-2 border-dashed rounded-lg p-8 text-center transition-colors',
          isDragging ? 'border-primary-400 bg-primary-50' : 'border-neutral-300 hover:border-neutral-400',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      >
        <input
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={handleChange}
          disabled={disabled}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
        />
        <Upload className="mx-auto h-12 w-12 text-neutral-400" />
        <p className="mt-4 text-sm text-neutral-600">
          <span className="font-semibold text-primary-500">Click to upload</span> or drag and drop
        </p>
        <p className="mt-1 text-xs text-neutral-500">
          {accept.replace(/\./g, '').toUpperCase()} files up to {maxSize}MB
        </p>
      </div>

      {error && <p className="mt-2 text-sm text-danger-600">{error}</p>}

      {selectedFiles.length > 0 && (
        <div className="mt-4 space-y-2">
          {selectedFiles.map((file, index) => (
            <div
              key={`${file.name}-${index}`}
              className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg"
            >
              <div className="flex items-center gap-3">
                <FileSpreadsheet className="h-8 w-8 text-success-500" />
                <div>
                  <p className="text-sm font-medium text-neutral-900">{file.name}</p>
                  <p className="text-xs text-neutral-500">{formatFileSize(file.size)}</p>
                </div>
              </div>
              {onRemoveFile && (
                <button
                  onClick={() => onRemoveFile(index)}
                  className="p-1 text-neutral-400 hover:text-danger-500 rounded"
                >
                  <X className="h-5 w-5" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
