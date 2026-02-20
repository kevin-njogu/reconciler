# Payment Gateway Reconciliation System

A full-stack financial reconciliation platform built with FastAPI and React. Automates the matching of external bank statements (Equity, KCB, M-Pesa) with internal Workpay payment records using composite reconciliation keys.

## Features

- **Multi-Gateway Support** — Reconcile transactions from multiple payment gateways with configurable per-gateway settings
- **Automated Matching** — Intelligent transaction matching using composite keys (`Reference|Amount|Gateway`)
- **Carry-Forward Reconciliation** — Previously unreconciled items participate in future reconciliation runs
- **Auto-Classification** — Credits auto-reconciled as deposits; charge-keyword debits auto-reconciled as charges
- **Maker-Checker Workflow** — Role-based separation of duties for reconciliation and gateway configuration
- **Manual Reconciliation** — Users can manually reconcile exceptions; admins approve or reject
- **Report Generation** — Export 8-sheet XLSX or flat CSV reports per gateway with date/run filters
- **Real-time Dashboard** — Per-gateway match rates, unreconciled counts, and pending approvals
- **Pluggable Storage** — Local filesystem or Google Cloud Storage for uploaded files
- **File Archiving** — Every upload creates an immutable audit copy before overwriting
- **Secure Authentication** — JWT access + refresh tokens, concurrent session prevention, account lockout
- **Password Security** — Configurable policy, 90-day expiry, password history, forced change on first login
- **Background Email Delivery** — Welcome, reset, lockout, and change notifications via async SMTP
- **Structured Logging** — JSON/text logging with correlation IDs, sensitive-data masking, file rotation
- **Security Headers** — CSP, HSTS, X-Frame-Options, rate limiting on all endpoints

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, SQLAlchemy, Alembic, Pandas, OpenPyXL |
| Database | MySQL 8.0+ |
| Authentication | JWT (HS256), bcrypt, aiosmtplib |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS |
| State | Zustand (auth), TanStack React Query (server state) |
| Storage | Local filesystem or Google Cloud Storage |
| Deployment | Google Cloud Run, Cloud Build, Cloud SQL |

## Architecture

```
┌─────────────────┐         ┌──────────────────────┐
│   React SPA     │ ──────► │   FastAPI (Port 8000) │
│   (Port 3000)   │         └──────────┬───────────┘
└─────────────────┘                    │
                       ┌───────────────┼───────────────┐
                       ▼               ▼               ▼
               ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
               │    MySQL     │ │File Storage  │ │ SMTP Email   │
               │   Database   │ │(Local / GCS) │ │  Service     │
               └──────────────┘ └──────────────┘ └──────────────┘
```

## User Roles

| Role | Description | Key Capabilities |
|------|-------------|-----------------|
| `user` | Maker / Inputter | Upload files, run reconciliation, submit manual recons, submit gateway change requests |
| `admin` | Checker / Approver | Approve/reject manual reconciliations, approve/reject gateway change requests |
| `super_admin` | System Administrator | Create and manage user accounts. No access to operational approvals |

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── auth/               # JWT, bcrypt, auth dependencies
│   │   ├── config/             # App settings, gateway helpers
│   │   ├── controller/         # API route handlers (11 routers)
│   │   ├── customLogging/      # Structured logging, request tracing
│   │   ├── database/           # SQLAlchemy engine and session
│   │   ├── dataLoading/        # xlsx/csv file reader
│   │   ├── dataProcessing/     # File normalization and transformation
│   │   ├── exceptions/         # Custom exception hierarchy + handlers
│   │   ├── middleware/         # Security headers, audit log, rate limiting
│   │   ├── pydanticModels/     # Request/response schemas
│   │   ├── reconciler/         # Core reconciliation engine
│   │   ├── reports/            # Excel/CSV report generation
│   │   ├── services/           # Async email service
│   │   ├── sqlModels/          # SQLAlchemy ORM models
│   │   ├── storage/            # Pluggable storage (local/GCS)
│   │   ├── templates/email/    # Jinja2 email templates
│   │   ├── upload/             # File upload + template generation
│   │   └── main.py             # App entry, middleware, router registration
│   ├── alembic/                # Database migrations
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/
│       ├── api/                # Axios client + endpoint modules
│       ├── components/         # Reusable UI + layout components
│       ├── features/           # Feature pages (auth, dashboard, reconcile, etc.)
│       ├── hooks/              # useToast and other custom hooks
│       ├── lib/                # Utility functions
│       ├── stores/             # Zustand auth store
│       └── types/              # TypeScript interfaces
├── docs/
│   ├── backend.md              # Detailed backend documentation
│   ├── frontend.md             # Detailed frontend documentation
│   └── deployment.md           # GCP deployment guide
├── Dockerfile                  # Multi-stage build (frontend + backend)
├── nginx.conf                  # Reverse proxy configuration
├── supervisord.conf            # Process manager configuration
├── cloudbuild.yaml             # CI/CD pipeline
├── docker-compose.yml          # Local development
└── .gitignore
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- MySQL 8.0+
- Docker & Docker Compose (recommended)

### Docker (Recommended)

