# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Payment Gateway Reconciliation System built with FastAPI. Reconciles financial transactions between external bank statements (Equity, KCB, M-Pesa) and internal Workpay records by matching Transaction IDs.

## Running the Application

**Local development:**
```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Docker (recommended):**
```bash
docker-compose up --build
```
- FastAPI: `http://localhost:8000`
- MySQL: `localhost:3307`

**Environment variables:**
- `DATABASE_URL_DOCKER`: MySQL connection string for Docker
- `DATABASE_URL_LOCAL`: MySQL connection string for local development
- `STORAGE_BACKEND`: `local` (default) or `gcs`
- `LOCAL_UPLOADS_PATH`: Path for local file storage (default: `uploads`)
- `GCS_BUCKET`: GCS bucket name when using cloud storage

## Architecture

### Layered Design
```
Controller Layer (app/controller/)
    ↓
Gateway Config (app/config/gateways.py)
    ↓
Business Logic (Reconciler.py)
    ↓
Data Processing (GatewayFile)
    ↓
Data Loading (DataLoader + StorageBackend)
    ↓
Persistence (MySQL: Transaction, Batch tables)
```

### Key Components

- **`app/config/gateways.py`**: Centralized gateway configuration. Database (`gateway_configs` table) is the single source of truth.

- **`app/reconciler/Reconciler.py`**: Core orchestrator. Loads files via `GatewayFile`, matches transactions by `Reference` column, persists results to unified `transactions` table.

- **`app/dataProcessing/GatewayFileClass.py`**: Contains `GatewayFile` class for unified file processing. Handles file normalization, column validation, float-to-string Reference conversion, and credit/debit extraction.

- **`app/dataLoading/data_loader.py`**: `DataLoader` class reads files using pluggable `StorageBackend`. Supports xlsx, xls, and csv.

- **`app/storage/`**: Pluggable storage layer with `LocalStorage` and `GcsStorage` backends.

- **`app/sqlModels/transactionEntities.py`**: Single `Transaction` table with `gateway` and `transaction_type` discriminators.

- **`app/reports/download_report.py`**: Generates Excel reports with detailed reconciliation summaries.

### Data Flow

1. Create batch via `POST /api/v1/batch` → stored in MySQL `batches` table + storage directory created
2. Upload files to gateway subdirectories:
   - External: `gateway_name=equity` → saves as `{batch_id}/equity/equity.xlsx`
   - Internal: `gateway_name=workpay_equity` → saves as `{batch_id}/equity/workpay_equity.xlsx`
   - Max 2 files per gateway subdirectory (one external, one internal)
3. Get available gateways via `GET /api/v1/reconcile/available-gateways/{batch_id}`
4. Reconcile via `POST /api/v1/reconcile?batch_id=X&gateway=equity`
   - Validates files exist (both external and internal required)
   - Fills null values with defaults
   - Generates reconciliation keys
   - Matches transactions and saves to database
5. Download report via `GET /api/v1/reports/download/equity?batch_id=X`
6. Close batch via `POST /api/v1/batch/{batch_id}/close` (only when all transactions reconciled)

### Role-Based Access Control (Maker-Checker Pattern)

The system implements a strict maker-checker workflow with three roles:

| Role | Description | Capabilities |
|------|-------------|--------------|
| `user` | Inputter/Maker | Create batches, upload files, run reconciliation, initiate manual reconciliation, submit gateway change requests, request batch deletions |
| `admin` | Approver/Checker | Approve/reject manual reconciliations, approve/reject gateway change requests, approve/reject batch delete requests |
| `super_admin` | System Administrator | Manage user accounts (create, update, deactivate). No access to operational approvals |

**Key Principle**: The same person cannot both initiate and approve an action. Users (makers) initiate, admins (checkers) approve.

**Maker-Checker Workflows**:
1. **Manual Reconciliation**: User marks transaction as manually reconciled → Admin approves/rejects
2. **Gateway Configuration**: User submits change request → Admin approves/rejects
3. **Batch Deletion**: User requests deletion → Admin approves/rejects

**Backend Dependencies** (in `app/auth/dependencies.py`):
- `require_user_role`: Only users (makers) - for initiating actions
- `require_admin_only`: Only admins (checkers) - for approving actions
- `require_super_admin`: Only super admins - for user management
- `require_active_user`: Any authenticated user - for read operations

### Matching Logic

