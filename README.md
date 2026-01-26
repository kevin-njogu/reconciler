# Payment Gateway Reconciliation System

A full-stack financial reconciliation platform built with FastAPI and React. Automates the matching of external bank statements (Equity, KCB, M-Pesa) with internal payment records using composite reconciliation keys.

## Features

- **Multi-Gateway Support**: Reconcile transactions from multiple payment gateways (Equity Bank, KCB, M-Pesa) with configurable gateway settings
- **Automated Matching**: Intelligent transaction matching using composite keys (Reference + Amount + Gateway)
- **Maker-Checker Workflow**: Role-based access control with separation of duties for critical operations
- **Batch Management**: Organize reconciliation work into batches with full audit trail
- **Report Generation**: Export reconciliation reports in Excel (XLSX) and CSV formats
- **Real-time Dashboard**: Monitor reconciliation status and transaction metrics
- **Manual Reconciliation**: Handle exceptions with approval workflow
- **Pluggable Storage**: Support for local file storage and Google Cloud Storage

## Tech Stack

### Backend
- **Framework**: FastAPI 0.118+
- **Database**: MySQL with SQLAlchemy ORM
- **Migrations**: Alembic
- **Authentication**: JWT with refresh tokens
- **Data Processing**: Pandas, OpenPyXL

### Frontend
- **Framework**: React 19 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: Zustand + React Query
- **Routing**: React Router v6

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Storage**: Local filesystem or Google Cloud Storage

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   React SPA     │────▶│   FastAPI       │
│   (Frontend)    │     │   (Backend)     │
└─────────────────┘     └────────┬────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
        ▼                        ▼                        ▼
┌───────────────┐    ┌───────────────────┐    ┌───────────────┐
│    MySQL      │    │  File Storage     │    │  Gateway      │
│   Database    │    │  (Local/GCS)      │    │  Configs      │
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
   git clone https://github.com/your-org/payment-reconciliation.git
   cd payment-reconciliation
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start the services**
   ```bash
   docker-compose up --build
   ```

4. **Access the application**
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Frontend: http://localhost:3000

#### Manual Installation

1. **Backend Setup**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or: venv\Scripts\activate  # Windows

   # Install dependencies
   pip install -r requirements.txt

   # Run database migrations
   alembic upgrade head

   # Start the server
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Frontend Setup**
   ```bash
   cd frontend

   # Install dependencies
   npm install

   # Start development server
   npm run dev
   ```

### Configuration

Copy `.env.example` to `.env` and configure the following:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL_LOCAL` | MySQL connection string | - |
| `STORAGE_BACKEND` | Storage type (`local` or `gcs`) | `local` |
| `JWT_SECRET_KEY` | Secret for JWT signing (min 32 chars) | - |
| `ENVIRONMENT` | App environment | `development` |
| `LOG_LEVEL` | Logging level | `INFO` |

See `.env.example` for the complete list of configuration options.

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

### User Roles

| Role | Description | Capabilities |
|------|-------------|--------------|
| `user` | Inputter/Maker | Create batches, upload files, run reconciliation, initiate actions |
| `admin` | Approver/Checker | Approve/reject manual reconciliations, gateway changes, batch deletions |
| `super_admin` | System Administrator | Manage user accounts |

## API Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/batch` | Create new batch |
| POST | `/api/v1/upload/file` | Upload transaction file |
| POST | `/api/v1/reconcile` | Run reconciliation |
| GET | `/api/v1/reports/download/batch` | Download report |

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

## Development

### Project Structure

```
.
├── app/                    # Backend application
│   ├── auth/              # Authentication & authorization
│   ├── config/            # Configuration management
│   ├── controller/        # API route handlers
│   ├── dataLoading/       # File loading utilities
│   ├── dataProcessing/    # Data transformation
│   ├── database/          # Database configuration
│   ├── exceptions/        # Custom exceptions
│   ├── middleware/        # Request middleware
│   ├── pydanticModels/    # Request/response schemas
│   ├── reconciler/        # Core reconciliation engine
│   ├── reports/           # Report generation
│   ├── sqlModels/         # SQLAlchemy ORM models
│   ├── storage/           # File storage backends
│   └── upload/            # File upload handling
├── alembic/               # Database migrations
├── frontend/              # React frontend
│   ├── src/
│   │   ├── api/          # API client
│   │   ├── components/   # Reusable UI components
│   │   ├── features/     # Feature modules
│   │   ├── hooks/        # Custom React hooks
│   │   ├── lib/          # Utilities
│   │   └── stores/       # State management
│   └── ...
├── docs/                  # Documentation
├── docker-compose.yml     # Docker configuration
└── requirements.txt       # Python dependencies
```

### Running Tests

```bash
# Backend tests
pytest

# Frontend tests
cd frontend && npm test
```

### Code Quality

```bash
# Backend linting
ruff check app/

# Frontend linting
cd frontend && npm run lint
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Commit Guidelines

- Use clear, descriptive commit messages
- Reference issue numbers when applicable
- Keep commits focused and atomic

## Security

- Never commit `.env` files or credentials
- Use environment variables for sensitive configuration
- JWT tokens should use strong secrets (32+ characters)
- All sensitive operations require maker-checker approval

## License

This project is proprietary software. All rights reserved.

## Support

For issues and feature requests, please open an issue on GitHub.

---

Built with FastAPI and React
