# Upload Operations Documentation

This document provides comprehensive documentation for the File Upload operations in the Payment Gateway Reconciliation System.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Upload Workflow](#upload-workflow)
4. [Backend Implementation](#backend-implementation)
   - [API Endpoints](#api-endpoints)
   - [Service Classes](#service-classes)
   - [Database Models](#database-models)
   - [Storage Backends](#storage-backends)
5. [Frontend Implementation](#frontend-implementation)
6. [Template Format](#template-format)
7. [File Naming Convention](#file-naming-convention)
8. [Validation Rules](#validation-rules)
9. [Role-Based Access Control](#role-based-access-control)
10. [Data Flow Examples](#data-flow-examples)

---

## Overview

The upload operations module handles file uploads for reconciliation batches. It provides a unified workflow for uploading financial records from both external sources (bank statements) and internal systems (Workpay records).

### Key Features

1. **Unified Template Format**: Single template for all gateways with standardized columns
2. **Gateway-Based File Naming**: Files are prefixed with gateway names for organization
3. **Column Validation**: Automatic validation of required columns before upload
4. **Pluggable Storage**: Supports local filesystem and Google Cloud Storage
5. **Batch Organization**: Files are grouped into batches for reconciliation
6. **Audit Trail**: Complete tracking of who uploaded what and when

### Key Design Principles

1. **Unified Template**: Same template columns for all gateways (external and internal)
2. **Gateway Prefix**: Files are prefixed with gateway name during upload
3. **Validation First**: Column validation before storage to prevent invalid data
4. **Batch Isolation**: Each batch has its own directory/namespace
5. **Flexible Storage**: Pluggable backend supports local and cloud storage

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                           │
├─────────────────────────────────────────────────────────────────┤
│  UploadPage.tsx                                                 │
│  - Download template                                            │
│  - Select batch and gateway                                     │
│  - Upload files with validation                                 │
│  - View uploaded files                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API Controller Layer                        │
│                   app/controller/upload.py                      │
├─────────────────────────────────────────────────────────────────┤
│  POST /validate        - Validate file columns                  │
│  POST /file            - Upload single file                     │
│  POST /files           - Upload multiple files                  │
│  GET  /template        - Download template                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Service Layer                               │
├─────────────────────────────────────────────────────────────────┤
│  FileUpload (upload_files.py)    │  BatchCreation (batch.py)   │
│  - File validation               │  - Batch lifecycle          │
│  - Gateway validation            │  - File record tracking     │
│  - Storage operations            │  - Status management        │
├──────────────────────────────────┼─────────────────────────────┤
│  TemplateGenerator               │  Storage Backend            │
│  - Generate XLSX/CSV template    │  - LocalStorage             │
│  - Pre-fill dates                │  - GcsStorage               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Database Layer                             │
│               app/sqlModels/batchEntities.py                    │
├─────────────────────────────────────────────────────────────────┤
│  batches table              │  batch_files table                │
│  - id, batch_id             │  - id, batch_id, filename         │
│  - status, description      │  - original_filename, gateway     │
│  - created_by_id            │  - file_size, content_type        │
│  - created_at, updated_at   │  - uploaded_by_id, uploaded_at    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Storage Layer                              │
│                   app/storage/                                  │
├─────────────────────────────────────────────────────────────────┤
│  LocalStorage                │  GcsStorage                      │
│  uploads/{batch_id}/         │  gs://{bucket}/{batch_id}/       │
│    equity_statement.xlsx     │    equity_statement.xlsx         │
│    workpay_equity_file.xlsx  │    workpay_equity_file.xlsx      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Upload Workflow

### Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          STEP 1: BATCH CREATION                          │
├──────────────────────────────────────────────────────────────────────────┤
│  POST /api/v1/batch                                                      │
│  - Creates new batch record with unique ID                               │
│  - Status: PENDING                                                       │
│  - Creates storage directory for batch                                   │
│  - Records: batch_id, created_by, created_at                             │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      STEP 2: DOWNLOAD TEMPLATE                           │
├──────────────────────────────────────────────────────────────────────────┤
│  GET /api/v1/upload/template?format=xlsx                                  │
│  - Generates template with current date as sample (YYYY-DD-MM)            │
│  - Columns: Date, Reference, Details, Debit, Credit                      │
│  - Same template for all gateways                                        │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    STEP 3: POPULATE TEMPLATE                             │
├──────────────────────────────────────────────────────────────────────────┤
│  User fills template with financial data:                                │
│  - External: Bank statement data (debits, credits)                       │
│  - Internal: Workpay payout records                                      │
│  - Transaction IDs must match for reconciliation                         │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      STEP 4: VALIDATE FILE                               │
├──────────────────────────────────────────────────────────────────────────┤
│  POST /api/v1/upload/validate (optional, recommended)                    │
│  - Checks for required columns                                           │
│  - Case-insensitive column matching                                      │
│  - Returns: valid (bool), found_columns, missing_columns                 │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        STEP 5: UPLOAD FILE                               │
├──────────────────────────────────────────────────────────────────────────┤
│  POST /api/v1/upload/file                                                │
│  - batch_id: Target batch                                                │
│  - gateway_name: equity, kcb, mpesa, workpay_equity, etc.                │
│  - skip_validation: true/false (default: false)                          │
│                                                                          │
│  Actions:                                                                │
│  1. Validate gateway name against database                               │
│  2. Validate file columns (unless skip_validation=true)                  │
│  3. Prefix filename with gateway: equity_statement.xlsx                  │
│  4. Save to storage: /{batch_id}/equity_statement.xlsx                   │
│  5. Create BatchFile record for audit trail                              │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      STEP 6: REPEAT FOR ALL FILES                        │
├──────────────────────────────────────────────────────────────────────────┤
│  For reconciliation, upload both:                                        │
│  - External file: gateway_name=equity → equity_statement.xlsx            │
│  - Internal file: gateway_name=workpay_equity → workpay_equity_file.xlsx │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         READY FOR RECONCILIATION                         │
├──────────────────────────────────────────────────────────────────────────┤
│  POST /api/v1/reconcile/save?batch_id={batch_id}&external_gateway=equity │
│  - Reads equity_* and workpay_equity_* files from batch                  │
│  - Matches Transaction IDs                                               │
│  - Saves results to database                                             │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Backend Implementation

### API Endpoints

**Base URL:** `/api/v1/upload`

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| POST | `/validate` | Validate file columns | Users |
| POST | `/file` | Upload single file | Users |
| POST | `/files` | Upload multiple files | Users |
| GET | `/template` | Download upload template | Users |

---

#### POST `/validate`

Validate file columns before upload.

**Request:**
- `file`: File to validate (multipart/form-data)

**Response:**

```json
{
  "valid": true,
  "filename": "statement.xlsx",
  "file_size": 15234,
  "required_columns": ["Date", "Reference", "Details", "Debit", "Credit"],
  "found_columns": ["Date", "Reference", "Details", "Debit", "Credit"],
  "missing_columns": [],
  "message": "All required columns found"
}
```

**Error Response (missing columns):**

```json
{
  "valid": false,
  "filename": "statement.xlsx",
  "file_size": 15234,
  "required_columns": ["Date", "Reference", "Details", "Debit", "Credit"],
  "found_columns": ["Date", "Details", "Amount"],
  "missing_columns": ["Reference", "Debit", "Credit"],
  "message": "Missing columns: Reference, Debit, Credit"
}
```

---

#### POST `/file`

Upload a single file to a batch.

**Query Parameters:**
- `batch_id` (required): Batch ID to upload file to
- `gateway_name` (required): Gateway name to prefix the file
- `skip_validation` (optional): Skip column validation (default: false)

**Request:**
- `file`: File to upload (multipart/form-data)

**Response:**

```json
{
  "message": "equity_statement.xlsx uploaded successfully",
  "batch_id": "20240115_143022_a1b2c3d4",
  "gateway": "equity",
  "filename": "equity_statement.xlsx",
  "original_filename": "statement.xlsx",
  "file_size": 15234,
  "uploaded_by": "john.doe",
  "validation": {
    "found_columns": ["Date", "Reference", "Details", "Debit", "Credit"],
    "missing_columns": []
  }
}
```

**Error Response (missing columns):**

```json
{
  "error": "File is missing required columns",
  "missing_columns": ["Reference"],
  "found_columns": ["Date", "Details", "Debit", "Credit"],
  "required_columns": ["Date", "Reference", "Details", "Debit", "Credit"],
  "hint": "Download the template and ensure your file has all required columns. Use skip_validation=true to bypass this check."
}
```

---

#### POST `/files`

Upload multiple files to a batch (all with same gateway prefix).

**Query Parameters:**
- `batch_id` (required): Batch ID to upload files to
- `gateway_name` (required): Gateway name to prefix all files
- `skip_validation` (optional): Skip column validation (default: false)

**Request:**
- `files`: Multiple files to upload (multipart/form-data)

**Response:**

```json
{
  "message": "3 file(s) uploaded successfully",
  "batch_id": "20240115_143022_a1b2c3d4",
  "gateway": "equity",
  "files": [
    {
      "filename": "equity_jan_statement.xlsx",
      "original_filename": "jan_statement.xlsx",
      "file_size": 15234
    },
    {
      "filename": "equity_feb_statement.xlsx",
      "original_filename": "feb_statement.xlsx",
      "file_size": 18456
    }
  ],
  "uploaded_by": "john.doe"
}
```

---

#### GET `/template`

Download upload template. Uses current date as sample row in YYYY-DD-MM format.

**Query Parameters:**
- `format` (optional): Output format - `xlsx` (default) or `csv`

**Response:**
- StreamingResponse with file download
- Content-Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` (xlsx) or `text/csv` (csv)
- Content-Disposition: `attachment; filename=template.xlsx`

---

### Batch Management Endpoints

**Base URL:** `/api/v1/batch`

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| POST | `/` | Create new batch | Users |
| GET | `/{batch_id}` | Get batch details | Users |
| GET | `/` | List all batches | Users |
| PATCH | `/{batch_id}` | Update batch description | Users |
| PATCH | `/{batch_id}/status` | Update batch status | Users |
| DELETE | `/{batch_id}` | Delete batch and all data | Admin |
| GET | `/{batch_id}/files` | Get batch files | Users |
| DELETE | `/{batch_id}/files/{file_id}` | Delete single file | Admin |

---

#### POST `/` (Create Batch)

Create a new batch for file uploads.

**Request Body:**

```json
{
  "description": "January 2024 Equity Reconciliation"
}
```

**Response:**

```json
{
  "batch_id": "20240115_143022_a1b2c3d4",
  "batch_db_id": 42,
  "status": "pending",
  "description": "January 2024 Equity Reconciliation",
  "created_by": "john.doe",
  "message": "Batch created successfully"
}
```

---

#### GET `/{batch_id}` (Get Batch)

Get batch details.

**Response:**

```json
{
  "batch_id": "20240115_143022_a1b2c3d4",
  "batch_db_id": 42,
  "status": "pending",
  "description": "January 2024 Equity Reconciliation",
  "created_at": "2024-01-15T14:30:22Z",
  "updated_at": "2024-01-15T14:35:00Z",
  "created_by": "john.doe",
  "created_by_id": 5,
  "file_count": 2,
  "transaction_count": 0
}
```

---

#### DELETE `/{batch_id}` (Delete Batch)

Delete batch and all related data (Admin only).

**Response:**

```json
{
  "message": "Batch deleted successfully",
  "batch_id": "20240115_143022_a1b2c3d4",
  "transactions_deleted": 150,
  "files_deleted": 2
}
```

---

### Service Classes

#### FileUpload (`app/upload/upload_files.py`)

Main service for file upload operations.

```python
class FileUpload:
    def __init__(self, db: Session, storage: Optional[StorageBackend] = None)

    # Batch operations
    def create_batch(self) -> Batch
    def set_batch(self, batch_id: str) -> None
    def update_batch_status(self, status: BatchStatus) -> None

    # Validation
    def validate_gateway_name(self, gateway_name: str) -> str
    def validate_file(self, file: UploadFile) -> None
    def validate_file_columns(self, content: bytes, filename: str) -> Tuple[List[str], List[str]]

    # Upload operations
    async def save_file(self, file: UploadFile, gateway_name: str) -> str
    async def save_files(self, files: List[UploadFile], gateway_name: str) -> List[str]
    def list_batch_files(self) -> List[str]
```

#### BatchCreation (`app/upload/batch_creation.py`)

Service for batch lifecycle management.

```python
class BatchCreation:
    def __init__(self, db: Session)

    # Batch CRUD
    def create_batch(self, created_by_id: int, description: str) -> Batch
    def get_batch_by_id(self, batch_id: str) -> Optional[Batch]
    def update_batch_status(self, batch_id: str, status: BatchStatus) -> None
    def delete_batch(self, batch_id: str) -> Dict[str, Any]

    # File tracking
    def add_file_record(self, batch_id: str, filename: str, ...) -> BatchFile
    def get_batch_files(self, batch_id: str) -> List[BatchFile]
    def delete_file_record(self, batch_id: str, file_id: int) -> bool
```

#### TemplateGenerator (`app/upload/template_generator.py`)

Service for generating upload templates.

```python
class TemplateGenerator:
    def generate_template(self, template_date: date, format: TemplateFormat) -> bytes
    def get_template_filename(self, format: TemplateFormat) -> str
    def get_content_type(self, format: TemplateFormat) -> str
    @staticmethod
    def get_column_info() -> dict  # Column info for download popup
```

---

### Database Models

#### Batch (`app/sqlModels/batchEntities.py`)

```python
class BatchStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Batch(Base):
    __tablename__ = "batches"

    id: int                    # Primary key
    batch_id: str              # Unique batch identifier (e.g., "20240115_143022_a1b2c3d4")
    status: str                # BatchStatus value
    description: str           # Optional description
    created_by_id: int         # FK to User
    created_at: datetime       # Creation timestamp
    updated_at: datetime       # Last update timestamp
```

#### BatchFile (`app/sqlModels/batchEntities.py`)

```python
class BatchFile(Base):
    __tablename__ = "batch_files"

    id: int                    # Primary key
    batch_id: str              # FK to Batch.batch_id
    filename: str              # Stored filename (with gateway prefix)
    original_filename: str     # Original uploaded filename
    gateway: str               # Gateway name
    file_size: int             # File size in bytes
    content_type: str          # MIME type
    uploaded_by_id: int        # FK to User
    uploaded_at: datetime      # Upload timestamp
```

---

### Storage Backends

#### StorageBackend Interface (`app/storage/base.py`)

Abstract base class for storage operations.

```python
class StorageBackend(ABC):
    # Core operations
    def save_file(self, batch_id: str, filename: str, content: bytes) -> str
    def read_file_bytes(self, batch_id: str, filename: str) -> bytes
    def list_files(self, batch_id: str) -> List[str]
    def file_exists(self, batch_id: str, filename: str) -> bool

    # Directory operations
    def ensure_batch_directory(self, batch_id: str) -> None
    def delete_batch_directory(self, batch_id: str) -> int
    def batch_directory_exists(self, batch_id: str) -> bool

    # Utilities
    def find_file_by_prefix(self, batch_id: str, prefix: str) -> Optional[str]
    def is_supported_extension(self, filename: str) -> bool
```

#### LocalStorage (`app/storage/local_storage.py`)

Filesystem-based storage for development.

- Base path: `./uploads/{batch_id}/`
- Files: `{base_path}/{filename}`

#### GcsStorage (`app/storage/gcs_storage.py`)

Google Cloud Storage for production.

- Bucket: Configured via `GCS_BUCKET` environment variable
- Path: `gs://{bucket}/{batch_id}/{filename}`

**Configuration:**
- `STORAGE_BACKEND`: `local` or `gcs`
- `LOCAL_UPLOADS_PATH`: Path for local storage (default: `uploads`)
- `GCS_BUCKET`: GCS bucket name (required for gcs backend)

---

## Template Format

### Unified Template Columns

All uploads use the same template format regardless of gateway type.

| Column | Description | Format | Required |
|--------|-------------|--------|----------|
| Date | Transaction date | YYYY-DD-MM | Yes |
| Reference | Unique transaction identifier | Text/Number | Yes |
| Details | Transaction narration/description | Text | Yes |
| Debit | Debit amount (outgoing) | Number | No (can be empty) |
| Credit | Credit amount (incoming) | Number | No (can be empty) |

### Template Example

| Date | Reference | Details | Debit | Credit |
|------|---------------|-----------|-------|--------|
| 2026-24-01 | TXN123456 | SALARY PAYMENT - JOHN DOE | 50000.00 | |
| 2026-24-01 | TXN123457 | BANK CHARGE | 50.00 | |
| 2026-25-01 | TXN123458 | DEPOSIT RECEIVED | | 25000.00 |

### Supported File Formats

| Extension | Engine | Description |
|-----------|--------|-------------|
| `.xlsx` | openpyxl | Excel 2007+ (recommended) |
| `.xls` | xlrd | Excel 97-2003 |
| `.csv` | pandas | Comma-separated values |

---

## File Naming Convention

### Gateway Prefix Rules

Files are automatically prefixed with the gateway name during upload.

| Upload Gateway | File Prefix | Example |
|----------------|-------------|---------|
| equity | equity_ | equity_statement.xlsx |
| kcb | kcb_ | kcb_statement.xlsx |
| mpesa | mpesa_ | mpesa_statement.xlsx |
| workpay_equity | workpay_equity_ | workpay_equity_payouts.xlsx |
| workpay_kcb | workpay_kcb_ | workpay_kcb_payouts.xlsx |
| workpay_mpesa | workpay_mpesa_ | workpay_mpesa_payouts.xlsx |

### Reconciliation File Pairs

For each external gateway, you need two files:

| External Gateway | External File Pattern | Internal File Pattern |
|------------------|----------------------|----------------------|
| equity | equity_*.xlsx | workpay_equity_*.xlsx |
| kcb | kcb_*.xlsx | workpay_kcb_*.xlsx |
| mpesa | mpesa_*.xlsx | workpay_mpesa_*.xlsx |

---

## Validation Rules

### Column Validation

1. **Case-Insensitive**: Column matching ignores case ("DATE" matches "Date")
2. **Trimmed**: Leading/trailing whitespace is ignored
3. **All Required**: All 5 columns must be present by default

### Gateway Validation

1. Gateway name must exist in `gateway_configs` database table
2. Gateway must be active (`is_active = true`)
3. Valid upload gateways include both external gateways and internal prefixed versions

### File Validation

1. File must have a filename
2. File extension must be `.xlsx`, `.xls`, or `.csv`
3. File must be readable (not corrupted)

---

## Role-Based Access Control

### Endpoint Access Matrix

| Endpoint | User | Admin | Super Admin |
|----------|:----:|:-----:|:-----------:|
| POST `/upload/validate` | ✅ | ✅ | ❌ |
| POST `/upload/file` | ✅ | ✅ | ❌ |
| POST `/upload/files` | ✅ | ✅ | ❌ |
| GET `/upload/template` | ✅ | ✅ | ❌ |
| POST `/batch` | ✅ | ✅ | ❌ |
| GET `/batch/{id}` | ✅ | ✅ | ❌ |
| GET `/batch` | ✅ | ✅ | ❌ |
| PATCH `/batch/{id}` | ✅ | ✅ | ❌ |
| PATCH `/batch/{id}/status` | ✅ | ✅ | ❌ |
| DELETE `/batch/{id}` | ❌ | ✅ | ❌ |
| GET `/batch/{id}/files` | ✅ | ✅ | ❌ |
| DELETE `/batch/{id}/files/{file_id}` | ❌ | ✅ | ❌ |

---

## Data Flow Examples

### Example 1: Complete Upload Workflow

**Step 1: Create batch**

```bash
POST /api/v1/batch
Authorization: Bearer <user_token>

{
  "description": "January 2024 Equity Reconciliation"
}
```

Response:
```json
{
  "batch_id": "20240115_143022_a1b2c3d4",
  "status": "pending"
}
```

**Step 2: Download template**

```bash
GET /api/v1/upload/template?format=xlsx
Authorization: Bearer <user_token>
```

**Step 3: Upload external file (bank statement)**

```bash
POST /api/v1/upload/file?batch_id=20240115_143022_a1b2c3d4&gateway_name=equity
Authorization: Bearer <user_token>
Content-Type: multipart/form-data

file: @equity_january.xlsx
```

Response:
```json
{
  "message": "equity_equity_january.xlsx uploaded successfully",
  "batch_id": "20240115_143022_a1b2c3d4",
  "gateway": "equity",
  "filename": "equity_equity_january.xlsx"
}
```

**Step 4: Upload internal file (Workpay records)**

```bash
POST /api/v1/upload/file?batch_id=20240115_143022_a1b2c3d4&gateway_name=workpay_equity
Authorization: Bearer <user_token>
Content-Type: multipart/form-data

file: @workpay_january.xlsx
```

**Step 5: Ready for reconciliation**

```bash
POST /api/v1/reconcile/save?batch_id=20240115_143022_a1b2c3d4&external_gateway=equity
Authorization: Bearer <user_token>
```

### Example 2: Bulk Upload with Validation Skip

```bash
POST /api/v1/upload/files?batch_id=20240115_143022_a1b2c3d4&gateway_name=equity&skip_validation=true
Authorization: Bearer <user_token>
Content-Type: multipart/form-data

files: @jan_statement.xlsx
files: @feb_statement.xlsx
files: @mar_statement.xlsx
```

### Example 3: Pre-Upload Validation

```bash
POST /api/v1/upload/validate
Authorization: Bearer <user_token>
Content-Type: multipart/form-data

file: @my_file.xlsx
```

Response (invalid file):
```json
{
  "valid": false,
  "missing_columns": ["Reference"],
  "message": "Missing columns: Reference"
}
```

---

## File Locations Summary

### Backend

| File | Purpose |
|------|---------|
| `app/controller/upload.py` | Upload API endpoints |
| `app/controller/batch_creation.py` | Batch management API endpoints |
| `app/upload/upload_files.py` | FileUpload service class |
| `app/upload/batch_creation.py` | BatchCreation service class |
| `app/upload/template_generator.py` | TemplateGenerator class |
| `app/sqlModels/batchEntities.py` | Batch and BatchFile models |
| `app/storage/base.py` | StorageBackend interface |
| `app/storage/local_storage.py` | LocalStorage implementation |
| `app/storage/gcs_storage.py` | GcsStorage implementation |
| `app/storage/config.py` | Storage configuration |

### Frontend

| File | Purpose |
|------|---------|
| `frontend/src/features/upload/UploadPage.tsx` | Upload user interface |
| `frontend/src/api/upload.ts` | Upload API service |
| `frontend/src/api/batches.ts` | Batch API service |
| `frontend/src/types/index.ts` | TypeScript type definitions |
