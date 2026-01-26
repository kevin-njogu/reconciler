# Gateway Operations Documentation

This document provides comprehensive documentation for the Gateway Configuration CRUD (Create, Read, Update, Delete) operations in the Payment Gateway Reconciliation System.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Maker-Checker Workflow](#maker-checker-workflow)
4. [Backend Implementation](#backend-implementation)
   - [API Endpoints](#api-endpoints)
   - [Database Models](#database-models)
   - [Pydantic Models](#pydantic-models)
   - [Configuration Module](#configuration-module)
5. [Frontend Implementation](#frontend-implementation)
   - [API Service Layer](#api-service-layer)
   - [User Interface (GatewaysPage)](#user-interface-gatewayspage)
   - [Admin Interface (GatewayApprovalPage)](#admin-interface-gatewayapprovalpage)
6. [Role-Based Access Control](#role-based-access-control)
7. [Data Flow Examples](#data-flow-examples)

---

## Overview

The gateway operations module manages payment gateway configurations used for reconciliation. Instead of direct CRUD operations, the system implements a **maker-checker workflow** where:

- **Users** (maker) submit change requests for gateway modifications
- **Admins** (checker) review and approve/reject these requests
- Changes are only applied after admin approval

This ensures audit trail, accountability, and prevents unauthorized modifications to critical gateway configurations.

### Key Design Principles

1. **No Direct CRUD**: Users cannot directly create/update/delete gateways
2. **Change Request Pattern**: All modifications go through an approval workflow
3. **Soft Delete by Default**: Deactivation preserves history; permanent delete available for inactive gateways
4. **Database as Source of Truth**: Gateway configurations stored in DB, not hardcoded
5. **Immediate Application**: Approved changes apply immediately
6. **Role Separation**: Clear separation between requesters (users) and approvers (admins)
7. **Super Admin Exclusion**: Super admins are blocked from all gateway operations to maintain maker-checker integrity

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                           │
├─────────────────────────────────────────────────────────────────┤
│  GatewaysPage.tsx          │  GatewayApprovalPage.tsx           │
│  (User Interface)          │  (Admin Interface)                 │
│  - View gateways           │  - View pending requests           │
│  - Submit change requests  │  - Approve/reject requests         │
│  - View own requests       │  - View all requests history       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API Service Layer                           │
│                   frontend/src/api/gateways.ts                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Backend API Layer                           │
│               app/controller/gateway_config.py                  │
├─────────────────────────────────────────────────────────────────┤
│  READ Endpoints        │  Change Request      │  Approval       │
│  - GET /               │  - POST /change-req  │  - GET /pending │
│  - GET /info           │  - GET /my           │  - POST /review │
│  - GET /{name}         │  - GET /{id}         │  - GET /all     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Business Logic Layer                          │
│                   app/config/gateways.py                        │
│  - get_gateways_from_db()  - seed_default_gateways()           │
│  - get_gateway_from_db()   - get_gateways_info()               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Database Layer                             │
│               app/sqlModels/gatewayEntities.py                  │
├─────────────────────────────────────────────────────────────────┤
│  gateway_configs table     │  gateway_change_requests table     │
│  - id, name, gateway_type  │  - id, request_type, status        │
│  - display_name            │  - gateway_id, gateway_name        │
│  - country, currency       │  - proposed_changes                │
│  - date_format             │  - requested_by_id, reviewed_by_id │
│  - charge_keywords         │                                    │
│  - is_active               │                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Maker-Checker Workflow

### Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           USER (Maker)                                   │
├──────────────────────────────────────────────────────────────────────────┤
│  1. View available gateways                                              │
│     GET /api/v1/gateway-config/                                          │
│                                                                          │
│  2. Submit change request                                                │
│     POST /api/v1/gateway-config/change-request                           │
│     - System validates: no pending request for same gateway              │
│     - Creates record with status = PENDING                               │
│                                                                          │
│  3. View own requests                                                    │
│     GET /api/v1/gateway-config/change-requests/my                        │
│     - Can see pending/approved/rejected status                           │
│     - Sees approval/rejection details                                    │
│                                                                          │
│  4. Wait for admin approval...                                           │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          ADMIN (Checker)                                 │
├──────────────────────────────────────────────────────────────────────────┤
│  1. View pending requests                                                │
│     GET /api/v1/gateway-config/change-requests/pending                   │
│     - Sees all pending requests ordered by creation time                 │
│                                                                          │
│  2. Review request details                                               │
│     - Sees proposed changes                                              │
│     - Sees requester info                                                │
│                                                                          │
│  3a. APPROVE:                                                            │
│      POST /api/v1/gateway-config/change-requests/{id}/review             │
│      { "approved": true }                                                │
│      - _apply_gateway_change() called immediately                        │
│      - Gateway created/updated/deactivated/activated in DB               │
│      - Request status → APPROVED                                         │
│                                                                          │
│  3b. REJECT:                                                             │
│      POST /api/v1/gateway-config/change-requests/{id}/review             │
│      { "approved": false, "rejection_reason": "..." }                    │
│      - Request status → REJECTED                                         │
│      - Gateway NOT modified                                              │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                             RESULT                                       │
├──────────────────────────────────────────────────────────────────────────┤
│  - Complete audit trail: who requested, when, what changes,              │
│    who approved/rejected, when, why (if rejected)                        │
│  - All changes require admin approval                                    │
│  - Soft delete by default (is_active=false)                              │
│  - Permanent delete available for inactive gateways                      │
└──────────────────────────────────────────────────────────────────────────┘
```

### Change Request Types

| Type | Description | Proposed Changes Required |
|------|-------------|---------------------------|
| `create` | Create a new gateway | `gateway_type`, `display_name`, `country`, `currency`, `date_format`, `charge_keywords` (optional) |
| `update` | Update existing gateway | Any of: `display_name`, `country`, `currency`, `date_format`, `charge_keywords` |
| `delete` | Deactivate a gateway | None (soft delete) |
| `activate` | Reactivate a deactivated gateway | None |
| `permanent_delete` | Permanently remove an inactive gateway | None (hard delete, requires gateway to be inactive first) |

---

## Backend Implementation

### API Endpoints

**Base URL:** `/api/v1/gateway-config`

#### Read Endpoints

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| GET | `/` | List all gateways | Users, Admins |
| GET | `/options` | Get dropdown options (countries, currencies, date formats) | Users, Admins |
| GET | `/info` | Comprehensive gateway information | Users, Admins |
| GET | `/{gateway_name}` | Get specific gateway | Users, Admins |
| GET | `/upload-names/{gateway_name}` | Get upload names for a gateway | Users, Admins |

##### GET `/`

List all gateway configurations.

**Query Parameters:**
- `gateway_type` (optional): Filter by `external` or `internal`
- `include_inactive` (optional): Include deactivated gateways (default: false)

**Response:** `List[GatewayResponse]`

```json
[
  {
    "id": 1,
    "name": "equity",
    "gateway_type": "external",
    "display_name": "Equity Bank",
    "country": "KE",
    "currency": "KES",
    "date_format": "YYYY-MM-DD",
    "charge_keywords": ["charge", "fee", "commission", "levy"],
    "is_active": true,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

##### GET `/options`

Get dropdown options for gateway configuration forms.

**Response:** `GatewayOptionsResponse`

```json
{
  "countries": [
    { "code": "KE", "name": "Kenya" },
    { "code": "UG", "name": "Uganda" },
    { "code": "TZ", "name": "Tanzania" }
  ],
  "currencies": [
    { "code": "KES", "name": "Kenyan Shilling" },
    { "code": "USD", "name": "US Dollar" },
    { "code": "UGX", "name": "Ugandan Shilling" }
  ],
  "date_formats": [
    { "format": "YYYY-MM-DD", "example": "2024-01-15" },
    { "format": "DD/MM/YYYY", "example": "15/01/2024" },
    { "format": "MM/DD/YYYY", "example": "01/15/2024" }
  ]
}
```

##### GET `/info`

Get comprehensive gateway information for reconciliation.

**Response:**

```json
{
  "external_gateways": ["equity", "kcb", "mpesa"],
  "internal_gateways": ["workpay"],
  "upload_gateways": ["equity", "kcb", "mpesa", "workpay_equity", "workpay_kcb", "workpay_mpesa"],
  "charge_keywords": {
    "equity": ["CHARGE", "FEE", "COMMISSION", "LEVY"],
    "kcb": ["CHARGE", "FEE", "COMMISSION"],
    "mpesa": ["CHARGE", "FEE", "TRANSACTION COST"]
  },
  "gateway_configs": { ... }
}
```

##### GET `/{gateway_name}`

Get a specific gateway configuration.

**Response:** `GatewayResponse`

##### GET `/upload-names/{gateway_name}`

Get upload gateway names for an external gateway.

**Response:**

```json
{
  "gateway": "equity",
  "external_upload_name": "equity",
  "internal_upload_names": ["workpay_equity"]
}
```

---

#### Change Request Endpoints (User)

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| POST | `/change-request` | Submit a change request | Users only |
| GET | `/change-requests/my` | Get user's own requests | Users only |
| GET | `/change-requests/{request_id}` | Get specific request | Users (own), Admins (all) |

##### POST `/change-request`

Submit a gateway change request.

**Request Body:** `GatewayChangeRequestCreate`

```json
{
  "request_type": "create",
  "gateway_name": "coop",
  "proposed_changes": {
    "gateway_type": "external",
    "display_name": "Co-operative Bank",
    "country": "KE",
    "currency": "KES",
    "date_format": "YYYY-MM-DD",
    "charge_keywords": ["charge", "fee", "commission"]
  }
}
```

**Validation Rules:**
- No existing pending request for the same gateway
- For CREATE: `gateway_type`, `display_name`, `country`, `currency` required in `proposed_changes`
- For CREATE: `gateway_name` and `display_name` must be unique (not exist in database)
- For UPDATE/DELETE/ACTIVATE/PERMANENT_DELETE: Gateway must exist
- For UPDATE: `display_name` must be unique if changed
- For DELETE: Gateway must be active
- For ACTIVATE: Gateway must be inactive
- For PERMANENT_DELETE: Gateway must be inactive

**Response:** `GatewayChangeRequestResponse`

##### GET `/change-requests/my`

Get current user's change requests.

**Query Parameters:**
- `status` (optional): Filter by `pending`, `approved`, or `rejected`

**Response:** `GatewayChangeRequestListResponse`

```json
{
  "count": 3,
  "requests": [
    {
      "id": 1,
      "request_type": "create",
      "status": "pending",
      "gateway_id": null,
      "gateway_name": "coop",
      "proposed_changes": { ... },
      "requested_by_id": 5,
      "requested_by_name": "John Doe",
      "created_at": "2024-01-20T14:00:00Z",
      "reviewed_by_id": null,
      "reviewed_by_name": null,
      "reviewed_at": null,
      "rejection_reason": null
    }
  ]
}
```

---

#### Approval Endpoints (Admin)

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| GET | `/change-requests/pending` | Get pending requests | Admins only |
| GET | `/change-requests/all` | Get all requests | Admins only |
| POST | `/change-requests/{request_id}/review` | Approve/reject request | Admins only |

##### GET `/change-requests/pending`

Get all pending change requests for review.

**Response:** `GatewayChangeRequestListResponse` (ordered by creation time)

##### GET `/change-requests/all`

Get all change requests with optional filtering.

**Query Parameters:**
- `status` (optional): Filter by `pending`, `approved`, or `rejected`

**Response:** `GatewayChangeRequestListResponse`

##### POST `/change-requests/{request_id}/review`

Approve or reject a change request.

**Request Body:** `GatewayChangeRequestReview`

```json
// Approve
{
  "approved": true
}

// Reject
{
  "approved": false,
  "rejection_reason": "Gateway name conflicts with existing naming convention"
}
```

**Business Logic on Approval:**

The `_apply_gateway_change()` function is called immediately:

| Request Type | Action |
|--------------|--------|
| CREATE | Creates new `GatewayConfig` with `is_active=True` |
| UPDATE | Updates gateway's `display_name`, `country`, `currency`, `date_format`, `charge_keywords` |
| DELETE | Sets `is_active=False` (soft delete) |
| ACTIVATE | Sets `is_active=True` |
| PERMANENT_DELETE | Removes gateway record from database (hard delete, clears FK references first) |

**Response:** Updated `GatewayChangeRequestResponse`

---

#### Utility Endpoints

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| POST | `/seed-defaults` | Seed default gateways to DB | Admins only |

##### POST `/seed-defaults`

Seeds default gateways (equity, kcb, mpesa, workpay) if they don't exist.

**Response:**

```json
{
  "message": "Default gateways seeded successfully",
  "seeded_count": 4
}
```

---

### Database Models

**Location:** `app/sqlModels/gatewayEntities.py`

#### GatewayConfig

Stores gateway configurations.

```python
class GatewayConfig(Base):
    __tablename__ = "gateway_configs"

    id: int                    # Primary key
    name: str                  # Unique gateway identifier (e.g., "equity")
    gateway_type: str          # "external" or "internal"
    display_name: str          # Human-readable name (e.g., "Equity Bank")
    country: str               # ISO 3166-1 alpha-2 code (e.g., "KE", "UG")
    currency: str              # ISO 4217 code (e.g., "KES", "USD")
    date_format: str           # Expected date format (default: "YYYY-MM-DD")
    charge_keywords: list      # JSON array of charge keywords (lowercase)
    is_active: bool            # Soft delete flag (default: True)
    created_at: datetime       # Creation timestamp
    updated_at: datetime       # Last update timestamp
```

**Supported Countries:**
- KE (Kenya), UG (Uganda), TZ (Tanzania), RW (Rwanda)
- NG (Nigeria), GH (Ghana), ZA (South Africa)

**Supported Currencies:**
- KES, USD, UGX, TZS, RWF, NGN, GHS, ZAR

**Supported Date Formats:**
- YYYY-MM-DD (default), DD/MM/YYYY, MM/DD/YYYY, DD-MM-YYYY

**Indexes:**
- `ix_gateway_configs_name` (unique)
- `ix_gateway_configs_type`

#### GatewayChangeRequest

Stores change request records for audit trail.

```python
class GatewayChangeRequest(Base):
    __tablename__ = "gateway_change_requests"

    id: int                    # Primary key
    request_type: str          # "create", "update", "delete", "activate", "permanent_delete"
    status: str                # "pending", "approved", "rejected"
    gateway_id: int            # FK to GatewayConfig (nullable for CREATE, cleared on PERMANENT_DELETE)
    gateway_name: str          # Gateway identifier
    proposed_changes: dict     # JSON object with proposed modifications
    requested_by_id: int       # FK to User (requester)
    created_at: datetime       # Request submission time
    reviewed_by_id: int        # FK to User (reviewer, nullable)
    reviewed_at: datetime      # Review timestamp (nullable)
    rejection_reason: str      # Reason if rejected (nullable)
```

**Relationships:**
- `gateway`: ForeignKey to `GatewayConfig`
- `requested_by`: ForeignKey to `User`
- `reviewed_by`: ForeignKey to `User`

**Indexes:**
- `ix_gateway_change_status` (for filtering pending)
- `ix_gateway_change_requested_by` (for user's requests)
- `ix_gateway_change_created` (for sorting)

---

### Pydantic Models

**Location:** `app/pydanticModels/gatewayModels.py`

#### Request Models

```python
class GatewayChangeRequestCreate(BaseModel):
    request_type: Literal["create", "update", "delete", "activate", "permanent_delete"]
    gateway_name: str  # 2-50 chars, lowercase, alphanumeric + underscores
    proposed_changes: dict

class GatewayChangeRequestReview(BaseModel):
    approved: bool
    rejection_reason: Optional[str]  # Required if approved=False
```

#### Response Models

```python
class GatewayResponse(BaseModel):
    id: int
    name: str
    gateway_type: str
    display_name: str
    country: str
    currency: str
    date_format: str
    charge_keywords: List[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

class GatewayOptionsResponse(BaseModel):
    countries: List[CountryOption]   # {code, name}
    currencies: List[CurrencyOption] # {code, name}
    date_formats: List[DateFormatOption] # {format, example}

class GatewayChangeRequestResponse(BaseModel):
    id: int
    request_type: str
    status: str
    gateway_id: Optional[int]
    gateway_name: str
    proposed_changes: dict
    requested_by_id: int
    requested_by_name: Optional[str]  # Denormalized for display
    created_at: datetime
    reviewed_by_id: Optional[int]
    reviewed_by_name: Optional[str]   # Denormalized for display
    reviewed_at: Optional[datetime]
    rejection_reason: Optional[str]

class GatewayChangeRequestListResponse(BaseModel):
    count: int
    requests: List[GatewayChangeRequestResponse]
```

---

### Configuration Module

**Location:** `app/config/gateways.py`

#### Default Gateways

**Note:** Charge keywords are stored in lowercase for case-insensitive matching during reconciliation.

```python
DEFAULT_GATEWAYS = {
    "equity": {
        "type": "external",
        "display_name": "Equity Bank",
        "country": "KE",
        "currency": "KES",
        "date_format": "YYYY-MM-DD",
        "charge_keywords": ["charge", "fee", "commission", "levy"],
    },
    "kcb": {
        "type": "external",
        "display_name": "KCB Bank",
        "country": "KE",
        "currency": "KES",
        "date_format": "YYYY-MM-DD",
        "charge_keywords": ["charge", "fee", "commission"],
    },
    "mpesa": {
        "type": "external",
        "display_name": "M-Pesa",
        "country": "KE",
        "currency": "KES",
        "date_format": "YYYY-MM-DD",
        "charge_keywords": ["charge", "fee", "transaction cost"],
    },
    "workpay": {
        "type": "internal",
        "display_name": "Workpay",
        "country": "KE",
        "currency": "KES",
        "date_format": "YYYY-MM-DD",
        "charge_keywords": [],
    },
}
```

#### Key Functions

| Function | Description |
|----------|-------------|
| `get_gateways_from_db(db_session)` | Load active gateways from database |
| `get_gateway_from_db(db_session, name)` | Get specific gateway by name |
| `seed_default_gateways(db_session)` | Seed default gateways if they don't exist |
| `get_all_gateways(db_session)` | Get gateways from DB, fallback to defaults |
| `get_external_gateways()` | Get list of external gateway names |
| `get_internal_gateways()` | Get list of internal gateway names |
| `get_all_upload_gateways()` | Get all valid upload gateway names |
| `get_charge_keywords(gateway)` | Get charge keywords for a gateway |
| `get_gateways_info(db_session)` | Comprehensive gateway info for API |
| `get_gateway_options()` | Get dropdown options (countries, currencies, date formats) |

---

## Frontend Implementation

### API Service Layer

**Location:** `frontend/src/api/gateways.ts`

```typescript
export const gatewaysApi = {
  // Gateway options (for dropdowns)
  getOptions(): Promise<GatewayOptions>,

  // Gateway listing
  getGateways(): Promise<GatewayListItem[]>,
  list(params?): Promise<GatewayConfig[]>,
  getInfo(): Promise<GatewayInfo>,
  getByName(name: string): Promise<GatewayConfig>,

  // Change request workflow
  createChangeRequest(data: GatewayChangeRequestCreate): Promise<GatewayChangeRequest>,
  getMyChangeRequests(status?: string): Promise<GatewayChangeRequestListResponse>,
  getChangeRequest(id: number): Promise<GatewayChangeRequest>,
  getPendingChangeRequests(): Promise<GatewayChangeRequestListResponse>,
  getAllChangeRequests(status?: string): Promise<GatewayChangeRequestListResponse>,
  reviewChangeRequest(id: number, review: GatewayChangeRequestReview): Promise<GatewayChangeRequest>,

  // Utilities
  getUploadNames(name: string): Promise<UploadNamesResponse>,
  seedDefaults(): Promise<SeedDefaultsResponse>,
}
```

---

### User Interface (GatewaysPage)

**Location:** `frontend/src/features/gateways/GatewaysPage.tsx`

The user-facing gateway management interface.

#### Features

1. **Gateway List View**
   - Side-by-side tables for External (Banks) and Internal (Workpay) gateways
   - Columns: Gateway (name + display name), Location (country + currency), Status (Active/Inactive)
   - Pagination for each table (5 items per page)

2. **Add Gateway** (button at top)
   - Modal form with fields:
     - Gateway Name (validated: lowercase, alphanumeric + underscores)
     - Gateway Type (external/internal dropdown)
     - Display Name
     - Country (dropdown from supported countries)
     - Currency (dropdown from supported currencies)
     - Date Format (dropdown with examples)
     - Charge Keywords (comma-separated, auto-lowercased)
   - Required fields marked with red asterisk (*)
   - Submits `POST /change-request` with `request_type: "create"`

3. **Edit Gateway**
   - Modal pre-populated with current values
   - Editable fields: Display Name, Country, Currency, Date Format, Charge Keywords
   - Submits `POST /change-request` with `request_type: "update"`

4. **Dropdown Actions (per gateway)**
   - **"Edit"** → Opens edit modal
   - For active gateways:
     - **"Deactivate"** → Submits delete request (soft delete)
   - For inactive gateways:
     - **"Activate"** → Submits activate request
     - **"Delete"** → Opens confirmation modal for permanent deletion

5. **Delete Confirmation Modal**
   - Appears when requesting permanent delete
   - Shows warning: "This action cannot be undone once approved by an admin"
   - Displays gateway name being deleted
   - Buttons: "No, Cancel" and "Yes, Delete"

6. **My Requests Panel**
   - Shows count of pending requests in header button
   - Amber banner when pending requests exist
   - List view of all user's requests with:
     - Request type and gateway name
     - Status badge (Pending/Approved/Rejected)
     - Submission timestamp
     - Approver name (if approved)
     - Rejection reason (if rejected)

#### State Management

- Uses `@tanstack/react-query` for data fetching and caching
- Query keys: `gateway-configs`, `my-gateway-requests`
- Mutations invalidate relevant queries on success
- Toast notifications for success/error feedback

---

### Admin Interface (GatewayApprovalPage)

**Location:** `frontend/src/features/gateways/GatewayApprovalPage.tsx`

The admin interface for reviewing and approving gateway change requests.

#### Features

1. **Pending Requests Dashboard**
   - Summary count of pending requests
   - Filter tabs: Pending, Approved, Rejected, All

2. **Change Requests Table**
   - Columns:
     - Request Type (with icon)
     - Gateway Name
     - Proposed Changes (formatted display)
     - Requester
     - Status
     - Actions

3. **Request Type Icons**
   | Type | Icon | Color |
   |------|------|-------|
   | Create | Plus | Green |
   | Update | Edit2 | Blue |
   | Delete | Trash2 | Red |
   | Activate | Power | Purple |
   | Permanent Delete | Trash2 | Red |

4. **Proposed Changes Display**
   - CREATE: Shows type, display_name, country, currency, date_format, charge_keywords
   - UPDATE: Shows new values being set
   - DELETE: "Gateway will be deactivated"
   - ACTIVATE: "Gateway will be reactivated"
   - PERMANENT_DELETE: "Gateway will be permanently removed from the database"

5. **Review Modal**
   - Read-only section showing full request details
   - Requester name and submission time
   - Action buttons:
     - **Approve**: Warning message about immediate application
     - **Reject**: Requires rejection reason textarea

6. **Processed Requests View**
   - Shows reviewer name and review timestamp
   - Shows rejection reason for rejected requests

#### State Management

- Queries change requests with status filter
- `staleTime: 0` for always-fresh data
- On review completion, invalidates:
  - `gateway-change-requests`
  - `gateway-configs`
  - `gateways`

---

## Role-Based Access Control

### User Roles

| Role | Description | Gateway Permissions |
|------|-------------|---------------------|
| `super_admin` | System administrator | **Blocked** from gateway management |
| `admin` | Administrator | Can approve/reject change requests |
| `user` | Regular user | Can submit change requests |

### Endpoint Access Matrix

| Endpoint | User | Admin | Super Admin |
|----------|:----:|:-----:|:-----------:|
| GET `/` | ✅ | ✅ | ❌ |
| GET `/options` | ✅ | ✅ | ❌ |
| GET `/info` | ✅ | ✅ | ❌ |
| GET `/{name}` | ✅ | ✅ | ❌ |
| GET `/upload-names/{name}` | ✅ | ✅ | ❌ |
| POST `/change-request` | ✅ | ❌ | ❌ |
| GET `/change-requests/my` | ✅ | ❌ | ❌ |
| GET `/change-requests/{id}` | Own only | All | ❌ |
| GET `/change-requests/pending` | ❌ | ✅ | ❌ |
| GET `/change-requests/all` | ❌ | ✅ | ❌ |
| POST `/change-requests/{id}/review` | ❌ | ✅ | ❌ |
| POST `/seed-defaults` | ❌ | ✅ | ❌ |

### Authentication Dependencies

**Location:** `app/auth/dependencies.py`

- `require_active_user`: Basic authentication check
- `require_user_role`: Users only (blocks admins and super_admin)
- `require_admin_only`: Admins only (blocks users and super_admin)

---

## Data Flow Examples

### Example 1: Creating a New Gateway

**User submits request:**

```bash
POST /api/v1/gateway-config/change-request
Authorization: Bearer <user_token>

{
  "request_type": "create",
  "gateway_name": "coop",
  "proposed_changes": {
    "gateway_type": "external",
    "display_name": "Co-operative Bank",
    "country": "KE",
    "currency": "KES",
    "date_format": "YYYY-MM-DD",
    "charge_keywords": ["charge", "fee", "commission"]
  }
}
```

**Admin approves:**

```bash
POST /api/v1/gateway-config/change-requests/1/review
Authorization: Bearer <admin_token>

{
  "approved": true
}
```

**Result:**
- New gateway `coop` created in `gateway_configs` table
- Change request status updated to `approved`
- Audit trail preserved with requester and approver info

### Example 2: Updating Gateway Configuration

**User submits request:**

```bash
POST /api/v1/gateway-config/change-request
Authorization: Bearer <user_token>

{
  "request_type": "update",
  "gateway_name": "equity",
  "proposed_changes": {
    "charge_keywords": ["charge", "fee", "commission", "levy", "vat"],
    "date_format": "DD/MM/YYYY"
  }
}
```

### Example 3: Deactivating a Gateway

**User submits request:**

```bash
POST /api/v1/gateway-config/change-request
Authorization: Bearer <user_token>

{
  "request_type": "delete",
  "gateway_name": "old_bank",
  "proposed_changes": {}
}
```

**Admin rejects:**

```bash
POST /api/v1/gateway-config/change-requests/3/review
Authorization: Bearer <admin_token>

{
  "approved": false,
  "rejection_reason": "There are pending reconciliations using this gateway. Complete them first."
}
```

### Example 4: Permanently Deleting a Gateway

**Prerequisites:**
- Gateway must first be deactivated (request_type: "delete" approved)

**User submits permanent delete request:**

```bash
POST /api/v1/gateway-config/change-request
Authorization: Bearer <user_token>

{
  "request_type": "permanent_delete",
  "gateway_name": "old_bank",
  "proposed_changes": {}
}
```

**Admin approves:**

```bash
POST /api/v1/gateway-config/change-requests/4/review
Authorization: Bearer <admin_token>

{
  "approved": true
}
```

**Result:**
- All foreign key references in `gateway_change_requests` table are cleared (gateway_id set to NULL)
- Gateway record permanently removed from `gateway_configs` table
- Change request preserved for audit trail (with gateway_id = NULL)

---

## File Locations Summary

### Backend

| File | Purpose |
|------|---------|
| `app/controller/gateway_config.py` | API endpoint definitions |
| `app/config/gateways.py` | Gateway configuration helpers |
| `app/sqlModels/gatewayEntities.py` | Database models |
| `app/pydanticModels/gatewayModels.py` | Request/response schemas |
| `app/auth/dependencies.py` | RBAC decorators |

### Frontend

| File | Purpose |
|------|---------|
| `frontend/src/api/gateways.ts` | API service layer |
| `frontend/src/features/gateways/GatewaysPage.tsx` | User interface |
| `frontend/src/features/gateways/GatewayApprovalPage.tsx` | Admin interface |
| `frontend/src/types/index.ts` | TypeScript type definitions |