- Match on composite reconciliation key: `{reference}|{amount}|{base_gateway}`
- **Reference**: Cleaned string (no decimals, e.g., `123456.0` → `123456`)
- **Amount**: Absolute whole number (no cents)
- **Base Gateway**: Same for external and internal (e.g., `equity` for both)
- Credits: `Credit > 0` (auto-reconciled)
- Debits: `Debit > 0` (matched against internal records)
- Charges: Debits with keywords in Reference OR Details column (configurable per gateway, auto-reconciled)

**Gateway Naming**: Transactions are stored with `{gateway}_external` or `{gateway}_internal` suffix to identify source.

**Null Handling**: Before reconciliation, null values are filled:
- Date → current date
- Reference/Details → "NA"
- Debit/Credit → 0

See [docs/reconciliation.md](docs/reconciliation.md) for detailed reconciliation logic.

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/batch` | Create new batch (enforces one pending per user) |
| GET | `/api/v1/batch/{batch_id}` | Get batch details |
| GET | `/api/v1/batch` | List all batches (paginated, filterable) |
| POST | `/api/v1/batch/{batch_id}/close` | Close batch (creator only, all txns must be reconciled) |
| POST | `/api/v1/batch/{batch_id}/delete-request` | Request batch deletion (maker-checker) |
| GET | `/api/v1/batch/delete-requests/list` | List batch delete requests |
| POST | `/api/v1/batch/delete-requests/{id}/review` | Admin approve/reject delete request |
| GET | `/api/v1/batch/{batch_id}/files` | List files in a batch |
| GET | `/api/v1/upload/pending-batches` | Get user's pending batches for upload dropdown |
| POST | `/api/v1/upload/file` | Upload file to gateway subdirectory |
| DELETE | `/api/v1/upload/file` | Delete an uploaded file |
| GET | `/api/v1/upload/file/download` | Download an uploaded file |
| GET | `/api/v1/upload/files` | List files for a batch |
| POST | `/api/v1/upload/validate` | Validate file columns without uploading |
| GET | `/api/v1/upload/template` | Download unified template (xlsx or csv, current date as sample) |
| GET | `/api/v1/upload/template-info` | Get template column info for download popup |
| GET | `/api/v1/gateways` | List supported gateways, upload names, and charge keywords |
| GET | `/api/v1/reconcile/available-gateways/{batch_id}` | Get gateways with uploaded files for a batch |
| POST | `/api/v1/reconcile` | Run reconciliation and save to DB (single step) |
| GET | `/api/v1/reports/closed-batches` | Get closed batches for reports (latest 5 + search) |
| GET | `/api/v1/reports/available-gateways` | Get gateways with transactions for a batch |
| GET | `/api/v1/reports/download/batch` | Download report for batch+gateway (xlsx/csv) |
| GET | `/api/v1/reports/download/{gateway}` | Legacy: Gateway-specific Excel report |
| GET | `/api/v1/reports/download` | Legacy: Full Excel report |

**Upload Workflow:**
1. Get pending batches: `GET /api/v1/upload/pending-batches` (returns user's pending batches)
2. View template info: `GET /api/v1/upload/template-info` (column formats for popup)
3. Download template: `GET /api/v1/upload/template?format=xlsx` (current date as sample)
4. Fill template with your data (external bank statement or internal Workpay records)
5. Upload file: `POST /api/v1/upload/file?batch_id=X&gateway_name=equity`
   - File is renamed to `{gateway_name}.{ext}` and stored in `{batch_id}/{external_gateway}/`
   - Max 2 files per gateway (one external, one internal)
6. Delete file: `DELETE /api/v1/upload/file?batch_id=X&filename=equity.xlsx&gateway=equity`
7. Download file: `GET /api/v1/upload/file/download?batch_id=X&filename=equity.xlsx&gateway=equity`

Files must have columns: `Date`, `Reference`, `Details`, `Debit`, `Credit`

**Gateway Configuration API** (`/api/v1/gateway-config`):

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | List all gateway configurations |
| POST | `/` | Create a new gateway (via change request for maker-checker approval) |
| GET | `/info` | Get comprehensive gateway info for reconciliation |
| GET | `/{gateway_name}` | Get specific gateway config |
| PUT | `/{gateway_name}` | Update gateway config (via change request) |
| DELETE | `/{gateway_name}` | Deactivate or delete gateway (via change request) |
| POST | `/{gateway_name}/activate` | Reactivate a deactivated gateway (via change request) |
| POST | `/seed-defaults` | Seed default gateways to database |
| GET | `/upload-names/{gateway_name}` | Get upload gateway names for an external gateway |

## Adding a New Payment Gateway

### Via API (Recommended)

```bash
# Create new external gateway
curl -X POST /api/v1/gateway-config/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "coop",
    "gateway_type": "external",
    "display_name": "Co-operative Bank",
    "charge_keywords": ["CHARGE", "FEE", "COMMISSION", "LEDGER FEE"]
  }'
