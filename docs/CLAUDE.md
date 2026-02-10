# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Payment Gateway Reconciliation System built with FastAPI (backend) and React + TypeScript (frontend). Reconciles financial transactions between external bank statements (Equity, KCB, M-Pesa) and internal Workpay records by matching composite reconciliation keys.

## Project Structure

```
recon/
├── backend/                  (FastAPI application)
│   ├── app/                  (Python application code)
│   ├── alembic/              (Database migrations)
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── .env.example
│   ├── uploads/              (runtime data, gitignored)
│   └── logs/                 (runtime data, gitignored)
├── frontend/                 (React + TypeScript)
├── docs/                     (API documentation)
├── .github/workflows/
├── docker-compose.yml
├── .gitignore
├── CLAUDE.md
└── README.md
```

## Running the Application

**Local development (backend):**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Docker (recommended):**
```bash
docker-compose up --build
```
- FastAPI: `http://localhost:8000`
- Frontend: `http://localhost:3000`

**Environment variables:**

All environment variables are **required** and must be set in the `backend/.env` file. The application will fail to start if any are missing. Copy `backend/.env.example` to `backend/.env` and configure all values. See `backend/.env.example` for the complete list with documentation.

Key variables: `DATABASE_URL`, `JWT_SECRET_KEY`, `ENVIRONMENT`, `STORAGE_BACKEND`, `SMTP_HOST`, `SMTP_PASSWORD`, `TZ`.

**Database migrations:**
```bash
cd backend
alembic upgrade head
```

## Architecture

### Layered Design
```
Controller Layer (backend/app/controller/)     ─── routers
    ↓
Auth & Dependencies (backend/app/auth/)        ─── JWT, password, role checks
    ↓
Services (backend/app/services/)               ─── Email service
    ↓
Gateway Config (backend/app/config/gateways.py)
    ↓
Business Logic (Reconciler.py)
    ↓
Data Processing (GatewayFile)
    ↓
Data Loading (DataLoader + StorageBackend)
    ↓
Persistence (MySQL via SQLAlchemy)
```

### Key Components

- **`backend/app/config/gateways.py`**: Centralized gateway configuration. Database (`gateway_configs` table) is the single source of truth.

- **`backend/app/reconciler/Reconciler.py`**: Core orchestrator. Loads files via `GatewayFile`, matches transactions by `Reference` column, persists results to unified `transactions` table.

- **`backend/app/dataProcessing/GatewayFileClass.py`**: `GatewayFile` class for unified file processing. Handles file normalization, column validation, float-to-string Reference conversion, and credit/debit extraction.

- **`backend/app/dataLoading/data_loader.py`**: `DataLoader` class reads files using pluggable `StorageBackend`. Supports xlsx, xls, and csv.

- **`backend/app/storage/`**: Pluggable storage layer with `LocalStorage` and `GcsStorage` backends.

- **`backend/app/auth/config.py`**: `AuthSettings` loaded from environment. JWT, password policy, SMTP, and account security settings. Also contains `validate_password_strength()`.

- **`backend/app/auth/security.py`**: JWT token creation/verification, password hashing (bcrypt), session token generation.

- **`backend/app/auth/dependencies.py`**: FastAPI dependency injection for authentication and authorization. See Role-Based Access Control section below.

- **`backend/app/services/email_service.py`**: Async email service using `aiosmtplib` with Jinja2 HTML templates. All emails sent via FastAPI `BackgroundTasks` (non-blocking).

- **`backend/app/templates/email/`**: Jinja2 HTML email templates — `welcome_user.html`, `forgot_password.html`, `password_changed.html`, `account_locked.html`.

- **`backend/app/middleware/security.py`**: Security headers (CSP, HSTS, X-Frame-Options, etc.), rate limiting (SlowAPI), and file size validation.

### Authentication Flow (Single-Step)

1. **Login**: `POST /auth/login` → validates credentials → creates session → returns JWT access + refresh tokens

**Security Features:**
- Account lockout after N failed login attempts (configurable, default 5)
- Concurrent session prevention: new login invalidates previous session
- Password expiry (default 90 days), password history (default last 5)
- Rate limiting on all auth endpoints
- Background email delivery (non-blocking)

### Reconciliation Flow

1. Select gateway → upload external + internal files
2. Select gateway → preview (dry run with carry-forward) → save → auto-creates ReconciliationRun
3. Carry-forward: Previously unreconciled items included in future runs
4. Duplicate skipping: UniqueConstraint on (reconciliation_key, gateway), IntegrityError caught per-row

### Role-Based Access Control (Maker-Checker Pattern)

