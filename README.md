# Payment Gateway Reconciliation System

A full-stack financial reconciliation platform built with FastAPI and React. Automates the matching of external bank statements (Equity, KCB, M-Pesa) with internal payment records using composite reconciliation keys.

## Features

- **Multi-Gateway Support**: Reconcile transactions from multiple payment gateways (Equity Bank, KCB, M-Pesa) with configurable gateway settings
- **Automated Matching**: Intelligent transaction matching using composite keys (Reference + Amount + Gateway)
- **Maker-Checker Workflow**: Role-based access control with separation of duties for critical operations
- **2-Step OTP Authentication**: Secure login with email-based OTP verification, concurrent session prevention, and account lockout
- **Password Security**: Configurable password policy, 90-day expiry, password history tracking, and forced change on first login
- **Forgot Password Flow**: Self-service password reset via email OTP verification
- **Batch Management**: Organize reconciliation work into batches with full audit trail
- **Report Generation**: Export reconciliation reports in Excel (XLSX) and CSV formats
- **Real-time Dashboard**: Monitor reconciliation status and transaction metrics
- **Manual Reconciliation**: Handle exceptions with approval workflow
- **Pluggable Storage**: Support for local file storage and Google Cloud Storage
- **Background Email Delivery**: All emails (OTP, welcome, notifications) sent via background tasks for instant UI response
- **Structured Logging**: JSON or text logging with correlation IDs for request tracing
- **Security Headers**: CSP, HSTS, rate limiting, and OWASP-recommended headers

## Tech Stack

### Backend
- **Framework**: FastAPI 0.118+
- **Database**: MySQL 8.0+ with SQLAlchemy ORM
- **Migrations**: Alembic
- **Authentication**: JWT (access + refresh tokens) with OTP 2FA
- **Email**: aiosmtplib with Jinja2 HTML templates
- **Data Processing**: Pandas, OpenPyXL
- **Rate Limiting**: SlowAPI
- **Request Tracing**: asgi-correlation-id

### Frontend
- **Framework**: React 19 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: Zustand + React Query (TanStack Query)
- **Routing**: React Router v6
- **Font**: Inter (Google Fonts)

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Storage**: Local filesystem or Google Cloud Storage
- **Timezone**: Africa/Nairobi (EAT, UTC+3)

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   React SPA     │────>│   FastAPI        │
│   (Port 3000)   │     │   (Port 8000)    │
└─────────────────┘     └────────┬─────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
        v                        v                        v
┌───────────────┐    ┌───────────────────┐    ┌───────────────┐
│    MySQL      │    │  File Storage     │    │  SMTP Email   │
│   Database    │    │  (Local/GCS)      │    │  Service      │
└───────────────┘    └───────────────────┘    └───────────────┘
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- MySQL 8.0+
- Docker & Docker Compose (recommended)

### Installation

#### Using Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd payment-reconciliation
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration (all variables are required)
   ```

3. **Start the services**
   ```bash
   docker-compose up --build
   ```

4. **Run database migrations**
   ```bash
   docker exec -it fastapi_application alembic upgrade head
   ```

5. **Create the first super admin**
   ```bash
   curl -X POST http://localhost:8000/api/v1/users/create-super-admin \
     -H "Content-Type: application/json" \
     -d '{
       "first_name": "Admin",
       "last_name": "User",
       "email": "admin@example.com",
       "password": "YourSecurePassword1!",
       "secret_key": "<your SUPER_ADMIN_SECRET from .env>"
     }'
   ```

6. **Access the application**
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs (development only)
   - Frontend: http://localhost:3000

#### Manual Installation

1. **Backend Setup**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # Linux/Mac

   # Install dependencies
   pip install -r requirements.txt

   # Configure environment
   cp .env.example .env
   # Edit .env with your configuration

   # Run database migrations
   alembic upgrade head

   # Start the server
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

### Configuration

All environment variables are **required** and must be set in the `.env` file. The application will fail to start if any are missing.

Copy `.env.example` to `.env` and configure all values. Key variables:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | MySQL connection string (`mysql+pymysql://user:pass@host:port/db`) |
| `JWT_SECRET_KEY` | Secret for JWT signing (min 32 chars, generate with `openssl rand -hex 32`) |
| `SUPER_ADMIN_SECRET` | One-time secret for initial super admin creation (min 16 chars) |
| `ENVIRONMENT` | `development`, `staging`, or `production` |
| `STORAGE_BACKEND` | `local` or `gcs` |
| `SMTP_HOST` / `SMTP_PASSWORD` | Email server credentials for OTP delivery |
| `TZ` | Timezone (`Africa/Nairobi`) |

See `.env.example` for the complete list with documentation.

## Authentication

### Login Flow (2-Step OTP)

1. **Step 1**: User submits credentials → Server validates and sends a 6-digit OTP to email
2. **Step 2**: User enters OTP → Server issues JWT access + refresh tokens

### Security Features

