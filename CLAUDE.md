# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Payment Gateway Reconciliation System built with FastAPI. Reconciles financial transactions between payment gateways (Equity, KCB, M-Pesa) and Workpay (internal payment processing system) by matching transaction records and generating reports.

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
- Redis: `localhost:6379`

## Architecture

### Layered Design
```
Controller Layer (FastAPI routes)
    ↓
Business Logic (Reconciler.py - orchestrates reconciliation)
    ↓
Data Processing (GatewayFileClass, WorkpayFileClass)
    ↓
Data Loading (read.py, readGcs.py) + File Configs + Pydantic Models
    ↓
Persistence (MySQL via SQLAlchemy, Redis for sessions)
```

### Key Components

- **`app/reconciler/Reconciler.py`**: Core orchestrator that loads files, matches transactions, and persists results. This is where the reconciliation logic lives.

- **`app/dataProcessing/`**: OOP classes (`GatewayFile`, `WorkpayFile`) handle file normalization, column validation, date/numeric conversion, and data extraction (debits, credits, charges, payouts, refunds).

- **`app/fileConfigs/`**: Configuration classes per gateway defining column mappings, file prefixes, data types, date formats, and matching columns. Adding a new gateway means creating a new config here.

- **`app/pydanticModels/`**: Validation schemas per gateway type. Each gateway has models for bank-side (debits/credits/charges) and workpay-side (payouts/refunds).

- **`app/sqlModels/`**: SQLAlchemy ORM models inheriting from base transaction models. Tables grouped by gateway (e.g., `equity_debits`, `workpay_equity_payouts`).

### Data Flow

1. Session created → stored in Redis with format `sess_YYYY-MM-DD_HH-MM-SS`
2. Files uploaded to `uploads/{session_id}/`
3. Reconciliation triggered: files loaded as DataFrames → normalized → matched by reference columns → marked Reconciled/Unreconciled
4. Results bulk-inserted to MySQL (6 tables per gateway)
5. Reports exported as Excel with multiple sheets

### Matching Logic

- **Equity**: matches on "Customer Reference" column
- **KCB/M-Pesa**: matches on "TRANSACTION ID" or "API REFERENCE"
- Uses pandas `isin()` for set-based matching between bank and workpay records

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/create-session` | Create new reconciliation session |
| GET | `/api/v1/current/session` | Get active session |
| POST | `/api/v1/upload/file` | Upload bank statement or workpay file |
| POST | `/api/v1/reconcile/{gateway}` | Run reconciliation (equity/kcb/mpesa) |
| POST | `/api/v1/download/{gateway}` | Download Excel report |

## Adding a New Payment Gateway

1. Create config class in `app/fileConfigs/` (copy existing, adjust columns/mappings)
2. Create Pydantic models in `app/pydanticModels/`
3. Create SQL models in `app/sqlModels/`
4. Add reconciliation route in `app/controller/reconcile.py`
5. Update `Reconciler.py` with gateway-specific matching logic if needed

## Configuration Pattern

Each gateway config defines:
- `file_prefix`: filename pattern to search for
- `columns`: expected column names from source file
- `numeric_columns`/`string_columns`: type handling
- `date_format`: parsing format string
- `matching_column`: column used for record linking
- `filter_keywords`: patterns to identify charges/fees