# Batch Management

## Overview

A batch is the key control unit for each reconciliation session. All files uploaded and transactions reconciled are tagged with a `batch_id`. Batches enforce a controlled lifecycle: creation, usage (file upload & reconciliation), and closure.

## Batch Lifecycle

```
[Create] → [Pending] → [Upload Files] → [Reconcile] → [Close] → [Completed]
                                                              ↓
                                               (all transactions must be reconciled)
```

### Statuses
- **pending** – Batch is open and accepting uploads/reconciliations
- **completed** – Batch has been closed by its creator

## Business Rules

| Rule | Description |
|------|-------------|
| One pending batch per user | A user cannot create a new batch if they have an existing pending batch |
| Creator-only close | Only the user who created a batch can close it |
| Reconciliation gate | A batch cannot be closed if any transactions are unreconciled |
| No edits | Batches cannot be edited after creation (only created, closed, or deleted) |
| Multi-gateway | One batch can handle reconciliation of multiple different gateways |
| Storage provisioning | Creating a batch provisions a storage directory (local or GCS) |
| Maker-checker delete | Deletion requires user initiation + admin approval |

## API Endpoints

### Batch CRUD

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| POST | `/api/v1/batch` | user, admin | Create a new batch |
| GET | `/api/v1/batch` | user, admin | List all batches (paginated) |
| GET | `/api/v1/batch/{batch_id}` | user, admin | Get batch details |
| POST | `/api/v1/batch/{batch_id}/close` | creator only | Close a batch |

### Delete Requests (Maker-Checker)

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| POST | `/api/v1/batch/{batch_id}/delete-request` | user, admin | Initiate delete request |
| GET | `/api/v1/batch/delete-requests/list` | user, admin | List delete requests |
| POST | `/api/v1/batch/delete-requests/{id}/review` | admin only | Approve/reject delete request |

### File Management

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| GET | `/api/v1/batch/{batch_id}/files` | user, admin | List files in a batch |

## Create Batch

### Request
```http
POST /api/v1/batch
Authorization: Bearer <token>
Content-Type: application/json

{
  "description": "January 2026 reconciliation"  // optional
}
```

### Response (201)
```json
{
  "batch_id": "20260124_143052_a1b2c3d4",
  "batch_db_id": 15,
  "status": "pending",
  "description": "January 2026 reconciliation",
  "created_by": "john.doe",
  "created_at": "2026-01-24T14:30:52",
  "message": "Batch created successfully"
}
```

### Error: User has pending batch (400)
```json
{
  "detail": "You already have an open batch: 20260123_100000_abc12345. Close it before creating a new one."
}
```

### What happens on creation:
1. Validates user has no pending batch
2. Generates unique `batch_id` (format: `YYYYMMDD_HHMMSS_<uuid8>`)
3. Persists batch record to database
4. Creates storage directory:
   - **Development**: `uploads/{batch_id}/`
   - **Production**: GCS bucket path `{batch_id}/`

## Close Batch

### Request
```http
POST /api/v1/batch/{batch_id}/close
Authorization: Bearer <token>
```

### Response (200)
```json
{
  "batch_id": "20260124_143052_a1b2c3d4",
  "status": "completed",
  "closed_at": "2026-01-24T18:45:00+00:00",
  "message": "Batch closed successfully"
}
```

### Validation Rules:
- Only the batch creator can close it
- All transactions tagged to the batch must be reconciled
- Batch must be in `pending` status

### Error: Unreconciled transactions (400)
```json
{
  "detail": "Cannot close batch: 5 unreconciled transaction(s) remain. Reconcile all transactions first."
}
```

## Delete Request (Maker-Checker Workflow)

### Step 1: User initiates delete request
```http
POST /api/v1/batch/{batch_id}/delete-request
Authorization: Bearer <token>
Content-Type: application/json

{
  "reason": "Duplicate batch created by mistake"  // optional
}
```

### Response (201)
```json
{
  "id": 1,
  "batch_id": "20260124_143052_a1b2c3d4",
  "status": "pending",
  "reason": "Duplicate batch created by mistake",
  "requested_by": "john.doe",
  "created_at": "2026-01-24T19:00:00",
  "message": "Delete request submitted. Awaiting admin approval."
}
```

### Step 2: Admin reviews the request
```http
POST /api/v1/batch/delete-requests/{request_id}/review
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "approved": true
}
```

### Response (200) - Approved
```json
{
  "request_id": 1,
  "action": "approved",
  "batch_id": "20260124_143052_a1b2c3d4",
  "transactions_deleted": 150,
  "files_deleted": 4,
  "file_records_deleted": 4
}
```

### Cascade Deletion (on approval):
1. Delete all transactions tagged to the batch
2. Delete all file records from the database
3. Delete the storage directory and all files within it
4. Delete the batch record itself

### Response (200) - Rejected
```json
{
  "request_id": 1,
  "action": "rejected",
  "batch_id": "20260124_143052_a1b2c3d4",
  "rejection_reason": "Batch contains important records"
}
```

## Storage Configuration

| Environment | Backend | Directory |
|-------------|---------|-----------|
| Development | Local filesystem | `uploads/{batch_id}/` |
| Production | Google Cloud Storage | `{GCS_BUCKET}/{batch_id}/` |

Controlled by environment variables:
- `STORAGE_BACKEND`: `local` (default) or `gcs`
- `LOCAL_UPLOADS_PATH`: Local directory path (default: `uploads`)
- `GCS_BUCKET`: GCS bucket name for production

## Database Schema

### `batches` table

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INT (PK) | No | Auto-increment primary key |
| batch_id | VARCHAR(100) | No | Unique batch identifier |
| status | VARCHAR(20) | No | pending or completed |
| description | VARCHAR(500) | Yes | Optional description |
| created_by_id | INT (FK → users.id) | No | Creator user ID |
| created_at | DATETIME | No | Creation timestamp |
| closed_at | DATETIME | Yes | Closure timestamp |

### `batch_delete_requests` table

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INT (PK) | No | Auto-increment primary key |
| batch_id | VARCHAR(100) (FK) | No | Target batch |
| status | VARCHAR(20) | No | pending, approved, or rejected |
| reason | VARCHAR(500) | Yes | Reason for deletion |
| requested_by_id | INT (FK → users.id) | No | Requesting user |
| reviewed_by_id | INT (FK → users.id) | Yes | Reviewing admin |
| reviewed_at | DATETIME | Yes | Review timestamp |
| rejection_reason | VARCHAR(500) | Yes | Reason for rejection |
| created_at | DATETIME | No | Request timestamp |

## Frontend UI

### Batches List Page
- **Create Batch** button with confirmation modal
- Table columns: Batch ID, Status, Created By, Files, Created At, Closed At, Actions
- **Close** button: Visible only to the batch creator on pending batches
- **Request Delete** button: Available to all users (submits for admin approval)
- Status filter: All, Pending, Completed
- Pagination controls

### Batch Detail Page
- Batch info card with metadata
- Quick Actions (Upload Files, Run Reconciliation when pending; Download Report when completed)
- Uploaded files table
- Workflow progress indicator (Create → Upload → Reconcile → Close)

## Error Handling

All batch operations return appropriate HTTP status codes:
- `201`: Batch/request created successfully
- `400`: Validation error (pending batch exists, unreconciled transactions, etc.)
- `404`: Batch not found
- `500`: Internal server error (logged with full context)

Errors are logged with structured context using the application logger:
- Development: Full stack traces with DEBUG level
- Production: ERROR level only, no sensitive data exposed
