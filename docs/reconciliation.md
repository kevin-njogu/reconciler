# Reconciliation Logic

This document describes the reconciliation system that matches transactions between external bank statements and internal Workpay records.

## Overview

The reconciliation process matches transactions from two sources:
- **External records**: Bank statements from payment gateways (Equity, KCB, M-Pesa)
- **Internal records**: Workpay system records

Matching is performed using a composite reconciliation key that combines reference, amount, and gateway information.

## Reconciliation Key Format

The system generates a reconciliation key for each transaction:

```
{reference}|{amount}|{base_gateway}
```

### Key Components

| Component | Description | Example |
|-----------|-------------|---------|
| `reference` | Transaction reference, cleaned (no decimals) | `123456` |
| `amount` | Absolute whole number (no cents) | `5000` |
| `base_gateway` | Base gateway name (lowercase) | `equity` |

### Key Generation Rules

1. **Reference Cleaning**:
   - Remove decimal places: `123456.0` → `123456`
   - Empty/null values become `NA`
   - Scientific notation is handled: `1.23456E+5` → `123456`

2. **Amount Cleaning**:
   - Use absolute value (negatives become positive)
   - Use whole number only (no cents): `5000.50` → `5000`
   - For external debits: use `Debit` column
   - For internal records: use `Debit` column (payout amount)

3. **Base Gateway**:
   - Both external and internal transactions use the same base gateway
   - Example: `equity_external` and `equity_internal` both use `equity`
   - This enables matching between the two sources

### Example Keys

| Source | Reference | Amount | Gateway | Key |
|--------|-----------|--------|---------|-----|
| External (Equity) | 123456 | 5000.00 | equity_external | `123456\|5000\|equity` |
| Internal (Workpay) | 123456 | 5000.00 | equity_internal | `123456\|5000\|equity` |

These two records match because they have the same reconciliation key.

## Gateway Naming Convention

Transactions are stored with gateway identifiers that indicate their source:

| Source Type | Naming Pattern | Example |
|-------------|----------------|---------|
| External (bank statement) | `{gateway}_external` | `equity_external` |
| Internal (Workpay) | `{gateway}_internal` | `equity_internal` |

### File to Gateway Mapping

| Uploaded File | Stored Gateway |
|---------------|----------------|
| `equity.xlsx` | `equity_external` |
| `workpay_equity.xlsx` | `equity_internal` |
| `kcb.csv` | `kcb_external` |
| `workpay_kcb.csv` | `kcb_internal` |

## Null Value Handling

Before reconciliation, null/empty values are filled with defaults:

| Column | Fill Value | Notes |
|--------|------------|-------|
| Date | Current date | Format: `YYYY-MM-DD` |
| Reference | `NA` | String literal |
| Details | `NA` | String literal |
| Debit | `0` | Numeric zero |
| Credit | `0` | Numeric zero |

This ensures all transactions can be processed and keyed properly.

## Transaction Classification

### External Transactions (Bank Statement)

| Type | Condition | Status | Note |
|------|-----------|--------|------|
| Credit | `Credit > 0` | `reconciled` | `System Reconciled - Credit` |
| Charge | `Debit > 0` AND matches charge keywords | `reconciled` | `System Reconciled - Charge` |
| Debit (matched) | `Debit > 0` AND key matches internal | `reconciled` | `System Reconciled` |
| Debit (unmatched) | `Debit > 0` AND key NOT in internal | `unreconciled` | `null` |

### Internal Transactions (Workpay)

| Type | Condition | Status | Note |
|------|-----------|--------|------|
| Payout (matched) | Key matches external debit | `reconciled` | `System Reconciled` |
| Payout (unmatched) | Key NOT in external debits | `unreconciled` | `null` |

### Charge Keywords

Charges are identified by keywords in **both the `Reference` and `Details` columns**. A transaction is classified as a charge if:
- `Debit > 0` AND
- (`Reference` contains any charge keyword OR `Details` contains any charge keyword)

This ensures charges are correctly identified even when the keyword appears in the Reference field instead of the Details field.

**Default keywords per gateway:**

- **Equity**: `CHARGE`, `FEE`, `COMMISSION`, `LEDGER FEE`, `EXCISE DUTY`
- **KCB**: `CHARGE`, `FEE`, `COMMISSION`
- **M-Pesa**: `CHARGE`, `FEE`, `COMMISSION`, `TRANSACTION COST`

Keywords are configurable per gateway in the database and matched case-insensitively.

## Reconciliation Flow

```
1. User selects pending batch
         ↓
2. System fetches available gateways (gateways with uploaded files)
         ↓
3. User selects gateway
         ↓
4. User clicks "Reconcile"
         ↓
5. System validates:
   ├── Batch exists and is pending
   ├── Gateway directory exists
   ├── External file exists ({gateway}.xlsx or .csv)
   └── Internal file exists (workpay_{gateway}.xlsx or .csv)
         ↓
6. System loads and processes files:
   ├── Fill null values
   ├── Generate reconciliation keys
   └── Add metadata (batch_id, gateway, source_file)
         ↓
7. System matches transactions:
   ├── Build key sets for external debits
   ├── Build key sets for internal records
   └── Find matching keys
         ↓
8. System saves to database:
   ├── All external transactions
   └── All internal transactions
         ↓
9. Return summary to user
```

