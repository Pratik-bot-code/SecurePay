# SecurePay — Defect & Bug Resolution Tracker

**Last Updated**: October 28, 2026  
**Status**: All Verifiable Defects Resolved & Tested

---

## Defect Inventory & Resolution History

### BUG-001: Outgoing Sandbox Transfers Inverted as Inflows
- **Severity**: Critical (Financial Logic / Ledger Integrity)
- **Component**: `backend/app/services/payment_provider.py`
- **Root Cause**: The sandbox payment confirmation method (`confirm_payment()`) unconditionally executed `user_acc.balance_paise += order.amount_paise`, posted a credit `LedgerEntry`, and issued a "Payment Received" notification, even when the authenticated user was initiating an outgoing transfer to a peer.
- **Resolution**: Refactored `confirm_payment` to inspect order metadata and recipient identity. Outgoing P2P transfers now execute true double-entry bookkeeping: debiting the payer, crediting the on-platform payee (if present), generating distinct debit/credit ledger records, and issuing accurate "Payment Sent" notifications.
- **Verification**: Verified with automated tests in `test_fintech_upgrade.py` and `test_payment_provider.py`.

---

### BUG-002: Incomplete CSRF Token Propagation on Authentication
- **Severity**: High (Security / Usability)
- **Component**: `frontend/src/components/AuthScreen.jsx`
- **Root Cause**: The authentication callback in `AuthScreen.jsx` was invoked with `onAuthenticated(response.user)`, omitting the `csrf_token` returned by `/auth/login`. This required an extra session roundtrip before state-changing POST requests could authenticate successfully.
- **Resolution**: Updated `AuthScreen.jsx` to pass `onAuthenticated(response.user, response.csrf_token)`, synchronizing the CSRF token in memory and local session storage immediately upon login.
- **Verification**: Confirmed seamless first-time actions without CSRF 403 errors across all modal workflows.

---

### BUG-003: Disconnected Endpoint Signatures in Frontend API Client
- **Severity**: Medium (API Contract Mismatch)
- **Component**: `frontend/src/api.js`
- **Root Cause**:
  1. `revokeSession()` dispatched a `POST` request to `/auth/sessions/${id}/revoke`, whereas the backend router defined `DELETE /auth/sessions/{id}`.
  2. `changePassword()` dispatched `POST /auth/password`, whereas backend defined `PUT /auth/password`.
- **Resolution**: Updated `frontend/src/api.js` to dispatch `DELETE` to `/auth/sessions/${id}` and `PUT` to `/auth/password`, aligning the client with the OpenAPI schema.
- **Verification**: Tested remote session revocation and password modification in `test_api_ownership.py`.

---

### BUG-004: Missing Recipient Metadata & Status History in DB Schema
- **Severity**: High (Database Schema & Audit Compliance)
- **Component**: `backend/alembic/versions/` & `backend/app/models/entities.py`
- **Root Cause**: The initial database schema lacked recipient fields (`recipient_identifier`, `recipient_type`, `recipient_display_name`) on `PaymentOrder` and had no audit trail table for order state transitions (`PaymentStatusHistory`).
- **Resolution**: Created Alembic migration `b3c8e1f42a7d_add_recipient_and_status_history.py` (down revision `fc11c9b21045`), adding the columns and creating the `payment_status_history` table with composite indexes on `(payment_order_id, created_at)`. Applied migration to head.
- **Verification**: Tested status history transitions and DB persistence across reconnection in `test_fintech_upgrade.py`.

---

### BUG-005: Unpaginated Transaction Ledger & Missing Summary Metrics
- **Severity**: Medium (Performance & UX)
- **Component**: `backend/app/api/routes.py` & `frontend/src/components/TransactionLedger.jsx`
- **Root Cause**: The transaction list endpoint only supported unbounded arrays without server-side aggregation for credits, debits, pending, successful, and failed counts.
- **Resolution**:
  1. Added `GET /api/transactions/summary` returning total credits, total debits, and counts for successful, pending, and failed states.
  2. Enhanced `GET /api/transactions` with `paginated=True` support returning `PaginatedTransactionsResponse`.
  3. Built `TransactionLedger.jsx` with summary cards, table, mobile cards, search, filters, pagination, and CSV export.
- **Verification**: Tested in `test_fintech_upgrade.py::test_paginated_transactions_and_csv_export`.

---

### BUG-006: Missing Indian Bank Directory & Unsupported vs Listed Ambiguity
- **Severity**: Medium (Fintech Capability)
- **Component**: `backend/app/services/bank_directory.py` & `frontend/src/components/BankAccountsModal.jsx`
- **Root Cause**: The previous bank linking modal contained arbitrary static bank names without category filtering, IFSC lookup, or distinction between directory-listed banks and banks enabled for sandbox account linking.
- **Resolution**: Created `backend/app/services/bank_directory.py` containing verified Indian financial institutions across Public Sector, Private, Small Finance, Payments, and Regional Rural banks. Added `/api/banks/directory` and `/api/banks/lookup/{ifsc}` endpoints. Updated `BankAccountsModal.jsx` with category chips and clear messaging for unsupported vs supported banks.
- **Verification**: Tested in `test_fintech_upgrade.py::test_bank_directory_endpoints`.

---

### BUG-007: Lack of Recipient Pre-Validation in Payment Flow
- **Severity**: Medium (Fintech UX / Error Prevention)
- **Component**: `frontend/src/components/SendPaymentModal.jsx` & `backend/app/api/routes.py`
- **Root Cause**: Payments previously initiated direct order creation without pre-validating or normalizing recipient identifiers, risking invalid transfers and poor user feedback.
- **Resolution**: Implemented `POST /api/payments/validate-recipient` validating UPI VPAs, Indian 10-digit mobile numbers, and platform `@handles`. Rebuilt `SendPaymentModal.jsx` into a 5-step guided wizard with privacy masking and ₹5,000 preset.
- **Verification**: Tested in `test_fintech_upgrade.py::test_recipient_validation`.

---

### BUG-008: Missing Double-Entry Ledger Immutability & Status Transitions
- **Severity**: High (Ledger Integrity)
- **Component**: `backend/app/core/database.py` & `backend/app/models/entities.py`
- **Root Cause**: Ledger entries could theoretically be modified or deleted without an audit trail if database-level constraints were bypassed.
- **Resolution**: Added SQLite triggers blocking `UPDATE` and `DELETE` on `ledger_entries`. All order state transitions now append an immutable row in `payment_status_history`.
- **Verification**: Tested in `test_database_reliability.py::test_ledger_trigger_immutability` and `test_fintech_upgrade.py::test_payment_status_history_tracking`.

