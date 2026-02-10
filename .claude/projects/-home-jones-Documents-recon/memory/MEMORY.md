# Project Memory

## Project: Payment Gateway Reconciliation System
- **Backend**: FastAPI + SQLAlchemy + MySQL + Alembic
- **Frontend**: React 19 + TypeScript + Vite + Tailwind CSS + Zustand + React Query
- **Auth**: 2-step OTP login, JWT with session tokens, bcrypt, concurrent session prevention
- **Roles**: user (maker), admin (checker), super_admin (user mgmt)

## Key Architecture Patterns
- Maker-checker workflow for: manual reconciliation, gateway changes, batch deletion
- Reconciliation key: `{reference}|{amount}|{base_gateway}`
- File storage: `{batch_id}/{external_gateway}/{gateway_name}.{ext}`
- Gateway naming: external=`equity`, internal=`workpay_equity`
- Pluggable storage: LocalStorage or GcsStorage

## Recent Work: Metabase Integration
- Backend: `app/controller/metabase.py` - connection, browsing, import
- Frontend: `MetabaseConnection.tsx`, `MetabaseDashboard.tsx`
- Import flow: execute question → column mapping → save CSV to batch
- Gateway fetch issue: `getGateways()` filters by `gateway_type=external`. Fixed to use `list()` instead.
- Date range filtering added to import modal

## Common Gotchas
- `gatewaysApi.getGateways()` filters `gateway_type=external` - may miss gateways. Use `gatewaysApi.list()` for all.
- Alert component `title` prop expects string, not JSX elements
- Button `variant` values: primary, secondary, outline, ghost, danger (no "default")
- Frontend proxy: `/api` → `http://localhost:8000` in Vite dev

## File Locations
- See [architecture.md](architecture.md) for detailed file map