## API Endpoints

### Get Available Gateways

Returns gateways that have files uploaded for a batch.

```
GET /api/v1/reconcile/available-gateways/{batch_id}
```

**Response:**
```json
{
  "batch_id": "BATCH-20260125-001",
  "available_gateways": [
    {
      "gateway": "equity",
      "display_name": "Equity Bank",
      "has_external": true,
      "has_internal": true,
      "external_file": "equity.xlsx",
      "internal_file": "workpay_equity.xlsx",
      "ready_for_reconciliation": true
    }
  ]
}
```

### Run Reconciliation

Validates, processes, and saves reconciliation in a single operation.

```
POST /api/v1/reconcile?batch_id={batch_id}&gateway={gateway}
```

**Parameters:**
- `batch_id`: The batch ID to reconcile
- `gateway`: Base gateway name (e.g., `equity`, not `equity_external`)

**Response:**
```json
{
  "message": "Reconciliation completed and saved",
  "batch_id": "BATCH-20260125-001",
  "gateway": "equity",
  "summary": {
    "total_external": 150,
    "total_internal": 145,
    "matched": 140,
    "unmatched_external": 10,
    "unmatched_internal": 5,
    "credits": 20,
    "charges": 5
  },
  "saved": {
    "external_records": 150,
    "internal_records": 145,
    "total": 295
  }
}
```

## Error Handling

| Scenario | HTTP Status | Message |
|----------|-------------|---------|
| Batch not found | 404 | "Batch not found" |
| Batch not pending | 400 | "Batch is not in pending status" |
| Gateway directory missing | 400 | "No files uploaded for {gateway}" |
| External file missing | 400 | "External file not found for {gateway}" |
| Internal file missing | 400 | "Internal file not found for {gateway}" |
| Already reconciled | 409 | "Reconciliation already exists for this batch and gateway" |
| File read error | 500 | "Error reading file: {details}" |

## Database Schema

### Transaction Table Columns

| Column | Type | Description |
|--------|------|-------------|
| `gateway` | VARCHAR(50) | Gateway identifier (e.g., `equity_external`) |
| `transaction_type` | VARCHAR(50) | Type: `credit`, `debit`, `charge`, `payout` |
| `date` | DATETIME | Transaction date |
| `transaction_id` | VARCHAR(255) | Reference/transaction ID |
| `narrative` | VARCHAR(500) | Details/description |
| `debit` | DECIMAL(18,2) | Debit amount |
| `credit` | DECIMAL(18,2) | Credit amount |
| `reconciliation_status` | VARCHAR(50) | `reconciled` or `unreconciled` |
| `reconciliation_note` | VARCHAR(1000) | System or manual note |
| `reconciliation_key` | VARCHAR(255) | Generated match key for auditing |
| `source_file` | VARCHAR(255) | Source filename |
| `batch_id` | VARCHAR(100) | Batch identifier |
| `is_manually_reconciled` | VARCHAR(10) | `true` or `null` |

### Indexes

- `ix_gateway_batch`: (`gateway`, `batch_id`)
- `ix_gateway_type_batch`: (`gateway`, `transaction_type`, `batch_id`)
- `ix_recon_status_batch`: (`reconciliation_status`, `batch_id`)
- `ix_recon_key_batch`: (`reconciliation_key`, `batch_id`)

## File Requirements

### Supported Formats

- Excel: `.xlsx`, `.xls`
- CSV: `.csv`

### Required Columns

All uploaded files must have these columns:

| Column | Type | Description |
|--------|------|-------------|
| Date | Date | Transaction date (YYYY-MM-DD) |
| Reference | String | Unique transaction identifier |
| Details | String | Transaction description |
| Debit | Number | Debit amount (optional) |
| Credit | Number | Credit amount (optional) |

### File Naming

| File Type | Naming Pattern | Storage Path |
|-----------|----------------|--------------|
| External | `{gateway}.xlsx` | `{batch_id}/{gateway}/{gateway}.xlsx` |
| Internal | `workpay_{gateway}.xlsx` | `{batch_id}/{gateway}/workpay_{gateway}.xlsx` |

## Manual Reconciliation

For unmatched transactions, users can perform manual reconciliation:

1. View unreconciled transactions in the Transactions page
2. Select transactions to manually reconcile
3. Provide a reconciliation note
4. Submit for admin authorization (maker-checker workflow)

### Authorization Status

| Status | Description |
|--------|-------------|
| `pending` | Awaiting admin approval |
| `authorized` | Approved by admin |
| `rejected` | Rejected by admin |

## Best Practices

1. **Verify file format**: Ensure files use the unified template with correct columns
2. **Check for duplicates**: Remove duplicate records from source files before upload
3. **Validate references**: Ensure Reference values match between external and internal files
4. **Review unmatched**: Investigate unmatched transactions for data quality issues
5. **Use consistent amounts**: Ensure amounts match exactly (same currency, same precision)