- **Account Lockout**: After 5 failed login attempts, account locks for 15 minutes
- **Concurrent Session Prevention**: Only one active session per user; new login invalidates previous session
- **Password Policy**: Configurable minimum length, uppercase, lowercase, digit, and special character requirements
- **Password Expiry**: Passwords expire after 90 days (configurable)
- **Password History**: Prevents reuse of last 5 passwords (configurable)
- **Rate Limiting**: Login (5/min), OTP verify (10/min), forgot password (3/min)
- **OTP Resend Cooldown**: 2-minute cooldown between OTP resend requests

### User Roles

| Role | Description | Capabilities |
|------|-------------|--------------|
| `super_admin` | System Administrator | Create/manage user accounts, assign roles |
| `admin` | Approver/Checker | Approve/reject manual reconciliations, gateway changes, batch deletions |
| `user` | Inputter/Maker | Create batches, upload files, run reconciliation, initiate actions |

## Usage

### Reconciliation Workflow

1. **Create a Batch**: Start a new reconciliation batch
2. **Upload Files**: Upload external (bank) and internal (system) transaction files
3. **Run Reconciliation**: System automatically matches transactions
4. **Review Results**: Handle unmatched transactions manually if needed
5. **Generate Reports**: Export reconciliation results
6. **Close Batch**: Finalize the batch when complete

### File Format

Upload files must contain these columns:

| Column | Description | Required |
|--------|-------------|----------|
| Date | Transaction date (YYYY-MM-DD) | Yes |
| Reference | Unique transaction identifier | Yes |
| Details | Transaction description | Yes |
| Debit | Debit amount | No |
| Credit | Credit amount | No |

Download a template from the upload page to ensure correct formatting.

## API Documentation

Interactive API documentation is available at (development only):
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

| Group | Method | Endpoint | Description |
|-------|--------|----------|-------------|
| Auth | POST | `/api/v1/auth/login` | Step 1: Verify credentials, send OTP |
| Auth | POST | `/api/v1/auth/verify-otp` | Step 2: Verify OTP, get tokens |
| Auth | POST | `/api/v1/auth/forgot-password` | Request password reset OTP |
| Batch | POST | `/api/v1/batch` | Create new batch |
| Upload | POST | `/api/v1/upload/file` | Upload transaction file |
| Reconcile | POST | `/api/v1/reconcile` | Run reconciliation |
| Reports | GET | `/api/v1/reports/download/batch` | Download report |
| Users | POST | `/api/v1/users` | Create user (super admin only) |
| Gateways | GET | `/api/v1/gateway-config` | List gateway configurations |

## Database Migrations

```bash
# Run pending migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# View migration history
alembic history

# Rollback one revision
alembic downgrade -1
```

## Project Structure

```
.
├── app/                        # Backend application
│   ├── auth/                   # Authentication (JWT, password, dependencies)
│   ├── config/                 # App settings and gateway configuration
│   ├── controller/             # API route handlers (11 routers)
│   ├── customLogging/          # Structured logging configuration
│   ├── database/               # Database connection and session
│   ├── dataLoading/            # File loading (xlsx, csv)
│   ├── dataProcessing/         # Data transformation and normalization
│   ├── exceptions/             # Custom exceptions and handlers
│   ├── middleware/              # Security headers, audit, request logging
│   ├── pydanticModels/         # Request/response schemas
│   ├── reconciler/             # Core reconciliation engine
│   ├── reports/                # Report generation (Excel/CSV)
│   ├── services/               # Email and OTP services
│   ├── sqlModels/              # SQLAlchemy ORM models
│   ├── storage/                # File storage backends (local, GCS)
│   ├── templates/              # Jinja2 email templates
│   ├── upload/                 # File upload and batch handling
│   └── main.py                 # FastAPI application entry point
├── alembic/                    # Database migrations
├── frontend/                   # React + TypeScript frontend
│   └── src/
│       ├── api/                # API client modules
│       ├── components/         # Reusable UI components
│       │   ├── auth/           # OTP input, countdown timer
│       │   ├── layout/         # Header, sidebar, protected routes
│       │   └── ui/             # Buttons, modals, tables, forms
│       ├── features/           # Feature pages (11 modules)
│       ├── hooks/              # Custom React hooks
│       ├── lib/                # Utilities
│       ├── stores/             # Zustand state management
│       └── types/              # TypeScript type definitions
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example                # Environment variable reference
```

## Security

- All environment variables are required from `.env` — no hardcoded defaults
- JWT secrets must be strong (32+ characters)
- API docs (Swagger/ReDoc) are disabled in production
- Security headers: CSP, X-Frame-Options, X-Content-Type-Options, HSTS (HTTPS)
- Rate limiting on all authentication endpoints
- Audit logging for sensitive operations (user management, password changes, reconciliation)
- Email notifications for account lockout and password changes
- All emails sent as background tasks (non-blocking)

## License

This project is proprietary software. All rights reserved.