| Role | Description | Capabilities |
|------|-------------|--------------|
| `user` | Inputter/Maker | Upload files, run reconciliation, initiate manual reconciliation, submit gateway change requests |
| `admin` | Approver/Checker | Approve/reject manual reconciliations, approve/reject gateway change requests |
| `super_admin` | System Administrator | Manage user accounts (create, update, deactivate). No access to operational approvals |

**Backend Dependencies** (in `backend/app/auth/dependencies.py`):
- `get_current_user`: Extracts user from JWT, validates login session
- `require_active_user`: Checks user is active and password not expired
- `require_user_role`: Only users (makers) - for initiating actions
- `require_admin_only`: Only admins (checkers) - for approving actions
- `require_admin`: Admin or super_admin
- `require_super_admin`: Only super admins - for user management

### Matching Logic

- Match on composite reconciliation key: `{reference}|{amount}|{base_gateway}`
- **Reference**: Cleaned string (no decimals, e.g., `123456.0` → `123456`)
- **Amount**: Absolute whole number (no cents)
- **Base Gateway**: Same for external and internal (e.g., `equity` for both)
- Credits: `Credit > 0` (auto-reconciled)
- Debits: `Debit > 0` (matched against internal records)
- Charges: Debits with keywords in Reference OR Details column (configurable per gateway, auto-reconciled)

### Data Flow

1. Upload files: Select gateway → upload external + internal files
   - Storage path: `uploads/{gateway}/{filename}`
2. Reconcile: `POST /api/v1/reconcile` with gateway parameter
   - Validates files exist, fills null values, generates reconciliation keys
   - Matches transactions, saves to database, creates ReconciliationRun
3. Download report: `GET /api/v1/reports/download`

## Database Migrations (Alembic)

```bash
cd backend

# Run pending migrations
alembic upgrade head

# Create new migration (auto-generate from model changes)
alembic revision --autogenerate -m "description of changes"

# View migration history
alembic history

# Downgrade one revision
alembic downgrade -1

# View current revision
alembic current
```

Migration files are in `backend/alembic/versions/`. Always review auto-generated migrations before applying.

## Template Columns (Unified)

**Single unified template** (used for both external and internal records):
- Date (YYYY-MM-DD format, mandatory)
- Reference (unique transaction identifier, mandatory)
- Details (transaction narration/description, mandatory)
- Debit (debit amount, number, optional)
- Credit (credit amount, number, optional)

## Key Implementation Details

- **Single-Step Auth**: Login with email + password → JWT tokens (no OTP)
- **Forgot Password**: Generate reset_token → email link → reset password
- **User Creation**: Auto-generate password → welcome email with credentials
- **Reconciliation Runs**: Auto-created on reconcile, format `RUN-YYYYMMDD-HHMMSS-{uuid8}`
- **Carry-Forward**: Previously unreconciled items included in future reconciliation runs
- **Duplicate Key Deduplication**: Auto-reconciled transactions (charges, deposits) get counter suffixes on duplicate keys
- **Reference Handling**: Automatically converts float Reference values (e.g., `123456.0` from Excel) to clean strings (`"123456"`)
- **Reconciliation Key**: Generated composite key `{reference}|{amount}|{base_gateway}` stored in `reconciliation_key` column
- **Timezone**: Application standardized to Africa/Nairobi (EAT, UTC+3) across Python, MySQL sessions, and Docker
- **Security Headers**: CSP, HSTS, X-Frame-Options (DENY), X-Content-Type-Options (nosniff), Permissions-Policy
- **Rate Limiting**: SlowAPI with per-endpoint limits
- **Structured Logging**: JSON or text format, configurable level, correlation IDs via `asgi-correlation-id`
- **Error Handling**: Custom `MainException` hierarchy with centralized handlers

## Frontend Architecture

- **Framework**: React 19 + TypeScript, Vite, Tailwind CSS
- **State**: Zustand (auth store) + React Query (server state)
- **Routing**: React Router v6 with protected routes
- **API Client**: Axios with interceptors for JWT refresh and error handling
- **Font**: Inter (Google Fonts)

### Feature Pages (`frontend/src/features/`)
- `auth/` — LoginPage, ChangePasswordPage, ForgotPasswordPage
- `dashboard/` — DashboardPage
- `gateways/` — GatewaysPage, GatewayApprovalPage
- `operations/` — OperationsPage, AuthorizationPage
- `reconcile/` — ReconciliationPage
- `reports/` — ReportsPage
- `runs/` — ReconciliationRunsPage
- `transactions/` — TransactionsPage
- `upload/` — UploadPage
- `users/` — UsersPage

### Reusable Components (`frontend/src/components/`)
- `layout/` — Header, Sidebar, Layout (with protected route logic)
- `ui/` — Button, Input, Select, SearchableSelect, Pagination, etc.