```bash
# 1. Clone the repository
git clone <repository-url>
cd recon

# 2. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env — all variables are required

# 3. Start all services
docker-compose up --build

# 4. Run database migrations (first time only)
docker exec -it fastapi_application alembic upgrade head

# 5. Create the first super admin
curl -X POST http://localhost:8000/api/v1/users/create-super-admin \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Admin",
    "last_name": "User",
    "email": "admin@example.com",
    "password": "YourSecurePassword1!",
    "secret_key": "<SUPER_ADMIN_SECRET from .env>"
  }'
```

Access:
- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **API Docs** (dev only): http://localhost:8000/docs

### Manual Installation

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Linux/Mac
pip install -r requirements.txt
cp .env.example .env          # Edit all values
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Configuration

All environment variables are **required** and must be set in `backend/.env`. The app fails to start if any are missing.

| Variable | Example | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `mysql+pymysql://user:pass@localhost:3306/recon` | MySQL connection string |
| `JWT_SECRET_KEY` | `openssl rand -hex 32` | JWT signing key (32+ chars) |
| `ENVIRONMENT` | `production` | `development`, `staging`, or `production` |
| `STORAGE_BACKEND` | `local` | `local` or `gcs` |
| `GCS_BUCKET_NAME` | `my-bucket` | Required when `STORAGE_BACKEND=gcs` |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server hostname |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USERNAME` | `noreply@example.com` | SMTP login |
| `SMTP_PASSWORD` | — | SMTP password |
| `SMTP_FROM_EMAIL` | `noreply@example.com` | From address on emails |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed frontend origins |
| `TZ` | `Africa/Nairobi` | System timezone |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FORMAT` | `json` | `json` or `text` |

See `backend/.env.example` for the full list with descriptions.

## Reconciliation Workflow

```
1. Upload Files
   ├── External (bank statement)
   └── Internal (Workpay records)

2. Preview (Dry Run)
   ├── Auto-classify rows: deposit, charge, debit, payout
   ├── Include carry-forward unreconciled items from database
   └── Match external debits ↔ internal payouts by composite key

3. Save
   ├── Persist all transactions (matched + unmatched) to database
   └── Create ReconciliationRun record (RUN-YYYYMMDD-HHMMSS-{uuid8})

4. Review
   ├── Manual reconciliation for exceptions (maker submits, admin approves)
   └── Download report (XLSX: 8 sheets, or CSV: flat file)
```

### Reconciliation Key

For reconcilable transactions (debits ↔ payouts):
```
{reference}|{amount}|{base_gateway}
```

For auto-reconciled transactions (charges, deposits — date included to prevent cross-run duplicates):
```
{reference}|{amount}|{base_gateway}|{YYYYMMDD}
```

### File Format

Upload files (template mode) must contain these columns:

| Column | Required | Description |
|--------|----------|-------------|
| Date | Yes | Transaction date (`YYYY-MM-DD`) |
| Reference | Yes | Unique transaction identifier |
| Details | Yes | Transaction narration |
| Debit | No | Debit amount (number) |
| Credit | No | Credit amount (number) |

Download a pre-formatted template from the Reconcile page. For raw bank statements, use **Upload Raw Statement** mode — the system maps columns automatically using the gateway configuration.

## API Overview

Interactive docs available at http://localhost:8000/docs (development only).

| Group | Prefix | Description |
|-------|--------|-------------|
| Auth | `/api/v1/auth` | Login, logout, token refresh, password management |
| Users | `/api/v1/users` | User CRUD (super_admin only) |
| Gateways | `/api/v1/gateway-config` | Gateway config + maker-checker workflow |
| Upload | `/api/v1/upload` | File upload, download, delete, template |
| Reconcile | `/api/v1/reconcile` | Preview and execute reconciliation |
| Operations | `/api/v1/operations` | Manual reconciliation + admin authorization |
| Reports | `/api/v1/reports` | Report download (XLSX / CSV) |
| Runs | `/api/v1/runs` | Reconciliation run history |
| Transactions | `/api/v1/transactions` | Transaction browsing and filtering |
| Dashboard | `/api/v1/dashboard` | Aggregate statistics |

## Database Migrations

```bash
cd backend

# Apply all pending migrations
alembic upgrade head

# Create a new migration (auto-detect model changes)
alembic revision --autogenerate -m "short description"

# View history
alembic history --verbose

# Rollback one step
alembic downgrade -1

# Check current revision
alembic current
```

## Security

- Sensible defaults for non-sensitive config; secrets managed via GCP Secret Manager
- JWT secrets must be 32+ characters (`openssl rand -hex 32`)
- API docs (Swagger/ReDoc) are disabled in production (`ENVIRONMENT=production`)
- Security headers on every response: CSP, HSTS, X-Frame-Options, X-Content-Type-Options
- Rate limiting: login (5/min), forgot-password (3/min), uploads (30/min)
- Audit log records every state-changing API call (user, IP, timestamp, response status)
- Sensitive fields (passwords, tokens, secrets) masked in all log output
- File uploads validated for extension before storage; archive copy saved before overwrite
- Single active session per user — new login invalidates previous session

## Documentation

- [Backend Documentation](docs/backend.md) — Architecture, controllers, reconciliation engine, models, storage, configuration
- [Frontend Documentation](docs/frontend.md) — Components, routing, state management, API modules, role-based access
- [Deployment Guide](docs/deployment.md) — Step-by-step GCP deployment with Cloud Run, Cloud SQL, Secret Manager, and Cloud Build

## License

This project is proprietary software. All rights reserved.
