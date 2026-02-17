# Backend Documentation

FastAPI backend for the Payment Gateway Reconciliation System.

## Table of Contents

1. [Architecture](#architecture)
2. [Directory Structure](#directory-structure)
3. [Application Entry Point](#application-entry-point)
4. [Authentication & Security](#authentication--security)
5. [Database Models](#database-models)
6. [API Controllers](#api-controllers)
7. [Reconciliation Engine](#reconciliation-engine)
8. [Data Processing Pipeline](#data-processing-pipeline)
9. [Storage Backends](#storage-backends)
10. [File Upload Service](#file-upload-service)
11. [Reports](#reports)
12. [Email Service](#email-service)
13. [Middleware](#middleware)
14. [Logging](#logging)
15. [Exception Handling](#exception-handling)
16. [Configuration](#configuration)
17. [Database Migrations](#database-migrations)
18. [Environment Variables](#environment-variables)

---

## Architecture

The backend follows a strict layered architecture:

```
HTTP Request
     │
     ▼
Middleware Stack
  ├── Security Headers (HSTS, CSP, X-Frame-Options)
  ├── Rate Limiting (SlowAPI)
  ├── CORS
  ├── Audit Logging
  ├── Request Logging (correlation ID)
     │
     ▼
Controller Layer  (app/controller/)
  ├── Input validation (Pydantic)
  ├── Auth dependency injection
  └── Route handlers
     │
     ▼
Business Logic
  ├── Reconciler (app/reconciler/)
  ├── File Upload (app/upload/)
  └── Report Generation (app/reports/)
     │
     ▼
Data Access
  ├── SQLAlchemy ORM (app/sqlModels/)
  ├── Data Loading (app/dataLoading/)
  └── Storage Backends (app/storage/)
     │
     ▼
Infrastructure
  ├── MySQL Database
  ├── File Storage (Local / GCS)
  └── SMTP Email
```

---

## Directory Structure

```
backend/
├── app/
│   ├── main.py                     # FastAPI app + middleware + routers
│   ├── auth/
│   │   ├── __init__.py             # Public exports
│   │   ├── config.py               # AuthSettings (JWT, SMTP, password policy)
│   │   ├── dependencies.py         # FastAPI auth dependency injectors
│   │   └── security.py             # JWT, password hashing, session tokens
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py             # App settings from environment
│   │   └── gateways.py             # Gateway configuration helpers
│   ├── controller/
│   │   ├── auth.py                 # Auth endpoints (login, logout, password)
│   │   ├── batch_creation.py       # Bulk user creation from CSV
│   │   ├── dashboard.py            # Dashboard statistics
│   │   ├── gateway_config.py       # Gateway CRUD + change request workflow
│   │   ├── operations.py           # Manual reconciliation + authorization
│   │   ├── reconcile.py            # Reconciliation execution
│   │   ├── reports.py              # Report download endpoints
│   │   ├── runs.py                 # Reconciliation run listing
│   │   ├── transactions.py         # Transaction browsing + filtering
│   │   ├── upload.py               # File upload/download/delete
│   │   └── users.py                # User management (super_admin only)
│   ├── customLogging/
│   │   ├── __init__.py
│   │   ├── config.py               # Logging setup, formatters, filters
│   │   ├── logger.py               # get_logger(), log_operation() helpers
│   │   └── RequestLogger.py        # HTTP request/response logging middleware
│   ├── database/
│   │   └── mysql_configs.py        # SQLAlchemy engine, session, Base
│   ├── dataLoading/
│   │   └── data_loader.py          # DataLoader: reads xlsx, xls, csv from storage
│   ├── dataProcessing/
│   │   ├── GatewayFileClass.py     # GatewayFile: normalizes uploaded files
│   │   └── file_transformer.py     # FileTransformer: maps raw files to template
│   ├── exceptions/
│   │   ├── exceptions.py           # Custom exception hierarchy
│   │   └── handlers.py             # Global FastAPI exception handlers
│   ├── middleware/
│   │   ├── audit.py                # Audit log middleware
│   │   └── security.py             # Security headers + rate limiter
│   ├── pydanticModels/
│   │   ├── authModels.py           # Auth request/response schemas
│   │   ├── gatewayModels.py        # Gateway request/response schemas
│   │   ├── runModels.py            # Run schemas
│   │   └── transactionModels.py    # Transaction schemas
│   ├── reconciler/
│   │   └── Reconciler.py           # Core reconciliation orchestrator
│   ├── reports/
│   │   ├── download_report.py      # Report query + streaming response
│   │   └── output_writer.py        # Excel formatting with openpyxl
│   ├── services/
│   │   └── email_service.py        # Async email via aiosmtplib + Jinja2
│   ├── sqlModels/
│   │   ├── authEntities.py         # User, RefreshToken, LoginSession, AuditLog
│   │   ├── gatewayEntities.py      # Gateway, GatewayFileConfig, GatewayChangeRequest
│   │   ├── runEntities.py          # ReconciliationRun, UploadedFile
│   │   └── transactionEntities.py  # Transaction (unified table)
│   ├── storage/
│   │   ├── base.py                 # StorageBackend ABC
│   │   ├── config.py               # get_storage() factory
│   │   ├── gcs_storage.py          # Google Cloud Storage backend
│   │   └── local_storage.py        # Local filesystem backend
│   ├── templates/email/
│   │   ├── account_locked.html
│   │   ├── forgot_password.html
│   │   ├── password_changed.html
│   │   └── welcome_user.html
│   └── upload/
│       ├── batch_creation.py       # Batch user creation logic
│       ├── template_generator.py   # Excel/CSV template generation
│       └── upload_files.py         # FileUpload class
├── alembic/
│   └── versions/                   # Migration scripts
├── alembic.ini
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Application Entry Point

**`app/main.py`**

Creates the FastAPI application, mounts all middleware, registers all routers, and defines the lifespan context manager for startup/shutdown.

**Middleware order** (outermost → innermost):
1. `CorrelationIdMiddleware` — attaches unique request ID to each request
2. `RequestLoggingMiddleware` — logs all HTTP requests/responses with timing
3. `AuditLogMiddleware` — writes POST/PUT/PATCH/DELETE to audit_logs table
4. `CORSMiddleware` — allows requests from configured origins
5. `SecurityHeadersMiddleware` — adds HSTS, CSP, X-Frame-Options, etc.

**Registered routers** (all under `/api/v1`):
- `/auth` — Authentication
- `/users` — User management
- `/gateway-config` — Gateway configuration
- `/upload` — File upload
- `/reconcile` — Reconciliation
- `/operations` — Manual reconciliation
- `/reports` — Report downloads
- `/runs` — Run history
- `/transactions` — Transaction browsing
- `/dashboard` — Dashboard stats

**Health check**: `GET /health` — returns `{"status": "ok"}` with no auth requirement.

---

## Authentication & Security

### `app/auth/config.py` — AuthSettings

Settings loaded from environment variables at startup. Missing variables cause startup failure.

| Setting | Default | Description |
|---------|---------|-------------|
| `JWT_SECRET_KEY` | required | HMAC-SHA256 signing key |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `MAX_LOGIN_ATTEMPTS` | `5` | Lockout threshold |
| `LOCKOUT_DURATION_MINUTES` | `15` | Lockout duration |
| `PASSWORD_EXPIRY_DAYS` | `90` | Password expiry |
| `PASSWORD_HISTORY_COUNT` | `5` | Remembered passwords |
| `REQUIRE_UPPERCASE` | `true` | Password complexity |
| `REQUIRE_LOWERCASE` | `true` | Password complexity |
| `REQUIRE_DIGITS` | `true` | Password complexity |
| `REQUIRE_SPECIAL_CHARS` | `true` | Password complexity |
| `MIN_PASSWORD_LENGTH` | `8` | Minimum length |

### `app/auth/security.py` — Security Primitives

- `hash_password(password)` — bcrypt hashing
- `verify_password(plain, hashed)` — bcrypt verification
- `create_access_token(data, expires_delta)` — JWT creation
- `verify_access_token(token)` — JWT verification, returns payload
- `generate_session_token()` — UUID4-based session identifier
- `generate_reset_token()` — URL-safe reset token

### `app/auth/dependencies.py` — FastAPI Dependencies

Inject into route handlers via `Depends(...)`:

| Dependency | Description |
|-----------|-------------|
| `get_current_user` | Extracts user from JWT; validates active login session |
| `require_active_user` | Extends `get_current_user`; checks account active and password not expired |
| `require_user_role` | Allows only `role=user` (makers) |
| `require_admin_only` | Allows only `role=admin` (checkers; excludes super_admin) |
| `require_admin` | Allows `admin` or `super_admin` |
| `require_super_admin` | Allows only `role=super_admin` |

### Login Flow

1. `POST /api/v1/auth/login` with `{email, password}`
2. Validate credentials; check lockout status
3. Invalidate any existing login session (concurrent session prevention)
4. Create `LoginSession` record with session token
5. Return JWT access token + refresh token

### Token Refresh

`POST /api/v1/auth/refresh` — validates refresh token, issues new access token without requiring password re-entry.

### Forgot Password

1. `POST /api/v1/auth/forgot-password` — generates reset token, stores hashed in DB, emails link
2. `POST /api/v1/auth/reset-password` — validates token (10-minute expiry), sets new password

---

## Database Models

### `app/sqlModels/authEntities.py`

**`User`** — All user accounts.
- Fields: `id`, `username`, `email`, `hashed_password`, `role`, `status`, `first_name`, `last_name`, `mobile`
- Security: `failed_login_attempts`, `locked_until`, `password_changed_at`, `must_change_password`
- Relationships: `login_sessions`, `refresh_tokens`, `audit_logs`
- Roles: `super_admin`, `admin`, `user`
- Status: `active`, `blocked`, `deactivated`

**`RefreshToken`** — Stored refresh tokens for token rotation.

**`LoginSession`** — One active session per user (single concurrent session enforcement).
- `session_token` — UUID4 identifier stored in JWT payload

**`AuditLog`** — Immutable audit trail for sensitive operations.
- Records: method, path, user, IP, status code, timestamp

### `app/sqlModels/transactionEntities.py`

**`Transaction`** — Unified table for all transactions from all gateways.

| Column | Description |
|--------|-------------|
| `gateway` | Full gateway name (e.g., `equity_external`, `workpay_equity`) |
| `transaction_id` | Cleaned reference string |
| `narrative` | Transaction description |
| `debit` | Debit amount (Decimal) |
| `credit` | Credit amount (Decimal) |
| `date` | Transaction date |
| `transaction_type` | `deposit`, `debit`, `charge`, `payout`, `refund` |
| `reconciliation_status` | `reconciled` or `unreconciled` |
| `reconciliation_category` | `reconcilable`, `auto_reconciled`, `non_reconcilable` |
| `reconciliation_key` | Composite matching key |
| `reconciliation_note` | System-generated note |
| `run_id` | Associated reconciliation run |
| `source_file` | Original filename |
| `authorization_status` | `pending`, `authorized`, `rejected` (manual recons) |
| `is_manual` | Boolean, whether manually reconciled |
| `manual_recon_note` | User-provided note for manual reconciliations |

**Unique constraint**: `(reconciliation_key, gateway)` — prevents cross-run duplicates.

**Transaction types by gateway side**:

| Gateway | Type | Category |
|---------|------|----------|
| `{gw}_external` | `deposit` (credit > 0) | `auto_reconciled` |
| `{gw}_external` | `charge` (debit, keyword match) | `auto_reconciled` |
| `{gw}_external` | `debit` (debit, no keyword) | `reconcilable` |
| `{gw}_internal` | `payout` (debit) | `reconcilable` |
| `{gw}_internal` | `refund` (credit) | `auto_reconciled` |

### `app/sqlModels/gatewayEntities.py`

**`Gateway`** — Logical gateway (e.g., Equity, KCB, M-Pesa).
- Has external and internal `GatewayFileConfig` children
- `is_active` — controls visibility

**`GatewayFileConfig`** — Per-file configuration for each gateway side.
- `config_type`: `external` or `internal`
- `column_mapping`: JSON dict mapping raw file columns → template columns
- `charge_keywords`: JSON array of strings used to identify charge transactions
- `header_row_index`: Which row contains column headers (0-based)
- `date_format`: strftime format for date parsing

**`GatewayChangeRequest`** — Maker-checker change log.
- `request_type`: `create`, `update`, `delete`, `activate`, `permanent_delete`
- `status`: `pending`, `approved`, `rejected`
- `proposed_config`: Full proposed state as JSON
- Linked to submitting user and reviewing admin

### `app/sqlModels/runEntities.py`

**`ReconciliationRun`** — One record per reconciliation execution.
- `run_id`: Format `RUN-YYYYMMDD-HHMMSS-{uuid8}`
- Counts: `total_external`, `total_internal`, `matched`, `unmatched_external`, `unmatched_internal`, `carry_forward_matched`

**`UploadedFile`** — Tracks files currently in storage.

---

## API Controllers

### Auth (`/api/v1/auth`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/login` | None | Login; returns access + refresh tokens |
| POST | `/logout` | User | Invalidate session |
| POST | `/refresh` | None | Refresh access token |
| GET | `/me` | User | Get current user profile |
| POST | `/change-password` | User | Change own password |
| POST | `/forgot-password` | None | Request password reset email |
| POST | `/reset-password` | None | Set new password via reset token |

### Users (`/api/v1/users`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | SuperAdmin | List all users with pagination |
| POST | `/` | SuperAdmin | Create user; auto-generates password; sends welcome email |
| GET | `/{id}` | SuperAdmin | Get user details |
| PATCH | `/{id}` | SuperAdmin | Update user (role, name, etc.) |
| POST | `/{id}/block` | SuperAdmin | Block user account |
| POST | `/{id}/unblock` | SuperAdmin | Unblock user account |
| POST | `/{id}/deactivate` | SuperAdmin | Permanently deactivate user |
| POST | `/{id}/reset-password` | SuperAdmin | Generate new temp password; email user |
| POST | `/create-super-admin` | None* | Bootstrap first super admin (requires secret key) |
| POST | `/batch` | SuperAdmin | Upload CSV to create multiple users at once |

### Gateway Config (`/api/v1/gateway-config`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | User | List all gateways |
| GET | `/{id}` | User | Get single gateway |
| POST | `/change-request` | User | Submit a change request |
| GET | `/change-requests/my` | User | Get own submitted requests |
| GET | `/change-requests/pending` | Admin | List pending requests for approval |
| GET | `/change-requests/all` | Admin | List all requests with status filter |
| GET | `/change-requests/{id}` | User | Get single request |
| POST | `/change-requests/{id}/review` | Admin | Approve or reject a request |
| DELETE | `/{id}` | Admin | Permanently delete deactivated gateway |

### Upload (`/api/v1/upload`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/file` | User | Upload transaction file (template or raw transform) |
| DELETE | `/file` | User | Delete uploaded file |
| GET | `/file/download` | User | Download an uploaded file |
| GET | `/files` | User | List files for a gateway |
| GET | `/template` | User | Download the upload template |
| GET | `/template-info` | User | Get template column definitions |
| POST | `/validate` | User | Validate file columns without saving |

### Reconciliation (`/api/v1/reconcile`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/available-gateways` | User | List gateways with both files uploaded |
| POST | `/preview` | User | Dry-run reconciliation with carry-forward |
| POST | `/` | User | Execute and save reconciliation |

### Operations (`/api/v1/operations`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/unreconciled` | User | Get unreconciled transactions grouped by gateway |
| POST | `/manual-reconcile/{id}` | User | Manually reconcile a single transaction |
| POST | `/manual-reconcile-bulk` | User | Bulk manual reconciliation |
| GET | `/pending-authorization` | Admin | Get transactions pending admin approval |
| POST | `/authorize/{id}` | Admin | Authorize or reject a manual reconciliation |
| POST | `/authorize-bulk` | Admin | Bulk authorization |

### Reports (`/api/v1/reports`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/available-gateways` | User | Gateways with transactions |
| GET | `/runs` | User | Reconciliation runs for report drill-down |
| GET | `/download` | User | Download report as XLSX or CSV |

**XLSX report sheets** (always present, empty if no data):
1. **Unreconciled External** — Unmatched bank debits
2. **Unreconciled Internal** — Unmatched Workpay payouts
3. **Reconciled External** — Matched bank debits
4. **Reconciled Internal** — Matched Workpay payouts
5. **Charges** — Auto-reconciled bank charges
6. **Deposits** — Auto-reconciled credit/deposit transactions

### Runs (`/api/v1/runs`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | User | List runs with pagination; filter by gateway, date range |
| GET | `/{run_id}` | User | Get single run with transaction counts |

### Transactions (`/api/v1/transactions`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | User | Paginated list with search + multi-field filters |
| GET | `/filters` | User | Available filter values (gateways, types, statuses) |
| GET | `/{id}` | User | Get single transaction |

### Dashboard (`/api/v1/dashboard`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/stats` | User | Summary + per-gateway tile statistics |

---

## Reconciliation Engine

**`app/reconciler/Reconciler.py`** — The core business logic. The `Reconciler` class orchestrates the entire reconciliation process for a single gateway.

### Key Constants

```python
DATE_COLUMN = "Date"
REFERENCE_COLUMN = "Reference"
DETAILS_COLUMN = "Details"
DEBIT_COLUMN = "Debit"
CREDIT_COLUMN = "Credit"
RECONCILIATION_KEY_COLUMN = "reconciliation_key"
```

### Reconciliation Key Format

For reconcilable transactions (debits and payouts that must be matched):
```
{reference}|{amount}|{base_gateway}
```

For auto-reconciled transactions (charges and deposits — include date to prevent cross-run collision of identical-reference entries):
```
{reference}|{amount}|{base_gateway}|{YYYYMMDD}
```

Where:
- `reference` — cleaned string, float decimals stripped (e.g., `123456.0` → `123456`)
- `amount` — absolute whole number (no cents)
- `base_gateway` — gateway prefix without `_external`/`_internal` suffix

### Transaction Classification

```
External file rows:
  credit > 0                       → DEPOSIT   (auto_reconciled, RECONCILED)
  debit > 0 AND keyword in Details → CHARGE    (auto_reconciled, RECONCILED)
  debit > 0 AND no keyword         → DEBIT     (reconcilable, UNRECONCILED)

Internal file rows:
  debit > 0                        → PAYOUT    (reconcilable, UNRECONCILED)
  credit > 0                       → REFUND    (auto_reconciled, RECONCILED)
```

### Matching Algorithm

1. Build a set of internal payout reconciliation keys from the current run
2. For each external debit:
   - If key exists in internal keys → mark both RECONCILED, add to matched list
   - If key not found → mark UNRECONCILED (carry forward to next run)
3. Any internal payouts not matched by an external debit → UNRECONCILED

### Carry-Forward

On each reconciliation run, previously unreconciled transactions are loaded from the database alongside the new file transactions. They participate in the matching step, allowing new statements to match against old records. This ensures nothing is permanently lost from previous runs.

### Duplicate Key Handling

**Within-batch** (`_deduplicate_keys`): When the same file contains rows that produce identical keys (e.g., multiple "Transaction Charge" rows of KES 15 on the same date), counter suffixes are appended: `|1`, `|2`, etc.

**Cross-run**: The `UNIQUE(reconciliation_key, gateway)` constraint causes `IntegrityError` for already-saved keys, which are caught silently per row — the row is skipped as already processed.

---

## Data Processing Pipeline

### Template Upload Flow

1. File validated (extension, columns)
2. Archive copy saved: `uploads/{gateway}/archive/{name}_{timestamp}_{uuid8}.{ext}`
3. Normalized file saved: `uploads/{gateway}/{gateway_name}.{ext}`
4. Database record created in `uploaded_files` table

### Transform Upload Flow (Raw Statements)

1. File validated
2. Raw file archived: `uploads/{gateway}/archive/{name}_raw_{timestamp}_{uuid8}.{ext}`
3. Raw file saved: `uploads/{gateway}/{gateway_name}_raw.{ext}`
4. `FileTransformer` applies `column_mapping` from `GatewayFileConfig`
5. Normalized CSV saved: `uploads/{gateway}/{gateway_name}.csv`

### `GatewayFile` (`app/dataProcessing/GatewayFileClass.py`)

The `GatewayFile` class normalizes raw DataFrames into the unified template format:
- Strips and lowercases column names for case-insensitive matching
- Converts float Reference values to clean strings (`123456.0` → `"123456"`)
- Fills NaN values in Debit/Credit with 0
- Validates required columns: `Date`, `Reference`, `Details`
- Provides `get_credits()`, `get_charges(keywords)`, `get_non_charge_debits(keywords)` accessors
- `generate_reconciliation_key(reference, amount, gateway)` — static method

### `FileTransformer` (`app/dataProcessing/file_transformer.py`)

Transforms raw bank/internal files to the unified template using `column_mapping` defined in `GatewayFileConfig`:
- Handles configurable header row index (`header_row_index`)
- Applies date format parsing (`date_format` in config)
- Returns `TransformationResult` with `success`, `row_count`, `errors`, and `normalized_data` (CSV bytes)

---

## Storage Backends

**`app/storage/base.py`** — `StorageBackend` ABC defines the interface:

| Method | Description |
|--------|-------------|
| `save_file(gateway, filename, content)` | Write file bytes to storage |
| `read_file_bytes(gateway, filename)` | Read file as bytes |
| `open_file(gateway, filename)` | Open as file-like object |
| `delete_file(gateway, filename)` | Remove file, return `True`/`False` |
| `list_files(gateway)` | List filenames in gateway directory |
| `file_exists(gateway, filename)` | Check existence |
| `ensure_gateway_directory(gateway)` | Create directory if needed |
| `archive_file(gateway, filename, content)` | Write to `{gateway}/archive/{filename}` |
| `find_file_by_prefix(gateway, prefix)` | Find first file matching prefix |

### Local Storage (`app/storage/local_storage.py`)

Files stored at `backend/uploads/{gateway}/{filename}`. Path traversal is prevented by validating that resolved paths remain under the `base_path`.

Archive files stored at `backend/uploads/{gateway}/archive/{filename}`.

### GCS Storage (`app/storage/gcs_storage.py`)

Files stored at `gs://{bucket}/{gateway}/{filename}` using `gcsfs`. Archive files at `gs://{bucket}/{gateway}/archive/{filename}`.

Requires `GCS_BUCKET_NAME` and service account credentials via `GOOGLE_APPLICATION_CREDENTIALS`.

---

## File Upload Service

**`app/upload/upload_files.py`** — `FileUpload` class

Key behaviours:
- **File limit**: Max 2 files per gateway directory (1 external + 1 internal). Uploading the same type replaces it.
- **Archive on every upload**: Before overwriting any active file, an immutable copy is saved with timestamp + 8-char UUID suffix.
- **Archive naming**: `{gateway_name}_{YYYYMMDD_HHMMSS}_{uuid8}.{ext}` stored in `{gateway}/archive/`
- **Archive is best-effort**: Failures are logged as warnings and never block the upload.

**`app/upload/template_generator.py`**

Generates downloadable Excel or CSV templates with the 5 unified columns: `Date`, `Reference`, `Details`, `Debit`, `Credit`. Includes example rows and column format documentation.

---

## Reports

**`app/reports/download_report.py`**

Queries all transactions for a gateway (with optional date range and run_id filters), then streams the result as:
- **XLSX**: 6-sheet workbook (see [Reports endpoint](#reports-apiV1reports))
- **CSV**: Single flat file with all transaction columns

**`app/reports/output_writer.py`**

Formats Excel workbooks using `openpyxl`:
- Garamond font, size 11 body / size 12 bold header
- Light gray header fill (`#D3D3D3`)
- Thin borders on all cells
- Auto-adjusted column widths (capped at 50 characters)

---

## Email Service

**`app/services/email_service.py`** — `EmailService` class

All emails are sent asynchronously via `FastAPI.BackgroundTasks` so they never block the API response.

Jinja2 HTML templates in `app/templates/email/`:

| Template | Trigger |
|----------|---------|
| `welcome_user.html` | New user created (includes auto-generated password) |
| `forgot_password.html` | Password reset requested |
| `password_changed.html` | Password successfully changed |
| `account_locked.html` | Account locked after failed attempts |

---

## Middleware

### Security Headers (`app/middleware/security.py`)

`SecurityHeadersMiddleware` adds on every response:
- `Strict-Transport-Security` — HSTS (HTTPS only)
- `Content-Security-Policy` — Restricts resource origins
- `X-Frame-Options: DENY` — Prevents clickjacking
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy` — Disables camera, microphone, geolocation

**Rate limiting** via SlowAPI (default limits):
- Login: 5 requests/minute
- Forgot password: 3 requests/minute
- Upload: 30 requests/minute
- All other endpoints: 100 requests/minute

### Audit Logging (`app/middleware/audit.py`)

`AuditLogMiddleware` records every state-changing request (POST, PUT, PATCH, DELETE):
- Excluded paths: `/auth/login`, `/auth/refresh`, `/auth/reset-password` (contain credentials)
- Recorded fields: method, path, user ID, username, IP, response status, timestamp

---

## Logging

**`app/customLogging/`**

- **Format**: JSON (production) or text (development) — controlled by `LOG_FORMAT` env var
- **Sensitive data filtering**: `SensitiveDataFilter` masks `password`, `token`, `secret`, `key` fields
- **Correlation ID**: `asgi-correlation-id` middleware injects `X-Request-ID` header; included in all log records
- **File rotation**: Logs written to `backend/logs/app.log` with daily rotation and 7-day retention

Helper functions in `logger.py`:
- `get_logger(name)` — returns configured logger for a module
- `log_operation(logger, operation, success, **kwargs)` — structured operation log
- `log_exception(logger, message, exc)` — structured exception log with traceback

---

## Exception Handling

**`app/exceptions/exceptions.py`** — Exception hierarchy:

```
MainException
├── FileUploadException         (400)
├── ReconciliationException     (422)
├── AuthException
│   ├── InvalidCredentialsException  (401)
│   ├── PermissionDeniedException    (403)
│   └── AccountBlockedException      (403)
└── ReadFileException           (500)
```

**`app/exceptions/handlers.py`** — Global handlers registered on the FastAPI app:
- `MainException` → JSON error response with appropriate HTTP status
- `RequestValidationError` → 422 with field-level detail
- `Exception` → 500 with generic message (details logged server-side only)

---

## Configuration

**`app/config/settings.py`** — `Settings` loaded from environment:

| Setting | Description |
|---------|-------------|
| `DATABASE_URL` | MySQL connection string |
| `ENVIRONMENT` | `development`, `staging`, `production` |
| `DEBUG` | Enable debug mode |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) |
| `STORAGE_BACKEND` | `local` or `gcs` |
| `GCS_BUCKET_NAME` | GCS bucket (required if `STORAGE_BACKEND=gcs`) |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FORMAT` | `json` or `text` |
| `TZ` | Timezone (`Africa/Nairobi`) |

**`app/config/gateways.py`** — Gateway helper functions:

| Function | Description |
|----------|-------------|
| `get_all_upload_gateways(db)` | All active gateway names (external + internal) |
| `get_external_gateways(db)` | Base gateway names for reports |
| `get_charge_keywords(db, gateway)` | Charge keyword list for a gateway |
| `get_gateway_display_name(db, gateway)` | Human-readable gateway name |
| `get_gateway_from_db(db, name)` | Full config dict for a gateway |

---

## Database Migrations

Alembic manages all schema changes.

```bash
cd backend

# Apply all pending migrations
alembic upgrade head

# Create new migration (auto-detect model changes)
alembic revision --autogenerate -m "short description"

# View history
alembic history --verbose

# Rollback one step
alembic downgrade -1

# Show current revision
alembic current
```

Migration files live in `backend/alembic/versions/`. Always review auto-generated migrations before applying — Alembic may miss some changes or generate incorrect ones.

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env`. All variables are required unless marked optional.

| Variable | Required | Example | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | `mysql+pymysql://user:pass@localhost:3306/recon` | MySQL connection string |
| `JWT_SECRET_KEY` | Yes | `openssl rand -hex 32` | JWT signing key (32+ chars) |
| `ENVIRONMENT` | Yes | `production` | App environment |
| `STORAGE_BACKEND` | Yes | `local` or `gcs` | File storage target |
| `GCS_BUCKET_NAME` | If GCS | `my-bucket` | GCS bucket name |
| `SMTP_HOST` | Yes | `smtp.gmail.com` | SMTP server |
| `SMTP_PORT` | Yes | `587` | SMTP port |
| `SMTP_USERNAME` | Yes | `noreply@example.com` | SMTP user |
| `SMTP_PASSWORD` | Yes | `app-password` | SMTP password |
| `SMTP_FROM_EMAIL` | Yes | `noreply@example.com` | From address |
| `TZ` | Yes | `Africa/Nairobi` | System timezone |
| `CORS_ORIGINS` | Yes | `http://localhost:3000` | Allowed frontend origins |
| `SUPER_ADMIN_SECRET` | Yes | random string | Protects super admin bootstrap endpoint |
| `LOG_LEVEL` | Yes | `INFO` | Logging verbosity |
| `LOG_FORMAT` | Yes | `json` | `json` or `text` |