```

Note: Gateway changes require admin approval (maker-checker workflow).

### Via Config File (Fallback)

Edit `app/config/gateways.py` `DEFAULT_GATEWAYS` dict:

```python
DEFAULT_GATEWAYS = {
    # Existing gateways...
    "coop": {
        "type": "external",
        "display_name": "Co-operative Bank",
        "charge_keywords": ["CHARGE", "FEE", "COMMISSION"],
    },
}
```

Then seed to database: `POST /api/v1/gateway-config/seed-defaults`

### After Adding

- Upload external file: `gateway_name=coop`
- Upload internal file: `gateway_name=workpay_coop`
- Reconcile: `external_gateway=coop`
- Download report: `gateway=coop`

## File Upload Convention

Files are stored in gateway subdirectories within each batch:

```
uploads/{batch_id}/{external_gateway}/{gateway_name}.{ext}
```

| File Type | Gateway Name | Stored Path |
|-----------|--------------|-------------|
| Equity statement | `equity` | `{batch_id}/equity/equity.xlsx` |
| KCB statement | `kcb` | `{batch_id}/kcb/kcb.xlsx` |
| M-Pesa statement | `mpesa` | `{batch_id}/mpesa/mpesa.csv` |
| Workpay for Equity | `workpay_equity` | `{batch_id}/equity/workpay_equity.xlsx` |
| Workpay for KCB | `workpay_kcb` | `{batch_id}/kcb/workpay_kcb.xlsx` |
| Workpay for M-Pesa | `workpay_mpesa` | `{batch_id}/mpesa/workpay_mpesa.csv` |

Each gateway subdirectory contains at most 2 files (one external + one internal). Files are automatically renamed on upload. Internal files use combined gateway names (`workpay_{external_gateway}`) and are stored in the corresponding external gateway's subdirectory.

## Database Schema

Main tables:
- `batches`: Reconciliation batches (id, batch_id, status [pending/completed], description, created_by_id, created_at, closed_at)
- `batch_files`: Tracks uploaded files (id, batch_id, filename, original_filename, gateway, file_size, uploaded_by_id, uploaded_at)
- `batch_delete_requests`: Maker-checker delete workflow (id, batch_id, status [pending/approved/rejected], reason, requested_by_id, reviewed_by_id, reviewed_at, rejection_reason, created_at)
- `transactions`: Unified table with `gateway` and `transaction_type` discriminators, includes:
  - `reconciliation_key`: Generated match key for auditing (`{reference}|{amount}|{base_gateway}`)
  - `source_file`: Source filename for tracking
  - `is_manually_reconciled`: Flag for manual reconciliation
  - `authorization_status`: For maker-checker on manual reconciliations
- `gateway_configs`: Dynamic gateway configurations (name, gateway_type, display_name, charge_keywords, is_active)
- `users`: User accounts with roles (super_admin, admin, user)
- `audit_logs`: Audit trail for sensitive operations

## Database Migrations (Alembic)

This project uses Alembic for database migrations.

**Run pending migrations:**
```bash
alembic upgrade head
```

**Create a new migration (auto-generate from model changes):**
```bash
alembic revision --autogenerate -m "description of changes"
```

**Create an empty migration:**
```bash
alembic revision -m "description of changes"
```

**View migration history:**
```bash
alembic history
```

**Downgrade one revision:**
```bash
alembic downgrade -1
```

**View current revision:**
```bash
alembic current
```

Migration files are in `alembic/versions/`. Always review auto-generated migrations before applying.

## Template Columns (Unified)

**Single unified template** (used for both external and internal records):
- Date (YYYY-DD-MM format, mandatory)
- Reference (unique transaction identifier, mandatory)
- Details (transaction narration/description, mandatory)
- Debit (debit amount, number, optional - can be empty)
- Credit (credit amount, number, optional - can be empty)

The same template is used for all uploads. Gateway distinction is made by the filename during upload.

**Template download popup** shows expected formats and mandatory columns before download. The template file includes a sample row with the current date in YYYY-DD-MM format as guidance.

**Column mapping to database:**
- `Date` → `transactions.date` (datetime)
- `Reference` → `transactions.transaction_id` (varchar)
- `Details` → `transactions.narrative` (varchar)
- `Debit` → `transactions.debit` (decimal)
- `Credit` → `transactions.credit` (decimal)

## Report Summary Structure

The reconciliation report includes a detailed summary sheet:

```
BATCH INFORMATION
├── External Gateway, Internal Gateway, Batch ID

