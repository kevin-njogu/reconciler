# File Upload System

## Overview

The file upload system manages transaction files for reconciliation batches. Files are organized in gateway subdirectories within each batch, supporting both external bank statements and internal records.

## Directory Structure

```
uploads/
  {batch_id}/
    {external_gateway}/
      {gateway_name}.{ext}     (external file)
      workpay_{gateway}.{ext}  (internal file)
```

### Examples

```
uploads/
  20260124_abc123/
    equity/
      equity.xlsx              (Equity bank statement)
      workpay_equity.xlsx      (Internal Workpay records for Equity)
    mpesa/
      mpesa.csv                (M-Pesa statement)
      workpay_mpesa.csv        (Internal Workpay records for M-Pesa)
```

## Business Rules

1. **Batch Ownership**: Users can only upload files to their own pending batches
2. **Max 2 Files per Gateway**: Each gateway subdirectory holds at most 2 files (one external, one internal)
3. **File Replacement**: Uploading the same file type replaces the existing file
4. **Supported Formats**: `.xlsx` and `.csv` only
5. **Column Validation**: Files must contain: `Date`, `Reference`, `Details`, `Debit`, `Credit`
6. **File Renaming**: Files are renamed to `{gateway_name}.{ext}` on upload
7. **Autonomous Deletion**: Users can delete their own files without admin approval
8. **Closed Batch Protection**: Files cannot be added or removed from closed batches

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/upload/pending-batches` | Get current user's pending batches for dropdown |
| POST | `/api/v1/upload/file` | Upload a file to a batch's gateway subdirectory |
| DELETE | `/api/v1/upload/file` | Delete an uploaded file |
| GET | `/api/v1/upload/file/download` | Download an uploaded file |
| GET | `/api/v1/upload/files` | List all files for a batch |
| POST | `/api/v1/upload/validate` | Validate file columns before upload |
| GET | `/api/v1/upload/template` | Download upload template (current date as sample) |
| GET | `/api/v1/upload/template-info` | Get template column info for download popup |

## Upload Workflow

### 1. Select Batch

```
GET /api/v1/upload/pending-batches
```

Returns only the current user's pending batches. The dropdown is populated with these options.

### 2. Select Gateway

Choose from available gateways:
- **External**: `equity`, `kcb`, `mpesa` (bank statements)
- **Internal**: `workpay_equity`, `workpay_kcb`, `workpay_mpesa` (internal records)

### 3. Upload File

```
POST /api/v1/upload/file?batch_id=X&gateway_name=equity
Content-Type: multipart/form-data
```

The file is:
1. Validated for correct extension (`.xlsx` or `.csv`)
2. Validated for required columns
3. Renamed to `{gateway_name}.{ext}` (e.g., `equity.xlsx`)
4. Stored in `{batch_id}/{external_gateway}/` directory
5. Recorded in `batch_files` database table

**Response:**
```json
{
  "message": "equity.xlsx uploaded successfully",
  "batch_id": "20260124_abc123",
  "gateway": "equity",
  "upload_gateway": "equity",
  "filename": "equity.xlsx",
  "original_filename": "bank_statement_jan.xlsx",
  "file_size": 15234,
  "uploaded_by": "john"
}
```

### 4. Manage Files

**List files:**
```
GET /api/v1/upload/files?batch_id=X
```

**Delete a file:**
```
DELETE /api/v1/upload/file?batch_id=X&filename=equity.xlsx&gateway=equity
```

**Download a file:**
```
GET /api/v1/upload/file/download?batch_id=X&filename=equity.xlsx&gateway=equity
```

## Gateway Mapping

When a user uploads with an internal gateway (e.g., `workpay_equity`), the system:
1. Derives the external gateway: `workpay_equity` → `equity`
2. Uses `equity` as the subdirectory name
3. Names the file `workpay_equity.{ext}`

| Upload Gateway | Subdirectory | Stored Filename |
|---------------|-------------|-----------------|
| `equity` | `equity/` | `equity.xlsx` |
| `workpay_equity` | `equity/` | `workpay_equity.xlsx` |
| `mpesa` | `mpesa/` | `mpesa.csv` |
| `workpay_mpesa` | `mpesa/` | `workpay_mpesa.csv` |

## Storage Backends

The upload system uses a pluggable storage backend:

- **Local Storage** (`STORAGE_BACKEND=local`): Files stored on local filesystem at `LOCAL_UPLOADS_PATH`
- **GCS Storage** (`STORAGE_BACKEND=gcs`): Files stored in Google Cloud Storage bucket `GCS_BUCKET`

Both backends implement the same interface with gateway subdirectory support.

## Frontend Upload Page

The upload page provides:
1. **Batch Dropdown**: Shows only the current user's pending batches
2. **Gateway Select**: Lists all configured gateways (external + internal)
3. **File Upload**: Drag-and-drop or click to select, with real-time column validation
4. **Upload Status**: Visual feedback (validating → valid/invalid → uploading → success)
5. **File List**: Table of uploaded files for the selected batch with:
   - Filename (stored name + original name)
   - Gateway badge
   - File size
   - Upload date and user
   - Download button
   - Delete button (with confirmation modal)

## Template System

### Template Columns

The upload template has a unified format with 5 columns:

| Column | Description | Format | Mandatory |
|--------|-------------|--------|-----------|
| Date | Transaction date | YYYY-DD-MM | Yes |
| Reference | Transaction ID / unique identifier | Text/Number | Yes |
| Details | Transaction narration / description | Text | Yes |
| Debit | Outgoing amount | Number | No |
| Credit | Incoming amount | Number | No |

### Template Download Workflow

1. User clicks "Download Template" button in the upload page
2. A popup displays the expected column formats and mandatory fields
3. User selects format (Excel or CSV)
4. User clicks "Download" to get the template file
5. The template includes a sample row with the current date in YYYY-DD-MM format as guidance

### Template API

**Download template:**
```
GET /api/v1/upload/template?format=xlsx
```

The template is named `template.xlsx` or `template.csv` depending on the selected format.
The Date column sample row contains the current date in YYYY-DD-MM format.

**Get column info (for popup):**
```
GET /api/v1/upload/template-info
```

Returns column definitions, formats, mandatory flags, and usage notes.

### Column Mapping

Template columns map to database columns:

| Template Column | DB Column | Notes |
|----------------|-----------|-------|
| Date | `date` | Parsed from YYYY-DD-MM to datetime |
| Reference | `transaction_id` | Used for reconciliation matching |
| Details | `narrative` | Used for charge keyword filtering |
| Debit | `debit` | Numeric, used for amount matching |
| Credit | `credit` | Numeric, used for amount matching |

Column matching during upload validation is case-insensitive.

## Error Handling

- **Invalid gateway**: Returns 400 with list of valid gateways
- **Batch not found**: Returns 404
- **Not batch owner**: Returns 403
- **Batch closed**: Returns 400
- **Max files exceeded**: Returns 400 with message to delete first
- **Invalid columns**: Returns 400 with missing columns list
- **Unsupported format**: Returns 400 with allowed formats
