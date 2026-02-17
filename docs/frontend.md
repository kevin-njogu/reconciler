# Frontend Documentation

React + TypeScript frontend for the Payment Gateway Reconciliation System.

## Table of Contents

1. [Tech Stack](#tech-stack)
2. [Directory Structure](#directory-structure)
3. [Application Entry & Routing](#application-entry--routing)
4. [Authentication & State Management](#authentication--state-management)
5. [API Client](#api-client)
6. [API Modules](#api-modules)
7. [TypeScript Types](#typescript-types)
8. [Utility Library](#utility-library)
9. [UI Components](#ui-components)
10. [Layout Components](#layout-components)
11. [Feature Pages](#feature-pages)
12. [Hooks](#hooks)
13. [Role-Based Access Control](#role-based-access-control)

---

## Tech Stack

| Library | Version | Purpose |
|---------|---------|---------|
| React | 19 | UI framework |
| TypeScript | 5+ | Type safety |
| Vite | 5+ | Build tool and dev server |
| Tailwind CSS | 4 | Utility-first styling |
| React Router | v6 | Client-side routing |
| TanStack React Query | v5 | Server state management |
| Zustand | 4+ | Client state (auth) |
| Axios | 1+ | HTTP client |
| React Hook Form | 7+ | Form state management |
| Zod | 3+ | Schema validation |
| Lucide React | — | Icons |

---

## Directory Structure

```
frontend/src/
├── main.tsx                    # React app entry point
├── App.tsx                     # Router configuration + React Query setup
├── index.css                   # Global styles (Tailwind base)
├── api/                        # API client + endpoint modules
│   ├── index.ts                # Barrel export for all API modules
│   ├── client.ts               # Axios instance, token storage, interceptors
│   ├── auth.ts                 # Auth endpoints
│   ├── users.ts                # User management endpoints
│   ├── gateways.ts             # Gateway config endpoints
│   ├── runs.ts                 # Reconciliation run endpoints
│   ├── upload.ts               # File upload endpoints
│   ├── reconciliation.ts       # Reconciliation endpoints
│   ├── reports.ts              # Report download endpoints
│   ├── operations.ts           # Manual reconciliation endpoints
│   ├── dashboard.ts            # Dashboard statistics endpoints
│   └── transactions.ts         # Transaction browsing endpoints
├── types/
│   └── index.ts                # All TypeScript interfaces and types
├── stores/
│   ├── index.ts                # Barrel + helper hooks
│   └── authStore.ts            # Zustand auth store with persistence
├── hooks/
│   ├── index.ts                # Barrel export
│   └── useToast.tsx            # Toast notification store and hook
├── lib/
│   └── utils.ts                # Utility functions (cn, format*, color*, etc.)
├── components/
│   ├── ui/                     # Reusable UI primitives (21 components)
│   │   ├── index.ts
│   │   ├── Alert.tsx
│   │   ├── Badge.tsx
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── ErrorBoundary.tsx
│   │   ├── FileUpload.tsx
│   │   ├── Input.tsx
│   │   ├── Modal.tsx
│   │   ├── Pagination.tsx
│   │   ├── PasswordInput.tsx
│   │   ├── SearchableSelect.tsx
│   │   ├── Select.tsx
│   │   ├── Spinner.tsx
│   │   ├── Table.tsx
│   │   └── Toast.tsx
│   └── layout/                 # Application shell
│       ├── index.ts
│       ├── Layout.tsx
│       ├── Sidebar.tsx
│       ├── Header.tsx
│       └── ProtectedRoute.tsx
└── features/                   # Feature pages by domain
    ├── auth/
    │   ├── index.ts
    │   ├── LoginPage.tsx
    │   ├── ChangePasswordPage.tsx
    │   └── ForgotPasswordPage.tsx
    ├── dashboard/
    │   ├── index.ts
    │   └── DashboardPage.tsx
    ├── gateways/
    │   ├── index.ts
    │   ├── GatewaysPage.tsx
    │   └── GatewayApprovalPage.tsx
    ├── operations/
    │   ├── index.ts
    │   ├── OperationsPage.tsx
    │   ├── AuthorizationPage.tsx
    │   ├── SimpleSideBySideView.tsx
    │   ├── SideBySideTransactionView.tsx
    │   ├── SimpleAuthorizationView.tsx
    │   └── SideBySideAuthorizationView.tsx
    ├── reconcile/
    │   ├── index.ts
    │   └── ReconcilePage.tsx
    ├── reports/
    │   ├── index.ts
    │   └── ReportsPage.tsx
    ├── runs/
    │   ├── index.ts
    │   ├── RunsPage.tsx
    │   └── RunDetailPage.tsx
    ├── transactions/
    │   ├── index.ts
    │   └── TransactionsPage.tsx
    └── users/
        ├── index.ts
        └── UsersPage.tsx
```

---

## Application Entry & Routing

### `main.tsx`

Bootstraps React in strict mode. Imports global CSS.

### `App.tsx`

Configures the React Query client (stale time 0, always refetch on mount) and defines all routes.

**Route map:**

| Path | Component | Access |
|------|-----------|--------|
| `/login` | `LoginPage` | Public |
| `/forgot-password` | `ForgotPasswordPage` | Public |
| `/change-password` | `ChangePasswordPage` | Any authenticated user |
| `/` | `DashboardPage` | Any authenticated user |
| `/reconcile` | `ReconcilePage` | `user` role only |
| `/operations` | `OperationsPage` | `user` role only |
| `/gateways` | `GatewaysPage` | `user` role only |
| `/reconciliation-approvals` | `AuthorizationPage` | `admin` role only (strict) |
| `/gateway-approvals` | `GatewayApprovalPage` | `admin` role only (strict) |
| `/users` | `UsersPage` | `super_admin` only |
| `/transactions` | `TransactionsPage` | Any authenticated user |
| `/reports` | `ReportsPage` | Any authenticated user |
| `/runs` | `RunsPage` | Any authenticated user |
| `/runs/:runId` | `RunDetailPage` | Any authenticated user |
| `/upload` | Redirect → `/reconcile` | Legacy redirect |
| `/reconciliation` | Redirect → `/reconcile` | Legacy redirect |

---

## Authentication & State Management

### `stores/authStore.ts`

Zustand store with `localStorage` persistence. Tracks all auth state for the current session.

**State:**

| Field | Type | Description |
|-------|------|-------------|
| `user` | `User \| null` | Current authenticated user |
| `isAuthenticated` | `boolean` | Auth status |
| `mustChangePassword` | `boolean` | Forces redirect to change-password page |
| `isLoading` | `boolean` | True while validating session on startup |

**Actions:**

| Action | Description |
|--------|-------------|
| `login(email, password)` | Calls `/auth/login`, stores tokens, sets user state |
| `logout()` | Calls `/auth/logout`, clears all state and tokens |
| `checkAuth()` | Calls `/auth/me` to revalidate session on app load |
| `setUser(user)` | Direct user state update (used after profile changes) |
| `setMustChangePassword(value)` | Used to clear forced-change flag after completion |

### Helper Hooks (`stores/index.ts`)

Import these hooks in components instead of accessing the store directly:

```tsx
import { useUser, useIsAuthenticated, useIsAdmin, useIsSuperAdmin, useIsAdminOnly, useIsUserRole, useUserRole } from '@/stores';

const user = useUser();                // User | null
const isAuth = useIsAuthenticated();   // boolean
const isAdmin = useIsAdmin();          // admin OR super_admin
const isSuperAdmin = useIsSuperAdmin(); // super_admin only
const isAdminOnly = useIsAdminOnly();   // admin only (not super_admin)
const isUser = useIsUserRole();         // user only (makers)
const role = useUserRole();             // 'super_admin' | 'admin' | 'user' | null
```

---

## API Client

### `api/client.ts`

**Axios instance** configured with:
- Base URL: `/api/v1`
- Default `Content-Type: application/json`

**Token storage** (localStorage):

```ts
import { tokenStorage } from '@/api';

tokenStorage.getAccessToken()
tokenStorage.getRefreshToken()
tokenStorage.setTokens(access, refresh)
tokenStorage.setAccessToken(access)
tokenStorage.clearTokens()   // also redirects to /login
```

**Request interceptor**: Automatically attaches `Authorization: Bearer {token}` to every request.

**Response interceptor (token refresh)**:
- On 401, checks if the failing request was itself an auth endpoint (skips refresh to prevent loops)
- Queues all other failing requests while a single refresh attempt runs
- On refresh success: retries all queued requests with the new token
- On refresh failure: clears tokens and redirects to `/login`

**`getErrorMessage(error)`**: Extracts a human-readable string from Axios errors. Handles FastAPI's `detail` field (string or array), field-level validation errors, and generic messages.

---

## API Modules

All modules export a plain object of async functions. Import from the barrel:

```ts
import { authApi, usersApi, gatewaysApi, uploadApi, reconciliationApi, reportsApi, operationsApi, dashboardApi, transactionsApi, runsApi } from '@/api';
```

### `api/auth.ts`

```ts
authApi.login(data)                  // POST /auth/login
authApi.logout(refreshToken)         // POST /auth/logout
authApi.refresh(refreshToken)        // POST /auth/refresh
authApi.getCurrentUser()             // GET /auth/me
authApi.changePassword(data)         // POST /auth/change-password
authApi.forgotPassword(data)         // POST /auth/forgot-password
authApi.resetPassword(data)          // POST /auth/reset-password
```

### `api/users.ts`

```ts
usersApi.list(params)                // GET /users
usersApi.getById(userId)             // GET /users/{id}
usersApi.create(data)                // POST /users
usersApi.update(userId, data)        // PATCH /users/{id}
usersApi.block(userId)               // POST /users/{id}/block
usersApi.unblock(userId)             // POST /users/{id}/unblock
usersApi.deactivate(userId)          // POST /users/{id}/deactivate
usersApi.resetPassword(userId)       // POST /users/{id}/reset-password
```

### `api/gateways.ts`

```ts
gatewaysApi.list(includeInactive)                  // GET /gateway-config/
gatewaysApi.get(gatewayId)                         // GET /gateway-config/{id}
gatewaysApi.createChangeRequest(data)              // POST /gateway-config/change-request
gatewaysApi.getMyChangeRequests(status)            // GET /gateway-config/change-requests/my
gatewaysApi.getPendingChangeRequests(page, size)   // GET /gateway-config/change-requests/pending
gatewaysApi.getAllChangeRequests(status, page, size)// GET /gateway-config/change-requests/all
gatewaysApi.getChangeRequest(requestId)            // GET /gateway-config/change-requests/{id}
gatewaysApi.reviewChangeRequest(requestId, review) // POST /gateway-config/change-requests/{id}/review
```

### `api/upload.ts`

```ts
uploadApi.uploadFile(gateway, file, transform)  // POST /upload/file
uploadApi.deleteFile(filename, gateway)          // DELETE /upload/file
uploadApi.downloadFile(filename, gateway)        // GET /upload/file/download (blob)
uploadApi.listFiles(gateway)                     // GET /upload/files
uploadApi.downloadTemplate(format)              // GET /upload/template (blob)
uploadApi.getTemplateInfo()                     // GET /upload/template-info
uploadApi.validateFile(file)                    // POST /upload/validate
```

### `api/reconciliation.ts`

```ts
reconciliationApi.getReadyGateways()   // GET /reconcile/available-gateways
reconciliationApi.preview(gateway)     // POST /reconcile/preview
reconciliationApi.reconcile(gateway)   // POST /reconcile
```

### `api/operations.ts`

```ts
// User (maker) actions
operationsApi.getUnreconciled(gateway)               // GET /operations/unreconciled
operationsApi.manualReconcile(txId, type, note)      // POST /operations/manual-reconcile/{id}
operationsApi.manualReconcileBulk(txIds, type, note) // POST /operations/manual-reconcile-bulk

// Admin (checker) actions
operationsApi.getPendingAuthorization(gateway)       // GET /operations/pending-authorization
operationsApi.authorize(txId, action, note)          // POST /operations/authorize/{id}
operationsApi.authorizeBulk(txIds, action, note)     // POST /operations/authorize-bulk
```

### `api/reports.ts`

```ts
reportsApi.getAvailableGateways()                                          // GET /reports/available-gateways
reportsApi.getRuns(gateway, limit)                                         // GET /reports/runs
reportsApi.downloadReport(gateway, format, dateFrom, dateTo, runId)        // GET /reports/download (blob)
```

### `api/dashboard.ts`

```ts
dashboardApi.getStats()   // GET /dashboard/stats → DashboardStats
```

### `api/transactions.ts`

```ts
transactionsApi.list(filters)         // GET /transactions (paginated)
transactionsApi.getFilterOptions()    // GET /transactions/filters
transactionsApi.get(id)               // GET /transactions/{id}
```

### `api/runs.ts`

```ts
runsApi.list(params)        // GET /runs (paginated)
runsApi.getById(runId)      // GET /runs/{runId}
```

---

## TypeScript Types

All types are defined in `types/index.ts` and imported with `@/types`.

### Auth Types

```ts
type UserRole = 'super_admin' | 'admin' | 'user';
type UserStatus = 'active' | 'blocked' | 'deactivated';

interface User {
  id: number;
  username: string;
  email: string;
  role: UserRole;
  status: UserStatus;
  first_name: string;
  last_name: string;
  mobile?: string;
  must_change_password: boolean;
  created_at: string;
  last_login?: string;
}
```

### Transaction Types

```ts
type TransactionType = 'deposit' | 'debit' | 'charge' | 'payout' | 'refund';
type ReconciliationStatus = 'reconciled' | 'unreconciled';
type ReconciliationCategory = 'reconcilable' | 'auto_reconciled' | 'non_reconcilable';

interface Transaction {
  id: number;
  gateway: string;
  transaction_id: string;
  narrative: string;
  debit: number;
  credit: number;
  date: string;
  transaction_type: TransactionType;
  reconciliation_status: ReconciliationStatus;
  reconciliation_category: ReconciliationCategory;
  reconciliation_key: string;
  reconciliation_note?: string;
  run_id: string;
  source_file?: string;
  is_manual?: boolean;
  manual_recon_note?: string;
  authorization_status?: string;
}
```

### Gateway Types

```ts
type FileConfigType = 'external' | 'internal';
type ChangeRequestType = 'create' | 'update' | 'delete' | 'activate' | 'permanent_delete';
type ChangeRequestStatus = 'pending' | 'approved' | 'rejected';

interface GatewayFileConfig {
  id: number;
  name: string;
  display_name: string;
  config_type: FileConfigType;
  column_mapping: Record<string, string>;
  charge_keywords: string[];
  header_row_index: number;
  date_format?: string;
  is_active: boolean;
}

interface UnifiedGateway {
  id: number;
  display_name: string;
  is_active: boolean;
  external_config?: GatewayFileConfig;
  internal_config?: GatewayFileConfig;
}
```

---

## Utility Library

**`lib/utils.ts`** — all exports used throughout the app.

| Function | Description |
|----------|-------------|
| `cn(...inputs)` | Merge Tailwind classes with deduplication (`clsx` + `tailwind-merge`) |
| `formatDate(date)` | `Jan 1, 2025` (user's local timezone) |
| `formatDateTime(date)` | Date + time in user's local timezone |
| `formatDateTimeWithTimezone(date)` | Includes timezone abbreviation (e.g., `EAT`) |
| `formatCurrency(amount)` | `KES 1,234.56` |
| `formatNumber(num)` | `1,234` with locale-aware separators |
| `capitalizeFirst(str)` | Uppercases only the first character |
| `getStatusColor(status)` | Tailwind class string for a status value |
| `getRoleColor(role)` | Tailwind class string for a role value |
| `downloadFile(blob, filename)` | Triggers browser download of a blob |
| `formatBytes(bytes, decimals)` | `2.5 MB` human-readable size |

---

## UI Components

All components are exported from `components/ui/index.ts`. Import with:

```ts
import { Button, Card, Table, Alert, ... } from '@/components/ui';
```

### Button

```tsx
<Button variant="primary" | "secondary" | "danger" | "ghost" size="sm" | "md" | "lg" isLoading={false}>
  Label
</Button>
```

### Input / PasswordInput

```tsx
<Input label="Email" type="email" error="Required" />
<PasswordInput label="Password" />  // toggle show/hide built in
```

### Select / SearchableSelect

```tsx
<Select label="Gateway" options={[{value, label}]} value={val} onChange={handler} />
<SearchableSelect label="Run" options={opts} value={val} onChange={handler} />
```

### Card

```tsx
<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
    <CardDescription>Subtitle</CardDescription>
  </CardHeader>
  <CardContent>Body</CardContent>
  <CardFooter>Footer</CardFooter>
</Card>
```

### Badge

```tsx
<Badge variant="success" | "warning" | "error" | "info" | "neutral">
  Text
</Badge>

// Helper: maps status string to variant
const variant = getStatusBadgeVariant(transaction.reconciliation_status);
```

### Modal

```tsx
<Modal isOpen={open} onClose={close} title="Confirm Action">
  Modal content here
  <ModalFooter>
    <Button onClick={close}>Cancel</Button>
    <Button variant="primary" onClick={confirm}>Confirm</Button>
  </ModalFooter>
</Modal>
```

### Table

```tsx
<Table>
  <TableHeader>
    <TableRow>
      <TableHead>Column</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    {rows.map(row => (
      <TableRow key={row.id}>
        <TableCell>{row.value}</TableCell>
      </TableRow>
    ))}
    {rows.length === 0 && <TableEmpty colSpan={4} message="No data" />}
  </TableBody>
</Table>
```

### Alert

```tsx
<Alert variant="info" | "success" | "warning" | "error" title="Heading">
  Message body
</Alert>
```

### Loading States

```tsx
<Spinner />          // inline spinner
<Loading />          // spinner + "Loading..." text
<PageLoading />      // full-page centered spinner
```

### FileUpload

```tsx
<FileUpload onFileSelect={handleFile} accept=".xlsx,.csv" />
// Supports drag-and-drop + click-to-browse
```

### Pagination / CompactPagination

```tsx
<Pagination page={page} totalPages={10} onPageChange={setPage} />
<CompactPagination page={page} totalPages={10} onPageChange={setPage} />
```

### Toast

Toasts are managed by the `useToast` hook (see [Hooks](#hooks)). The `<ToastContainer />` is rendered once in `App.tsx`.

### ErrorBoundary

```tsx
<ErrorBoundary fallback={<p>Something went wrong</p>}>
  <MyComponent />
</ErrorBoundary>
```

---

## Layout Components

### `Layout.tsx`

The main authenticated shell. Renders:
- Fixed `Sidebar` on the left (256px)
- `Header` at the top
- `<Outlet />` for route content in the scrollable main area

### `Sidebar.tsx`

Vertical navigation list. Items filtered by user role:

| Nav Item | Icon | Visible To |
|----------|------|-----------|
| Dashboard | `LayoutDashboard` | All roles |
| Reconcile | `RefreshCw` | `user` only |
| Manual Recon | `GitMerge` | `user` only |
| Gateways | `Building2` | `user` only |
| Transactions | `List` | All roles |
| Reports | `FileText` | All roles |
| Reconciliation Approvals | `CheckSquare` | `admin` only |
| Gateway Approvals | `ShieldCheck` | `admin` only |
| Users | `Users` | `super_admin` only |

Active route is highlighted with a background and primary color via `NavLink`.

### `Header.tsx`

Sticky top bar (height 64px). Shows app name on the left. On the right:
- Current user avatar (circle with initials)
- Username and role badge
- Dropdown menu: **Change Password** / **Logout**

### `ProtectedRoute.tsx`

Wraps routes requiring specific access. Props:

| Prop | Type | Description |
|------|------|-------------|
| `requireAdmin` | boolean | Requires `admin` or `super_admin` |
| `requireSuperAdmin` | boolean | Requires `super_admin` |
| `requireAdminOnly` | boolean | Requires `admin` (not `super_admin`) |
| `requireUserRole` | boolean | Requires `user` role |

Redirect behaviour:
1. Loading → `<PageLoading />`
2. Not authenticated → `/login`
3. `mustChangePassword` (and not on `/change-password`) → `/change-password`
4. Role mismatch → `/` (dashboard)

---

## Feature Pages

### `features/auth/`

**`LoginPage`** — Email + password form. On success, stores tokens and navigates to dashboard (or previous route). Shows `Alert` for session-expired redirects.

**`ChangePasswordPage`** — Current + new + confirm password form validated with Zod. Used both for user-initiated changes and the forced first-login change. Auto-logs out after success.

**`ForgotPasswordPage`** — Two-step flow:
1. Enter email → receive reset token via email
2. Enter token + new password → redirected to login

---

### `features/dashboard/DashboardPage`

Fetches `dashboardApi.getStats()` on mount (stale time 0).

Displays:
- **Summary bar** (3 cards): Reconciliation rate, Pending approvals, Total unreconciled items
- **Gateway tiles**: One card per active gateway showing external debit count, internal payout count, unreconciled count, and a colour-coded match rate progress bar (green ≥ 90%, amber ≥ 70%, red < 70%)

---

### `features/reconcile/ReconcilePage`

The primary reconciliation workflow for `user` role.

**Steps:**
1. **Select gateway** — dropdown of gateways with upload status
2. **Statement Type** — checkbox: External Statement / Internal Statement
3. **Upload Mode** — checkbox: Upload As Template / Upload Raw Statement
4. **File selection and upload** — drag-drop or browse; supports delete + download of existing files
5. **Preview** — dry-run showing matched/unmatched/carry-forward counts
6. **Save** — commits the reconciliation run to the database

**Key states:**
- `selectedBaseGateway` — currently selected gateway
- `uploadTarget` — `'external'` | `'internal'`
- `uploadMode` — `'template'` | `'transform'`
- `selectedFile` — file chosen but not yet uploaded
- `previewResult` — result from `reconciliationApi.preview()`

---

### `features/gateways/`

**`GatewaysPage`** (user role) — Lists all gateways. Users can view details and submit change requests (create, update, delete, activate) which enter the maker-checker workflow.

**`GatewayApprovalPage`** (admin role) — Lists pending change requests in a paginated table. Admins can view the full proposed config, then **Approve** (auto-applies changes) or **Reject** (requires reason).

---

### `features/operations/`

**`OperationsPage`** (user role) — Side-by-side view of unreconciled external and internal transactions for a selected gateway. Users can:
- Select one external + one internal transaction and manually reconcile them
- Bulk-select and apply the same action to multiple transactions
- Add a reconciliation note

**`AuthorizationPage`** (admin role) — Lists manual reconciliations pending admin sign-off. Admins can:
- View the full transaction details
- **Authorize** (approve) — marks transaction as reconciled
- **Reject** — requires a reason; marks transaction as unreconciled again

**Helper views** (`SimpleSideBySideView`, `SideBySideTransactionView`, `SimpleAuthorizationView`, `SideBySideAuthorizationView`) are sub-components used by the two pages above to separate UI concerns.

---

### `features/reports/ReportsPage`

Allows any authenticated user to download reconciliation reports.

Controls:
- **Gateway** dropdown (only gateways with transactions appear)
- **Date From / Date To** optional filters
- **Format**: XLSX (multi-sheet) or CSV (flat)
- **Run drill-down**: Optional list of reconciliation runs to filter by a specific run

Downloads trigger `reportsApi.downloadReport()` which returns a blob; `downloadFile(blob, filename)` triggers the browser save dialog.

---

### `features/runs/`

**`RunsPage`** — Paginated table of all reconciliation runs. Filterable by gateway and date range. Clicking a row navigates to the detail page.

**`RunDetailPage`** — Shows full stats for a single run: total records, matched, unmatched, carry-forward matches, and transaction counts by reconciliation status.

---

### `features/transactions/TransactionsPage`

Searchable, filterable, paginated view of all transactions across all gateways. Filters:
- Free-text search (transaction ID or narrative)
- Gateway, run ID, date range, reconciliation status, transaction type

---

### `features/users/UsersPage`

Super admin only. Full user lifecycle management:
- List users with pagination and status/role filtering
- **Create user**: form → API auto-generates password → welcome email sent
- **Actions per user**: copy initial password, change role, block/unblock, reset password, deactivate

---

## Hooks

### `useToast` (`hooks/useToast.tsx`)

```ts
import { useToast } from '@/hooks';

const toast = useToast();

toast.success('Reconciliation complete');
toast.error('Upload failed: invalid columns');
toast.info('Preview ready');
toast.warning('File will replace existing');
toast.dismiss(id);
```

Toasts auto-dismiss after 5 seconds. The internal store (`useToastStore`) is a Zustand store that `ToastContainer` subscribes to.

---

## Role-Based Access Control

The RBAC system spans routing (ProtectedRoute), navigation (Sidebar), and API calls. Three roles:

| Role | Code value | Purpose |
|------|-----------|---------|
| Super Admin | `super_admin` | Manages user accounts |
| Admin | `admin` | Approves actions (checker) |
| User | `user` | Initiates actions (maker) |

**Frontend enforcement:**
- `ProtectedRoute` blocks page access with redirect to `/`
- `Sidebar` hides navigation items not accessible to the current role
- Action buttons are conditionally rendered based on `useIsAdmin()`, `useIsUserRole()`, etc.

**Backend enforcement** (source of truth):
- Every endpoint uses a dependency (`require_user_role`, `require_admin_only`, etc.)
- Frontend RBAC is UX-only — unauthorized API calls return 403

**Key rule**: `admin` and `super_admin` are separate roles with no overlap. An admin cannot manage users; a super admin cannot approve reconciliations.