EXTERNAL RECORDS (BANK STATEMENT)
├── Total/Reconciled/Unreconciled Debits Count
├── Total Credits Count, Total Charges Count

EXTERNAL AMOUNTS
├── Total/Reconciled/Unreconciled Debits Amount
├── Total Credits Amount, Total Charges Amount

INTERNAL RECORDS (WORKPAY)
├── Total/Reconciled/Unreconciled Count

INTERNAL AMOUNTS
├── Total/Reconciled/Unreconciled Amount

RECONCILIATION VARIANCE
├── Count and Amount differences between external and internal
```

## Key Implementation Details

- **Reference Handling**: Automatically converts float Reference values (e.g., `123456.0` from Excel) to clean strings (`"123456"`) to ensure proper matching.

- **Column Normalization**: Case-insensitive column matching (e.g., "date" matches "Date", "reference" matches "Reference").

- **Credit/Debit Extraction**: Credits are transactions where `Credit > 0`. Debits are transactions where `Debit > 0`.

- **Reconciliation Key**: Generated composite key `{reference}|{amount}|{base_gateway}` stored in `reconciliation_key` column for auditing and debugging.

- **Source File Tracking**: Each transaction stores its source filename in `source_file` column.

- **Gateway Identifiers**: Transactions use `{gateway}_external` or `{gateway}_internal` naming to identify source type.

- **Null Value Handling**: Before reconciliation, null/empty values are filled with defaults (Date→current date, Reference/Details→"NA", Debit/Credit→0).

- **Duplicate Prevention**: Reconciliation checks for existing records before saving to prevent running twice on the same batch+gateway.

- **Batch Lifecycle**: Batches have two statuses: `pending` (open for uploads/reconciliation) and `completed` (closed). A user can only have one pending batch at a time. Only the batch creator can close it, and only when all transactions are reconciled. Deletion goes through maker-checker approval (user initiates, admin approves).

- **Configurable Gateways**: Gateway configurations are stored in the database (`gateway_configs` table) as the single source of truth. Use the Gateway Configuration API to add/update gateways. All gateway changes go through maker-checker approval workflow.

## Reports

Reports can only be downloaded for **closed/completed batches**. Both a batch and gateway must be selected to download a report.

### Report Download Workflow

1. **Select Batch**: Choose from the latest 5 closed batches, or search by batch ID
2. **Select Gateway**: Choose from gateways that have transactions in the selected batch
3. **Select Format**: Choose between XLSX (Excel) or CSV
4. **Download**: Click download to generate and download the report

### Report Columns

| Column | Description |
|--------|-------------|
| Date | Transaction date (YYYY-MM-DD format) |
| Transaction Reference | Unique transaction identifier |
| Details | Transaction narration/description |
| Debit | Debit amount |
| Credit | Credit amount |
| Reconciliation Status | `reconciled` or `unreconciled` |
| Reconciliation Key | Composite key used for matching (`{reference}\|{amount}\|{gateway}`) |
| Batch ID | Batch identifier |

### Report API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/reports/closed-batches` | Get closed batches (latest 5 by default, supports search) |
| GET | `/api/v1/reports/available-gateways?batch_id=X` | Get gateways with transactions for a batch |
| GET | `/api/v1/reports/download/batch?batch_id=X&gateway=Y&format=xlsx` | Download report |

**Query Parameters for `/reports/closed-batches`:**
- `search`: Optional batch ID search term (partial match)
- `limit`: Maximum batches to return (default: 5, max: 50)

**Query Parameters for `/reports/download/batch`:**
- `batch_id`: Required. Must be a closed batch.
- `gateway`: Required. Base gateway name (e.g., `equity`, `kcb`, `mpesa`).
- `format`: Optional. `xlsx` (default) or `csv`.

### Example Usage

```bash
# Get latest 5 closed batches
curl /api/v1/reports/closed-batches

# Search for a specific batch
curl "/api/v1/reports/closed-batches?search=BATCH-2024"

# Get available gateways for a batch
curl "/api/v1/reports/available-gateways?batch_id=BATCH-20240126-001"

# Download XLSX report
curl -o report.xlsx "/api/v1/reports/download/batch?batch_id=BATCH-20240126-001&gateway=equity&format=xlsx"

# Download CSV report
curl -o report.csv "/api/v1/reports/download/batch?batch_id=BATCH-20240126-001&gateway=equity&format=csv"
```
