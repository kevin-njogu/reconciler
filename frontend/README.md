# ReconPay Frontend

React frontend for the Payment Gateway Reconciliation System.

## Tech Stack

- **React 19** with TypeScript
- **Vite** for build tooling
- **TailwindCSS v4** for styling
- **React Router v6** for routing
- **TanStack Query** for server state management
- **Zustand** for client state management
- **React Hook Form + Zod** for form handling and validation
- **Axios** for HTTP requests
- **Lucide React** for icons

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- Backend API running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at `http://localhost:3000`.

### Build for Production

```bash
npm run build
npm run preview  # Preview production build
```

## Project Structure

```
src/
├── api/                    # API client and endpoints
│   ├── client.ts          # Axios instance with interceptors
│   ├── auth.ts            # Authentication endpoints
│   ├── users.ts           # User management endpoints
│   ├── batches.ts         # Batch endpoints
│   ├── gateways.ts        # Gateway configuration endpoints
│   ├── upload.ts          # File upload endpoints
│   ├── reconciliation.ts  # Reconciliation endpoints
│   └── reports.ts         # Report download endpoints
├── components/
│   ├── ui/                # Reusable UI components
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── Select.tsx
│   │   ├── Card.tsx
│   │   ├── Modal.tsx
│   │   ├── Table.tsx
│   │   ├── Badge.tsx
│   │   ├── Alert.tsx
│   │   ├── FileUpload.tsx
│   │   └── ...
│   └── layout/            # Layout components
│       ├── Layout.tsx
│       ├── Sidebar.tsx
│       ├── Header.tsx
│       └── ProtectedRoute.tsx
├── features/              # Feature modules
│   ├── auth/              # Login, password change
│   ├── dashboard/         # Dashboard page
│   ├── users/             # User management (admin)
│   ├── batches/           # Batch management
│   ├── upload/            # File upload
│   ├── reconciliation/    # Run reconciliation
│   ├── reports/           # Download reports
│   └── gateways/          # Gateway configuration (admin)
├── hooks/                 # Custom hooks
│   └── useToast.tsx       # Toast notifications
├── lib/                   # Utility functions
│   └── utils.ts           # Helper functions
├── stores/                # Zustand stores
│   └── authStore.ts       # Authentication state
├── types/                 # TypeScript types
│   └── index.ts           # All type definitions
├── App.tsx                # Main app with routes
├── main.tsx               # Entry point
└── index.css              # Global styles + Tailwind
```

## Features

### Authentication
- JWT-based authentication with access/refresh tokens
- Auto token refresh on 401 responses
- Protected routes with role-based access
- Forced password change for new users

### User Management (Admin)
- List, create, update users
- Block/unblock users
- Reset passwords
- Role assignment (user, admin, super_admin)

### Batch Management
- Create new reconciliation batches
- View batch status and details
- Filter by status

### File Upload
- Upload external (bank) and internal (Workpay) files
- Gateway selection dropdown
- Drag & drop file upload
- Download templates

### Reconciliation
- Select batch and gateway
- Preview reconciliation results
- Save reconciliation to database
- View match statistics

### Reports
- Download gateway-specific reports
- Download full batch reports
- Excel format output

### Gateway Configuration (Admin)
- Add new payment gateways
- Edit gateway settings
- Configure charge keywords
- Activate/deactivate gateways

## Environment

The frontend proxies API requests to the backend via Vite's dev server proxy:

```typescript
// vite.config.ts
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

For production, configure your web server (nginx, etc.) to proxy `/api` to the backend.

## Authentication Flow

1. User logs in with username/password
2. Backend returns access token (15 min) and refresh token (7 days)
3. Tokens stored in localStorage
4. Access token attached to all API requests via Axios interceptor
5. On 401, automatically refresh token and retry request
6. On refresh failure, redirect to login

## Role-Based Access

| Role | Access |
|------|--------|
| `user` | Dashboard, Batches, Upload, Reconciliation, Reports |
| `admin` | All user access + User Management, Gateway Configuration |
| `super_admin` | All admin access + Deactivate users, Create admins |

## Scripts

```bash
npm run dev      # Start development server
npm run build    # Build for production
npm run preview  # Preview production build
npm run lint     # Run ESLint
```
